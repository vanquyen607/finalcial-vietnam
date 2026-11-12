from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..config import settings
from ..db import db
from ..services import alerts as alerts_svc
from ..services import news as news_svc
from ..services.broadcast import hub
from ..services.poller import poller
from ..services.premium import SJC_CODE, compute_premium
from ..symbols import GOLD_TYPES, brand_groups, featured_types, resolve
from .deps import require_token

router = APIRouter(prefix="/api", tags=["api"])


# ---------- health / meta ----------
@router.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "app": "Aurum Terminal",
        "time": int(time.time()),
        "status": poller.status,
        "clients": hub.count,
    }


@router.get("/metrics", dependencies=[Depends(require_token)])
async def metrics() -> dict:
    """Quan sát vận hành: nhịp poll, lỗi từng nguồn, tỷ giá/tin, streak lỗi."""
    return {
        "ts": int(time.time()),
        "metrics": poller.metrics,
        "source": poller.status.get("source"),
        "polls": poller.status.get("polls"),
        "last_success": poller.status.get("last_success"),
        "last_error": poller.status.get("last_error"),
    }


@router.get("/symbols")
async def symbols(featured: bool = Query(False)) -> dict:
    items = featured_types() if featured else GOLD_TYPES
    groups = brand_groups(featured)
    brands = [{k: g[k] for k in ("brand", "label", "order", "count")} for g in groups]
    return {"count": len(items), "items": items, "brands": brands}


# ---------- quotes ----------
@router.get("/quotes")
async def quotes() -> dict:
    latest = poller.latest or db.latest_quotes()
    items = [latest[c] for c in latest]
    items.sort(key=lambda r: (r.get("code") or ""))
    return {"ts": int(time.time()), "source": poller.status.get("source"),
            "count": len(items), "items": items}


def _one(ref: str) -> dict:
    meta = resolve(ref)
    if meta is None:
        raise HTTPException(404, f"Không tìm thấy loại vàng: {ref}")
    latest = poller.latest or db.latest_quotes()
    row = latest.get(meta["code"])
    if row is None:
        raise HTTPException(503, "Chưa có dữ liệu giá (poller chưa chạy)")
    return row


@router.get("/quotes/{ref}")
async def quote_one(ref: str) -> dict:
    return _one(ref)


# ---------- history ----------
_SPARK_TTL = 60
_spark_cache: dict[int, tuple[int, dict]] = {}
_HIST_FAIL_TTL = 600
_hist_fail: dict[str, int] = {}


@router.get("/sparklines")
async def sparklines(hours: int = Query(24, ge=1, le=168)) -> dict:
    """Chuỗi giá intraday cho sparkline của từng mã (1 truy vấn cho mọi mã + cache 60s)."""
    now = int(time.time())
    cached = _spark_cache.get(hours)
    if cached and now - cached[0] < _SPARK_TTL:
        return cached[1]

    since = now - hours * 3600
    series = db.sparklines(since, [m["code"] for m in GOLD_TYPES])
    payload = {"since": since, "series": series,
               "count": sum(len(v) for v in series.values())}
    _spark_cache[hours] = (now, payload)
    return payload


@router.get("/history/{ref}")
async def history(ref: str, days: int = Query(30, ge=1, le=30)) -> dict:
    meta = resolve(ref)
    if meta is None:
        raise HTTPException(404, f"Không tìm thấy loại vàng: {ref}")
    code = meta["code"]

    daily = db.daily(code, days)
    now = int(time.time())
    # Chỉ gọi mạng khi nguồn thật sự có history và chưa fail gần đây.
    if len(daily) < min(days, 3) and poller.provider.supports_history(code):
        if now - _hist_fail.get(code, 0) <= _HIST_FAIL_TTL:
            if not daily:
                raise HTTPException(502, "Nguồn lịch sử đang lỗi, thử lại sau")
        else:
            try:
                rows = await poller.provider.fetch_history(code, days)
                db.upsert_daily([{"code": code, **r} for r in rows if r.get("date")])
                daily = db.daily(code, days)
                _hist_fail.pop(code, None)
            except Exception as exc:  # noqa: BLE001
                _hist_fail[code] = now
                if not daily:
                    raise HTTPException(502, f"Không lấy được lịch sử: {exc}") from exc

    since = int(time.time()) - 24 * 3600
    ticks = db.series(code, since)
    return {
        "code": code, "meta": meta, "days": days,
        "daily": daily,
        "intraday": [{"ts": t["ts"], "buy": t["buy"], "sell": t["sell"]} for t in ticks],
        "source": poller.status.get("source"),
    }


