from __future__ import annotations

import asyncio

from app.db import Database
from app.providers.base import GoldProvider, ProviderQuote
from app.providers.mock import MockProvider
from app.services import alerts as alerts_svc
from app.services import poller as poller_mod


def test_tick_with_mock_does_not_persist_or_alert(tmp_path, monkeypatch):
    temp_db = Database(tmp_path / "poller.db")
    monkeypatch.setattr(poller_mod, "db", temp_db)
    monkeypatch.setattr(alerts_svc, "db", temp_db)
    # Tắt tác vụ phụ (tỷ giá/tin) để test không chạm mạng.
    monkeypatch.setattr(poller_mod.settings, "fx_interval", 10 ** 9)
    monkeypatch.setattr(poller_mod.settings, "news_interval", 10 ** 9)
    temp_db.add_alert("SJL1L10", "up", 0.0001, "ngưỡng cực nhỏ để chắc chắn khớp")

    pl = poller_mod.Poller()
    pl.provider = MockProvider()

    async def scenario():
        try:
            return await pl.tick()
        finally:
            await pl.provider.aclose()
            await pl._aux.aclose()

    result = asyncio.run(scenario())
    temp_db.close()

    assert result["source"] == "mock"
    assert result["changed"] > 0
    # giá mock KHÔNG vào DB, alert KHÔNG kích hoạt trên giá giả
    assert result["events"] == 0
    check = Database(tmp_path / "poller.db")
    try:
        assert check.latest_quotes() == {}
        assert len(check.active_alerts()) == 1
    finally:
        check.close()
    # latest in-memory vẫn cập nhật để UI hiển thị (kèm cờ source=mock)
    assert set(pl.latest) != set()
    assert pl.status["source"] == "mock"


class FixedProvider(GoldProvider):
    """Nguồn không trả change (như 4 tiệm tư nhân) để test tự tính theo ngày."""

    name = "fixed"

    def __init__(self, buy: float) -> None:
        self.buy = buy

    async def fetch_current(self) -> list[ProviderQuote]:
        return [ProviderQuote(code="HT_24K", name="Huy Thanh 24K", buy=self.buy,
                              sell=self.buy + 1_000_000, change_buy=0, change_sell=0,
                              unit="VND", per="lượng", source="shops:ht")]


def test_tick_computes_day_change_for_sources_without_change(tmp_path, monkeypatch):
    temp_db = Database(tmp_path / "daychange.db")
    monkeypatch.setattr(poller_mod, "db", temp_db)
    monkeypatch.setattr(alerts_svc, "db", temp_db)
    monkeypatch.setattr(poller_mod.settings, "fx_interval", 10 ** 9)
    monkeypatch.setattr(poller_mod.settings, "news_interval", 10 ** 9)

    pl = poller_mod.Poller()
    provider = FixedProvider(100.0)
    pl.provider = provider

    async def scenario():
        try:
            await pl.tick()  # tick đầu ngày -> mốc mở cửa
            first = pl.latest["HT_24K"]["change_buy"]
            provider.buy = 110.0
            await pl.tick()
            return first, pl.latest["HT_24K"]["change_buy"]
        finally:
            await pl.provider.aclose()
            await pl._aux.aclose()

    first, second = asyncio.run(scenario())
    temp_db.close()

    assert first == 0
    assert second == 10.0
