"""API phan tich chung khoan - Phan Tich CK."""
import logging
import time
from collections import deque
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import alerts, brief, events, flow, fund, fundtrend, market, news, peers, portfolio, regime, screen
from backend.auth import admin_guard, is_locked

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="Phan Tich Co Phieu VN", version="1.0",
              docs_url=None, redoc_url=None, openapi_url=None)


@app.on_event("startup")
def _startup():
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
    return {"in_session": market.is_session(), "now": market.now_vn().strftime("%H:%M %d/%m")}


@app.get("/api/symbols")
def api_symbols():
    return {"basket": market.BASKET}


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


# ---------------- alerts ----------------
@app.get("/api/alerts")
def api_alerts(limit: int = Query(50, ge=1, le=200)):
    return {"status": "ready", "alerts": alerts.list_alerts(limit)}


@app.post("/api/alerts/rules", dependencies=[Depends(admin_guard)])
async def api_add_alert_rule(request: Request):
    body = await request.json()
    try:
        rule = alerts.add_rule(body)
        return {"status": "ok", "rule": rule}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@app.get("/api/alerts/rules")
def api_list_alert_rules():
    return {"status": "ready", "rules": alerts.list_rules()}


@app.delete("/api/alerts/rules/{rule_id}", dependencies=[Depends(admin_guard)])
def api_delete_alert_rule(rule_id: str):
    ok = alerts.delete_rule(rule_id)
    if ok:
        return {"status": "ok"}
    return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy rule"})


@app.post("/api/alerts/clear", dependencies=[Depends(admin_guard)])
def api_clear_alerts():
    n = alerts.clear_alerts()
    return {"status": "ok", "cleared": n}


# ---------------- portfolio ----------------
@app.get("/api/portfolio")
def api_portfolio():
    return {"status": "ready", **portfolio.get_summary()}


@app.post("/api/portfolio", dependencies=[Depends(admin_guard)])
async def api_portfolio_add(request: Request):
    body = await request.json()
    try:
        r = portfolio.add_position(body.get("symbol", ""),
                                   float(body.get("qty", 0)),
                                   float(body.get("avg_price", 0)))
        return {"status": "ok", **r}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@app.put("/api/portfolio/{sym}", dependencies=[Depends(admin_guard)])
async def api_portfolio_update(sym: str, request: Request):
    body = await request.json()
    try:
        r = portfolio.update_position(sym, float(body.get("qty", 0)),
                                      float(body.get("avg_price", 0)))
        return {"status": "ok", **r}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@app.delete("/api/portfolio/{sym}", dependencies=[Depends(admin_guard)])
def api_portfolio_delete(sym: str):
    ok = portfolio.remove_position(sym)
    if ok:
        return {"status": "ok"}
    return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy"})


# ---------------- brief ----------------
@app.get("/api/brief")
def api_brief():
    return brief.build_brief()


@app.exception_handler(Exception)
def err(request, exc):  # noqa: ANN001
    # khong tra noi dung exception ra client (chan lo thong tin noi bo) — ghi log server
    logging.getLogger("phan-tich").exception("500 %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={
        "status": "error",
        "message": "Lỗi máy chủ — thử lại sau."})


app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="static")
