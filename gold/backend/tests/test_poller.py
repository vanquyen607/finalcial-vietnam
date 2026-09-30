from __future__ import annotations

import asyncio

from app.db import Database
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