# ---------- premium (chênh lệch SJC - thế giới) ----------
@router.get("/premium")
async def premium() -> dict:
    latest = poller.latest or db.latest_quotes()
    sjc = latest.get(SJC_CODE)
    xau = latest.get("XAUUSD")
    fx = db.latest_fx()
    if sjc is None or xau is None or fx is None:
        raise HTTPException(503, "Chưa đủ dữ liệu (giá SJC / XAUUSD / tỷ giá)")
    gap = compute_premium(sjc["sell"], xau["buy"], fx["usd_vnd"])
    if gap is None:
        raise HTTPException(503, "Dữ liệu giá chưa hợp lệ để tính chênh lệch")
    return {
        "ts": int(time.time()),
        "sjc": {"code": SJC_CODE, "name": sjc["name"], "sell": sjc["sell"], "source": sjc["source"]},
        "xau": {"buy": xau["buy"], "source": xau["source"]},
        "fx": {"usd_vnd": fx["usd_vnd"], "source": fx["source"], "ts": fx["ts"]},
        **gap,
    }


# ---------- news ----------
@router.get("/news")
async def news(limit: int = Query(30, ge=1, le=100)) -> dict:
    items = db.list_news(limit)
    if not items:
        # DB trống (vừa khởi động): kéo trực tiếp một lần cho có tin ngay.
        try:
            await news_svc.refresh_news(poller._aux)
            items = db.list_news(limit)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"Không lấy được tin tức: {exc}") from exc
    return {"count": len(items), "items": items}


# ---------- alerts ----------
class AlertIn(BaseModel):
    code: str = Field(description="type_code hoặc alias, ví dụ: sjc | SJL1L10 | xauusd")
    direction: str = Field(pattern="^(up|down)$")
    threshold: float = Field(default=0, ge=0, le=100, description="% thay đổi trong ngày (0 = dùng giá tuyệt đối)")
    note: str = ""
    target_price: float | None = Field(default=None, gt=0, description="Giá mua mục tiêu (VND/USD); nếu có thì bỏ qua %")


@router.get("/alerts")
async def list_alerts() -> dict:
    return {"items": db.list_alerts()}


@router.post("/alerts", status_code=201, dependencies=[Depends(require_token)])
async def create_alert(body: AlertIn) -> dict:
    meta = resolve(body.code)
    if meta is None:
        raise HTTPException(404, f"Không tìm thấy loại vàng: {body.code}")
    if body.target_price is None and body.threshold <= 0:
        raise HTTPException(422, "Cần ngưỡng % > 0 hoặc giá mục tiêu > 0")
    row = db.add_alert(meta["code"], body.direction, round(body.threshold, 4),
                       body.note.strip(), body.target_price)
    row["name"] = meta["name"]
    return row


@router.delete("/alerts/{alert_id}", dependencies=[Depends(require_token)])
async def delete_alert(alert_id: int) -> dict:
    if not db.delete_alert(alert_id):
        raise HTTPException(404, "Không tồn tại alert")
    return {"deleted": alert_id}


@router.patch("/alerts/{alert_id}", dependencies=[Depends(require_token)])
async def toggle_alert(alert_id: int, active: bool = Query(...)) -> dict:
    if not db.set_alert_active(alert_id, active):
        raise HTTPException(404, "Không tồn tại alert")
    return {"id": alert_id, "active": active}


# ---------- debug (chẩn đoán nguồn) ----------
@router.get("/debug/kimtin", dependencies=[Depends(require_token)])
async def debug_kimtin() -> dict:
    import httpx
    from bs4 import BeautifulSoup
    url = "https://kimtin.com.vn/"
    try:
        async with httpx.AsyncClient(headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "vi,en;q=0.8",
        }, timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url)
        html = resp.text
        soup = BeautifulSoup(html, "lxml")
        panels = [p.get("id") for p in soup.select("[id^='gold-area-panel']")]
        tables = soup.find_all("table")
        has_sjc = "VÀNG MIẾNG SJC" in html.upper()
        return {
            "status_code": resp.status_code,
            "content_length": len(html),
            "panels": panels,
            "table_count": len(tables),
            "has_sjc_text": has_sjc,
            "final_url": str(resp.url),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


# ---------- WebSocket ----------
@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket, topics: str = "quote,status,alert") -> None:
    wanted = {t.strip() for t in topics.split(",") if t.strip()} or {"quote"}
    await hub.connect(ws, wanted)
    try:
        # Gửi snapshot ngay khi kết nối để client không phải chờ tick.
        await ws.send_text(json.dumps({
            "type": "snapshot", "ts": int(time.time()),
            "quotes": list((poller.latest or db.latest_quotes()).values()),
            "status": poller.status,
        }, ensure_ascii=False))
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("op") == "subscribe":
                current = set(msg.get("topics") or wanted)
                await hub.set_topics(ws, current)
                await ws.send_text(json.dumps({"type": "subscribed", "topics": sorted(current)}))
            elif msg.get("op") == "ping":
                await ws.send_text(json.dumps({"type": "pong", "ts": int(time.time())}))
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(ws)
