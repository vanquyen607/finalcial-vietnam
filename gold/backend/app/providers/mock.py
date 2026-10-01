from __future__ import annotations

import math
import random
import time
from datetime import date, timedelta

from ..symbols import GOLD_TYPES
from .base import GoldProvider, ProviderQuote

# Giá nền (VND/lượng, USD/ounce) — khớp mức thị trường 09/2026 để demo giống thật.
_BASE = {
    "SJL1L10": 140_500_000, "SJ9999": 140_000_000, "VNGSJC": 140_500_000,
    "DOHNL": 140_500_000, "DOHCML": 140_500_000, "DOJINHTV": 139_800_000,
    "PQHNVM": 140_200_000, "PQHN24NTT": 140_200_000,
    "BTSJC": 139_500_000, "BT9999NTT": 139_500_000,
    "VIETTINMSJC": 140_500_000,
    "XAUUSD": 4177.8,
}
_SPREAD = {"XAUUSD": 0.0}  # giá thế giới không có spread nội địa


class MockProvider(GoldProvider):
    """Mô phỏng giá chạy thật — dùng khi không có mạng hoặc GOLD_PROVIDER=mock."""

    name = "mock"

    def __init__(self) -> None:
        self._t = 0
        # Mọi mã trong GOLD_TYPES đều có giá nền (mã mới không trong _BASE thì ước lượng).
        self._level = {t["code"]: _BASE.get(
            t["code"], 140_000_000.0 if t["unit"] == "VND" else 4000.0) for t in GOLD_TYPES}
        self._prev = dict(self._level)

    def _step(self) -> None:
        self._prev = dict(self._level)
        self._t += 1
        for code, price in self._level.items():
            if code == "XAUUSD":
                drift = random.gauss(0, 0.0012)
            else:
                # Nội địa chỉ nhấp nhô vài trăm nghìn đến 1 triệu đồng.
                drift = random.gauss(0, 0.0004)
            wave = math.sin(self._t / 12.0 + hash(code) % 7) * 0.0006
            self._level[code] = price * (1 + drift + wave)

    async def fetch_current(self) -> list[ProviderQuote]:
        self._step()
        now = int(time.time())
        quotes: list[ProviderQuote] = []
        for meta in GOLD_TYPES:
            code = meta["code"]
            buy = self._level[code]
            sell = buy * (1 + _SPREAD.get(code, 0.021))  # spread nội địa ~2,1%
            prev = self._prev[code]
            if meta["unit"] == "VND":
                buy, sell = round(buy, -4), round(sell, -4)
                prev = round(prev, -4)
                step = 100_000
            else:
                buy, sell = round(buy, 2), round(sell, 2)
                prev = round(prev, 2)
                step = 0.1
            quotes.append(ProviderQuote(
                code=code, name=meta["name"], buy=buy, sell=sell,
                change_buy=round(buy - prev, 4) if step >= 1 else round(buy - prev, 4),
                change_sell=round(sell - prev, 4),
                unit=meta["unit"], per=meta["per"], source=self.name, updated_at=now,
            ))
        return quotes

    async def fetch_history(self, code: str, days: int) -> list[dict]:
        base = _BASE.get(code, 140_000_000)
        rnd = random.Random(code)
        today = date.today()
        rows = []
        price = base * (1 - rnd.uniform(0.00, 0.03))
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            prev = price
            price *= 1 + rnd.gauss(0, 0.004)
            rows.append({
                "date": d.isoformat(),
                "buy": round(price, -4) if base > 1e6 else round(price, 2),
                "sell": round(price * 1.021, -4) if base > 1e6 else round(price * 1.021, 2),
                "day_change_buy": round(price - prev, -4) if base > 1e6 else round(price - prev, 2),
                "day_change_sell": 0,
                "updates": rnd.randint(1, 6),
            })
        return rows
