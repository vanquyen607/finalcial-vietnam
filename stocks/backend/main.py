"""API phan tich chung khoan - Phan Tich CK."""
import logging
import time
from collections import deque
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend import alerts, auth2, brief, events, flow, fund, fundtrend, market, news, peers, quote, regime, screen, user_data
from backend.auth import admin_guard, is_locked
from backend import db as _db

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

COOKIE_NAME = "ck_session"
COOKIE_MAX_AGE = auth2.SESSION_TTL  # 7 ngày

app = FastAPI(title="Phan Tich Co Phieu VN", version="1.0",
              docs_url=None, redoc_url=None, openapi_url=None)

# ---- Pages (gate: chua dang nhap thi ve landing) ----
def _page_session(request: Request) -> dict | None:
    """Doc session tu cookie (truong hop trang HTML) hoac header."""
    token = request.cookies.get(COOKIE_NAME) or request.headers.get("x-session-token", "")
    return auth2.get_session(token)

@app.get("/")
def landing_page():
    return FileResponse(FRONTEND / "landing.html")

@app.get("/app")
def main_app(request: Request):
    if not _page_session(request):
        return RedirectResponse("/", status_code=302)
    return FileResponse(FRONTEND / "index.html")

@app.get("/admin")
def admin_page(request: Request):
    s = _page_session(request)
    if not s:
        return RedirectResponse("/", status_code=302)
    if s.get("role") != "admin":
        return RedirectResponse("/app", status_code=302)
    return FileResponse(FRONTEND / "admin.html")

# ---- Auth API ----
@app.post("/api/auth/register")
async def api_register(request: Request):
    body = await request.json()
    try:
        r = auth2.register(
            username=body.get("username", ""),
            email=body.get("email", ""),
            password=body.get("password", ""),
        )
        return {"status": "ok", **r}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.post("/api/auth/login")
async def api_login(request: Request):
    body = await request.json()
    try:
        r = auth2.login(
            username=body.get("username", ""),
            password=body.get("password", ""),
        )
        resp = JSONResponse(content={"status": "ok", **r})
        resp.set_cookie(
            COOKIE_NAME, r["token"],
            max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax", path="/",
        )
        return resp
    except ValueError as e:
        return JSONResponse(status_code=401, content={"status": "error", "message": str(e)})

@app.post("/api/auth/logout")
async def api_logout(request: Request):
    hdr = request.headers.get("x-session-token", "")
    ck = request.cookies.get(COOKIE_NAME, "")
    # xóa session của cả header lẫn cookie (tránh sót khi token header đã cũ)
    if hdr:
        auth2.logout(hdr)
    if ck and ck != hdr:
        auth2.logout(ck)
    resp = JSONResponse(content={"status": "ok"})
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp

@app.get("/api/auth/me")
def api_me(request: Request, session: dict = Depends(auth2.require_session)):
    resp = JSONResponse(content={"status": "ok", **session})
    # neu gui token hop le qua header ma cookie chua co/thua → sync cookie
    # (tranh loop: localStorage co token cu nhung cookie da mat khi vua deploy)
    hdr = request.headers.get("x-session-token", "")
    ck = request.cookies.get(COOKIE_NAME, "")
    if hdr and hdr != ck:
        resp.set_cookie(
            COOKIE_NAME, hdr,
            max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax", path="/",
        )
    return resp

# ---- Admin user management API ----
@app.get("/api/admin/users")
def api_admin_users(session: dict = Depends(auth2.require_admin)):
    return {"status": "ok", "users": auth2.list_users()}

@app.post("/api/admin/users/{username}/role")
async def api_set_role(username: str, request: Request, session: dict = Depends(auth2.require_admin)):
    body = await request.json()
    try:
        auth2.set_user_role(username, body.get("role", "user"))
        return {"status": "ok"}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.post("/api/admin/users/{username}/active")
async def api_set_active(username: str, request: Request, session: dict = Depends(auth2.require_admin)):
    body = await request.json()
    try:
        auth2.set_user_active(username, bool(body.get("active", True)))
        return {"status": "ok"}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.delete("/api/admin/users/{username}")
def api_delete_user(username: str, session: dict = Depends(auth2.require_admin)):
    try:
        auth2.delete_user(username)
        return {"status": "ok"}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})



@app.on_event("startup")
def _startup():
    auth2._bootstrap()   # init Neon schema + default admin
    try:
        user_data.migrate_schema()
    except Exception as e:
        import logging
        logging.getLogger("vnstock.user_data").warning(f"Schema migration error: {e}")
    alerts.migrate_legacy()   # file legacy -> Postgres (admin), idempotent
    alerts.start_scheduler()

