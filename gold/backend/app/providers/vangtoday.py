from __future__ import annotations

import time

import httpx

from ..config import settings
from .base import GoldProvider, ProviderQuote, raw_snapshot_to_quotes
from .spot import fetch_world_spot

BASE_URL = "https://vang.today/api/prices"
# vang.today yêu cầu UA hợp lệ, không thì trả rỗng.
HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)", "Accept": "application/json"}


class VangTodayProvider(GoldProvider):
    """vang.today — API miễn phí, không cần key; giá nội địa đổi ~30 phút/lần."""

    name = "vangtoday"

    def __init__(self, timeout: float | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=HEADERS,
            timeout=timeout or settings.provider_timeout,
            follow_redirects=True,
        )

    async def fetch_current(self) -> list[ProviderQuote]:
        resp = await self._client.get("", params={"action": "current"})
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("success"):
            raise RuntimeError(f"vang.today trả success=false: {payload}")
        rows = payload.get("data") or []
        if not rows:
            raise RuntimeError("vang.today trả data rỗng")
        quotes = raw_snapshot_to_quotes(rows, source=self.name, updated_at=payload.get("current_time"))
        await self._upgrade_world_spot(quotes)
        return quotes

    async def _upgrade_world_spot(self, quotes: list[ProviderQuote]) -> None:
        """Ghi đè XAUUSD bằng giá spot realtime (vang.today cập nhật ~30 phút/lần)."""
        spot = await fetch_world_spot(self._client)
        if not spot:
            return
        price, change = spot
        now = int(time.time())
        for q in quotes:
            if q.code == "XAUUSD" and price > 0:
                q.buy = price
                q.change_buy = change
                q.source = "spot"
                q.updated_at = now
                return

    async def fetch_history(self, code: str, days: int) -> list[dict]:
        """Một lần gọi trả lịch sử của toàn bộ mã theo ngày (<=30 ngày)."""
        resp = await self._client.get("", params={"days": max(1, min(days, 30)), "type": code})
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("success"):
            raise RuntimeError(f"vang.today history success=false: {payload}")

        out: list[dict] = []
        for day in payload.get("history") or []:
            entry = (day.get("prices") or {}).get(code)
            if not entry:
                continue
            out.append({
                "date": day.get("date"),
                "buy": float(entry.get("buy") or 0),
                "sell": float(entry.get("sell") or 0),
                "day_change_buy": float(entry.get("day_change_buy") or 0),
                "day_change_sell": float(entry.get("day_change_sell") or 0),
                "updates": int(entry.get("updates") or 0),
            })
        out.sort(key=lambda r: r["date"] or "")
        return out

    async def aclose(self) -> None:
        await self._client.aclose()


def now_epoch() -> int:
    return int(time.time())
