"""API phan tich chung khoan - Phan Tich CK."""
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import market, news

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="Phan Tich Co Phieu VN", version="1.0",
              docs_url=None, redoc_url=None, openapi_url=None)

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
    return {"ok": True, "time": market.now_vn().strftime("%H:%M:%S %d/%m/%Y")}


@app.get("/api/overview")
def api_overview(refresh: int = Query(0)):
    return market.overview(refresh=bool(refresh))


@app.get("/api/screen")
def api_screen():
    return market.screen()


@app.post("/api/screen/run")
def api_screen_run(auto: int = Query(0)):
    return market.start_screen(auto=bool(auto))


@app.post("/api/screen/stop")
def api_screen_stop():
    return market.stop_screen()


@app.get("/api/session")
def api_session():
    return {"in_session": market._in_session(), "now": market.now_vn().strftime("%H:%M %d/%m")}


@app.get("/api/symbols")
def api_symbols():
    return {"basket": market.BASKET}


@app.get("/api/symbol/{sym}")
def api_symbol(sym: str, refresh: int = Query(0)):
    return market.get_symbol(sym, refresh=bool(refresh), priority=bool(refresh))


@app.get("/api/symbol/{sym}/news")
def api_symbol_news(sym: str, refresh: int = Query(0)):
    return news.get_news(sym, refresh=bool(refresh))


@app.exception_handler(Exception)
def err(request, exc):  # noqa: ANN001
    return JSONResponse(status_code=500, content={"status": "error", "message": str(exc)})


app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="static")