# ---------------------------------------------------------------- rate limit
_WINDOW = 60          # giay
_LIMIT_ALL = 180      # req/phut/ip cho toan bo /api/
_LIMIT_STRICT = 10    # phut/ip cho POST + ?refresh=1 (tai tron API vnstock)
_hits: dict = {}
_hits_strict: dict = {}


def _ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "-"


def _allow(store: dict, ip: str, limit: int, now: float) -> bool:
    q = store.setdefault(ip, deque())
    while q and now - q[0] > _WINDOW:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


@app.middleware("http")
async def guard(request: Request, call_next):  # noqa: ANN001
    if request.url.path.startswith("/api/"):
        now = time.time()
        if len(_hits) > 500:
            _hits.clear()
            _hits_strict.clear()
        ip = _ip(request)
        strict = request.method == "POST" or request.query_params.get("refresh") == "1"
        over = not _allow(_hits, ip, _LIMIT_ALL, now) or (
            strict and not _allow(_hits_strict, ip, _LIMIT_STRICT, now))
        if over:
            return JSONResponse(status_code=429, content={
                "status": "error",
                "message": "Quá nhiều yêu cầu — đợi ít phút rồi thử lại."})
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return resp


@app.get("/api/health")
def health():
    return {"ok": True, "locked": is_locked(),
            "time": market.now_vn().strftime("%H:%M:%S %d/%m/%Y")}


@app.get("/api/auth/check")
def api_auth_check(_: None = Depends(admin_guard)):
    return {"status": "ok", "locked": is_locked()}


@app.get("/api/overview")
def api_overview(refresh: int = Query(0)):
    return market.overview(refresh=bool(refresh))


@app.get("/api/screen")
def api_screen():
    return screen.screen()


@app.post("/api/screen/run", dependencies=[Depends(admin_guard)])
def api_screen_run(auto: int = Query(0)):
    return screen.start_screen(auto=bool(auto))


@app.post("/api/screen/stop", dependencies=[Depends(admin_guard)])
def api_screen_stop():
    return screen.stop_screen()


@app.get("/api/session")
def api_session():
    now = market.now_vn()
    nxt = market.next_open(now)
    return {"in_session": market.is_session(now),
            "state": market.session_state(now),
            "now": now.strftime("%H:%M %d/%m"),
            "next_open_ts": int(nxt.timestamp()),
            "next_open": nxt.strftime("%H:%M %d/%m")}


@app.get("/api/symbols")
def api_symbols():
    return {"basket": market.BASKET}


@app.get("/api/quote")
def api_quote(symbols: str = Query("")):
    return quote.get(symbols)


@app.get("/api/symbol/{sym}")
def api_symbol(sym: str, refresh: int = Query(0)):
    result = market.get_symbol(sym, refresh=bool(refresh), priority=bool(refresh))
    if result.get("status") == "ready" and result.get("data"):
        result["data"] = regime.apply_gate(result["data"])
    return result


@app.get("/api/symbol/{sym}/news")
def api_symbol_news(sym: str, refresh: int = Query(0)):
    return news.get_news(sym, refresh=bool(refresh))


@app.get("/api/breadth")
def api_breadth(refresh: int = Query(0)):
    return market.breadth(refresh=bool(refresh))


@app.get("/api/regime")
def api_regime(refresh: int = Query(0)):
    return regime.get_regime(refresh=bool(refresh))


@app.get("/api/symbol/{sym}/fundamentals")
def api_symbol_fundamentals(sym: str):
    return fund.get_fundamentals(sym)


@app.get("/api/symbol/{sym}/events")
def api_symbol_events(sym: str, refresh: int = Query(0)):
    return events.get_events(sym, refresh=bool(refresh))


@app.get("/api/symbol/{sym}/fundtrend")
def api_symbol_fundtrend(sym: str):
    return fundtrend.get_fundtrend(sym)


@app.get("/api/symbol/{sym}/peers")
def api_symbol_peers(sym: str):
    return peers.get_peers(sym)


@app.get("/api/symbol/{sym}/flow")
def api_symbol_flow(sym: str):
    return flow.get_flow(sym)


# ---------------- user-specific endpoints (/api/me/...) ----------------
@app.get("/api/me/watchlist")
def api_me_watchlist(session: dict = Depends(auth2.require_session)):
    return {"status": "ok", "watchlist": user_data.watchlist_get(session["uid"])}

@app.post("/api/me/watchlist")
async def api_me_watchlist_add(request: Request, session: dict = Depends(auth2.require_session)):
    body = await request.json()
    try:
        r = user_data.watchlist_add(
            session["uid"],
            body.get("symbol", ""),
            body.get("note", ""),
            float(body["price_target"]) if body.get("price_target") is not None else None,
        )
        return {"status": "ok", **r}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.delete("/api/me/watchlist/{sym}")
