"""API phan tich chung khoan - Phan Tich CK."""
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import market, news

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="Phan Tich Co Phieu VN", version="1.0")


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
