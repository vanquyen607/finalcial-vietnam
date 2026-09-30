from __future__ import annotations

import math
import time

import httpx

from ..config import settings
from .base import GoldProvider, ProviderQuote, raw_snapshot_to_quotes
from .spot import fetch_world_spot

BASE_URL = "https://vang.today/api/prices"
# vang.today yêu cầu UA hợp lệ, không thì trả rỗng.
HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)", "Accept": "application/json"}


def _num(value: object) -> float | None:
    """Ép số, trả None khi không phải số hữu hạn (chống payload bẩn)."""
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def clean_rows(rows: object) -> list[dict]:
    """Lọc hàng giá hợp lệ: type_code chuỗi + buy là số hữu hạn.
    Các trường phụ thiếu/sai -> 0.0. Hàng không phải dict -> bỏ."""
    out: list[dict] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = row.get("type_code")
        buy = _num(row.get("buy"))
        if not code or not isinstance(code, str) or buy is None:
            continue
        out.append({
            "type_code": code,
            "buy": buy,
            "sell": _num(row.get("sell")) or 0.0,
            "change_buy": _num(row.get("change_buy")) or 0.0,
            "change_sell": _num(row.get("change_sell")) or 0.0,
        })
    return out


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
        rows = clean_rows(rows)
        if not rows:
            raise RuntimeError("vang.today trả data rỗng hoặc không hợp lệ")
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
            if not isinstance(day, dict):
                continue
            entry = (day.get("prices") or {}).get(code)
            if not isinstance(entry, dict):
                continue
            buy = _num(entry.get("buy"))
            if buy is None:
                continue
            out.append({
                "date": day.get("date"),
                "buy": buy,
                "sell": _num(entry.get("sell")) or 0.0,
                "day_change_buy": _num(entry.get("day_change_buy")) or 0.0,
                "day_change_sell": _num(entry.get("day_change_sell")) or 0.0,
                "updates": int(_num(entry.get("updates")) or 0),
            })
        out.sort(key=lambda r: r["date"] or "")
        return out

    async def aclose(self) -> None:
        await self._client.aclose()


def now_epoch() -> int:
    return int(time.time())
