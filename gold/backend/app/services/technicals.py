"""Cache 60 giây cho chỉ số kỹ thuật TradingView (GET /api/technicals).

Điểm Recommend của TradingView thay đổi chậm (theo nến đóng), 60 giây là
quá đủ; lỗi nguồn thì trả bản cache gần nhất kèm cờ stale.
"""
from __future__ import annotations

import asyncio
import logging
import time

import httpx

from ..providers import technicals as tech_src

log = logging.getLogger("aurum.technicals_svc")

TTL = 60

_cache: tuple[int, dict] | None = None
_lock = asyncio.Lock()


async def get_technicals() -> dict | None:
    global _cache
    now = int(time.time())
    async with _lock:
        if _cache is not None and now - _cache[0] < TTL:
            return {"ts": _cache[0], "stale": False, **_cache[1]}
        async with httpx.AsyncClient() as client:
            fresh = await tech_src.fetch_technicals(client)
        if fresh is None:
            if _cache is None:
                return None
            return {"ts": _cache[0], "stale": True, **_cache[1]}
        _cache = (now, fresh)
        return {"ts": now, "stale": False, **fresh}
