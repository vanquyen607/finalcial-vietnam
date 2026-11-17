"""Cache cho dữ liệu phụ (bạc / tỷ giá / xăng dầu) phục vụ GET /api/extras.

Mỗi mục có TTL riêng theo nhịp cập nhật của nguồn; lỗi nguồn thì trả bản
cache gần nhất (kèm cờ stale) thay vì làm hỏng cả trang.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable

import httpx

from ..db import db
from ..providers import extras as extras_src

log = logging.getLogger("aurum.extras_svc")

HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)"}
OZ_PER_LUONG = 37.5 / 31.1034768  # 1 lượng = 37,5 g; 1 troy ounce = 31,1034768 g

TTL = {"silver": 120, "silver_domestic": 600, "fx": 1800, "fuel": 3600}

_cache: dict[str, tuple[int, Any]] = {}
_lock = asyncio.Lock()


async def _section(key: str, now: int, fetch: Callable[[httpx.AsyncClient], Awaitable[Any]],
                   client: httpx.AsyncClient) -> dict | None:
    ts, data = _cache.get(key, (0, None))
    if data is not None and now - ts < TTL[key]:
        return {"ts": ts, "stale": False, **_wrap(key, data)}
    fresh = await fetch(client)
    if fresh is None:
        if data is None:
            return None
        return {"ts": ts, "stale": True, **_wrap(key, data)}
    _cache[key] = (now, fresh)
    return {"ts": now, "stale": False, **_wrap(key, fresh)}


def _wrap(key: str, data: Any) -> dict:
    if key == "silver":
        out = dict(data)
        fx = db.latest_fx()
        if fx and fx.get("usd_vnd"):
            out["vnd_per_luong"] = round(data["price_usd"] * fx["usd_vnd"] * OZ_PER_LUONG)
        return out
    if key == "fx":
        return {"source": "Vietcombank", "items": data}
    if key == "silver_domestic":
        return {"source": "Hãng + WebGia", "items": data}
    return {"source": "Petrolimex", "items": data}


async def get_extras() -> dict:
    """Trả payload cho /api/extras; từng mục độc lập, mục nào lỗi thì vắng mặt."""
    now = int(time.time())
    async with _lock:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
            silver, silver_domestic, fx, fuel = await asyncio.gather(
                _section("silver", now, extras_src.fetch_silver, client),
                _section("silver_domestic", now, extras_src.fetch_silver_domestic, client),
                _section("fx", now, extras_src.fetch_fx, client),
                _section("fuel", now, extras_src.fetch_fuel, client),
            )
    return {"ts": now, "silver": silver, "silver_domestic": silver_domestic,
            "fx": fx, "fuel": fuel}