def api_me_watchlist_delete(sym: str, session: dict = Depends(auth2.require_session)):
    ok = user_data.watchlist_remove(session["uid"], sym)
    return {"status": "ok", "removed": ok}

@app.get("/api/me/portfolio")
def api_me_portfolio(session: dict = Depends(auth2.require_session)):
    return {"status": "ready", **user_data.portfolio_get(session["uid"])}

@app.post("/api/me/portfolio")
async def api_me_portfolio_add(request: Request, session: dict = Depends(auth2.require_session)):
    body = await request.json()
    try:
        r = user_data.portfolio_add(
            session["uid"],
            body.get("symbol", ""),
            float(body.get("qty", 0)),
            float(body.get("avg_price", 0)),
        )
        return {"status": "ok", **r}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.put("/api/me/portfolio/{sym}")
async def api_me_portfolio_update(sym: str, request: Request, session: dict = Depends(auth2.require_session)):
    body = await request.json()
    try:
        r = user_data.portfolio_update(
            session["uid"],
            sym,
            float(body.get("qty", 0)),
            float(body.get("avg_price", 0)),
        )
        return {"status": "ok", **r}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.delete("/api/me/portfolio/{sym}")
def api_me_portfolio_delete(sym: str, session: dict = Depends(auth2.require_session)):
    ok = user_data.portfolio_remove(session["uid"], sym)
    return {"status": "ok", "removed": ok}

@app.post("/api/me/portfolio/sell")
async def api_me_portfolio_sell(request: Request, session: dict = Depends(auth2.require_session)):
    body = await request.json()
    try:
        r = user_data.portfolio_sell(
            session["uid"],
            body.get("symbol", ""),
            float(body.get("qty", 0)),
            float(body.get("price", 0)),
            float(body.get("fee", 0)),
            body.get("note", ""),
        )
        return {"status": "ok", **r}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.get("/api/me/transactions")
def api_me_transactions(sym: str = Query(""), limit: int = Query(50), session: dict = Depends(auth2.require_session)):
    return {"status": "ok", "transactions": user_data.transactions_get(session["uid"], sym, limit)}

@app.get("/api/me/alerts/rules")
def api_me_alert_rules(session: dict = Depends(auth2.require_session)):
    return {"status": "ok", "rules": user_data.alert_rules_get(session["uid"])}

@app.post("/api/me/alerts/rules")
async def api_me_alert_rule_add(request: Request, session: dict = Depends(auth2.require_session)):
    body = await request.json()
    try:
        r = user_data.alert_rule_add(
            session["uid"],
            body.get("symbol", ""),
            body.get("type", ""),
            float(body.get("threshold", 0)),
            body.get("note", ""),
        )
        return {"status": "ok", **r}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.delete("/api/me/alerts/rules/{rule_id}")
def api_me_alert_rule_delete(rule_id: str, session: dict = Depends(auth2.require_session)):
    ok = user_data.alert_rule_delete(session["uid"], rule_id)
    return {"status": "ok", "removed": ok}

@app.get("/api/me/alerts/events")
def api_me_alert_events(limit: int = Query(50, ge=1, le=200),
                        session: dict = Depends(auth2.require_session)):
    return {"status": "ready", "alerts": user_data.alert_events_get(session["uid"], limit=limit)}

@app.post("/api/me/alerts/events/clear")
def api_me_alert_events_clear(session: dict = Depends(auth2.require_session)):
    n = user_data.alert_events_clear(session["uid"])
    return {"status": "ok", "cleared": n}

@app.get("/api/me/notes/{sym}")
def api_me_note_get(sym: str, session: dict = Depends(auth2.require_session)):
    return {"status": "ok", "symbol": sym.upper(), "content": user_data.note_get(session["uid"], sym)}

@app.put("/api/me/notes/{sym}")
async def api_me_note_save(sym: str, request: Request, session: dict = Depends(auth2.require_session)):
    body = await request.json()
    try:
        user_data.note_save(session["uid"], sym, body.get("content", ""))
        return {"status": "ok"}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.get("/api/calc/breakeven")
def api_calc_breakeven(price: float = Query(...), buy_fee: float = Query(0.25), sell_fee: float = Query(0.25), tax: float = Query(0.1)):
    return {"status": "ok", **user_data.calc_breakeven(price, buy_fee, sell_fee, tax)}


# ---------------- brief ----------------
@app.get("/api/brief")
def api_brief(session: dict | None = Depends(auth2.optional_session)):
    return brief.build_brief(session["uid"] if session else None)


@app.exception_handler(Exception)
def err(request, exc):  # noqa: ANN001
    # khong tra noi dung exception ra client (chan lo thong tin noi bo) — ghi log server
    logging.getLogger("phan-tich").exception("500 %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={
        "status": "error",
        "message": "Lỗi máy chủ — thử lại sau."})


app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="static")
