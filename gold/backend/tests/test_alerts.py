from __future__ import annotations

import pytest

from app.db import Database
from app.services import alerts as alerts_mod
from app.services.alerts import day_change_pct, evaluate


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    monkeypatch.setattr(alerts_mod, "db", db)
    yield db
    db.close()


def quote(buy: float, change: float) -> dict:
    return {"code": "SJL1L10", "name": "SJC 9999", "buy": buy, "sell": buy + 3_000_000,
            "change_buy": change, "change_sell": change}


def test_day_change_pct():
    assert day_change_pct(102, 2) == 2.0
    assert day_change_pct(98, -2) == -2.0
    assert day_change_pct(100, 0) == 0.0
    assert day_change_pct(0, 0) == 0.0


def test_up_alert_triggers_once(temp_db):
    alert = temp_db.add_alert("SJL1L10", "up", 1.0, "test")

    events = evaluate({"SJL1L10": quote(102, 2)})
    assert len(events) == 1
    ev = events[0]
    assert ev["alert_id"] == alert["id"]
    assert ev["pct"] == 2.0
    assert "tăng 2.00%" in ev["message"]
    assert temp_db.active_alerts() == []
    assert temp_db.list_alerts()[0]["triggered_at"] is not None

    # đã tắt -> không kích hoạt lại dù giá vẫn vượt ngưỡng
    assert evaluate({"SJL1L10": quote(102, 2)}) == []


def test_direction_and_threshold(temp_db):
    up = temp_db.add_alert("SJL1L10", "up", 1.0, "")
    down = temp_db.add_alert("SJL1L10", "down", 1.0, "")

    events = evaluate({"SJL1L10": quote(98, -2)})
    assert [e["alert_id"] for e in events] == [down["id"]]
    assert "giảm 2.00%" in events[0]["message"]
    assert [a["id"] for a in temp_db.active_alerts()] == [up["id"]]

    # bước giá nhỏ hơn ngưỡng -> không kích hoạt
    assert evaluate({"SJL1L10": quote(100.5, 0.4)}) == []
    assert [a["id"] for a in temp_db.active_alerts()] == [up["id"]]


def test_missing_quote_is_skipped(temp_db):
    temp_db.add_alert("KHAC_MA", "up", 1.0, "")
    assert evaluate({"SJL1L10": quote(200, 50)}) == []
    assert len(temp_db.active_alerts()) == 1


def test_db_alert_roundtrip(temp_db):
    a = temp_db.add_alert("XAUUSD", "down", 2.5, "chú ý")
    assert temp_db.list_alerts()[0]["id"] == a["id"]
    assert temp_db.delete_alert(a["id"]) is True
    assert temp_db.delete_alert(a["id"]) is False
    assert temp_db.list_alerts() == []
