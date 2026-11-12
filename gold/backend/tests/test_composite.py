from __future__ import annotations

import asyncio
import time

import pytest

from app.providers.base import GoldProvider, ProviderQuote
from app.providers.composite import MergedProvider
from app.providers.vangtoday import HISTORY_CODES


def quote(code: str = "SJL1L10") -> ProviderQuote:
    return ProviderQuote(code=code, name=code, buy=100, sell=110, change_buy=0,
                         change_sell=0, unit="VND", per="lượng", source="t")


class GoodProvider(GoldProvider):
    name = "good"

    async def fetch_current(self) -> list[ProviderQuote]:
        return [quote()]


class BadProvider(GoldProvider):
    name = "bad"

    async def fetch_current(self) -> list[ProviderQuote]:
        raise RuntimeError("boom")


class SlowProvider(GoldProvider):
    name = "slow"

    async def fetch_current(self) -> list[ProviderQuote]:
        await asyncio.sleep(5)
        return [quote()]


class HistProvider(GoldProvider):
    name = "hist"

    async def fetch_current(self) -> list[ProviderQuote]:
        return []

    def supports_history(self, code: str) -> bool:
        return code == "SJL1L10"

    async def fetch_history(self, code: str, days: int) -> list[dict]:
        return [{"date": "2026-01-01", "buy": 1.0}]


def test_fetch_current_parallel_and_health():
    merged = MergedProvider([SlowProvider(), BadProvider(), GoodProvider()], timeout=0.2)
    started = time.perf_counter()
    quotes = asyncio.run(merged.fetch_current())
    elapsed = time.perf_counter() - started

    assert [q.code for q in quotes] == ["SJL1L10"]
    # nguồn chậm bị timeout, nguồn lỗi được ghi riêng, nguồn tốt vẫn trả dữ liệu
    assert set(merged.last_errors) == {"slow", "bad"}
    assert "good" in merged.last_ok
    # song song + timeout 0.2s -> không chờ 5s của nguồn chậm
    assert elapsed < 2.0


def test_fetch_current_raises_when_all_dead():
    merged = MergedProvider([BadProvider()])
    with pytest.raises(RuntimeError):
        asyncio.run(merged.fetch_current())


def test_history_only_delegates_to_supporting_provider():
    merged = MergedProvider([GoodProvider(), HistProvider()])
    assert merged.supports_history("SJL1L10")
    assert not merged.supports_history("HT_24K")
    assert asyncio.run(merged.fetch_history("SJL1L10", 5))[0]["date"] == "2026-01-01"
    with pytest.raises(NotImplementedError):
        asyncio.run(merged.fetch_history("HT_24K", 5))


def test_vangtoday_history_codes_are_exact():
    # 4 tiệm tư nhân + các mã Simplize/Ngọc Thẩm không có history trên vang.today
    assert "SJL1L10" in HISTORY_CODES
    assert "XAUUSD" in HISTORY_CODES
    assert "HT_24K" not in HISTORY_CODES
    assert "KTH_RING9999" not in HISTORY_CODES
