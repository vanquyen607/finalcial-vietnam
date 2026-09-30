from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.ratelimit import RateLimitMiddleware
from .api.routes import router
from .config import settings
from .services.poller import poller

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aurum")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.enable_poller:
        await poller.start()
    else:
        log.warning("GOLD_ENABLE_POLLER=0 — worker API-only, đọc DB dùng chung.")
    try:
        yield
    finally:
        await poller.stop()


app = FastAPI(
    title="Aurum Terminal — Giá vàng realtime",
    version="1.0.0",
    description="Backend FastAPI: lấy giá vàng (SJC/DOJI/PNJ/XAU-USD), lưu SQLite, phát WebSocket.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
if settings.rate_limit_per_min > 0:
    app.add_middleware(RateLimitMiddleware)

app.include_router(router)


@app.get("/api")
async def api_root() -> JSONResponse:
    return JSONResponse({"endpoints": ["/api/health", "/api/symbols", "/api/quotes",
                                       "/api/quotes/{ref}", "/api/history/{ref}",
                                       "/api/alerts", "/ws"]})


# ---------- static frontend (SPA) ----------
STATIC_INDEX = settings.static_dir / "index.html"


def _mount_static() -> None:
    if not settings.static_dir.is_dir():
        log.warning("Chưa build frontend (%s chưa tồn tại) — API vẫn chạy.",
                    settings.static_dir)
        return
    app.mount("/assets", StaticFiles(directory=settings.static_dir / "assets"), name="assets")
    # File tĩnh còn lại (manifest, icon, sw.js…)
    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        candidate = settings.static_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        if STATIC_INDEX.is_file():
            return FileResponse(STATIC_INDEX)
        return JSONResponse({"detail": "Frontend chưa được build"}, status_code=404)


_mount_static()
