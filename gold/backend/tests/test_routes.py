from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes
from app.config import settings
from app.db import Database
from app.services.poller import poller


def sjc_row(sell: float = 143_500_000) -> dict:
    return {"ts": 1_790_750_000, "code": "SJL1L10", "name": "SJC 9999",
            "buy": 140_500_000, "sell": sell, "change_buy": 1_000_000,
            "change_sell": 1_000_000, "unit": "VND", "per": "lượng", "source": "vangtoday"}


def xau_row(buy: float = 4194.975) -> dict:
    return {"ts": 1_790_750_000, "code": "XAUUSD", "name": "Giá vàng thế giới",
            "buy": buy, "sell": 0, "change_buy": 14.0, "change_sell": 0,
            "unit": "USD", "per": "ounce", "source": "spot"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    temp_db = Database(tmp_path / "routes.db")
    monkeypatch.setattr(routes, "db", temp_db)
    monkeypatch.setattr(poller, "latest", {})
    # cache module-level không được rò giữa các test
    routes._spark_cache.clear()
    routes._hist_fail.clear()
    app = FastAPI()
    app.include_router(routes.router)
    yield TestClient(app, raise_server_exceptions=False), temp_db
    temp_db.close()


def test_premium_endpoint_math(client, monkeypatch):
    c, temp_db = client
    monkeypatch.setattr(poller, "latest", {"SJL1L10": sjc_row(), "XAUUSD": xau_row()})
    temp_db.insert_fx(26_000.0, "test")

    r = c.get("/api/premium")
    assert r.status_code == 200
    body = r.json()
    expected_world = round(4194.975 * 26_000.0 * (37.5 / 31.1034768))
    assert body["world_vnd_luong"] == expected_world
    assert body["gap_abs"] == round(143_500_000 - expected_world)
    assert body["fx"]["usd_vnd"] == 26_000.0


def test_premium_503_without_fx(client, monkeypatch):
    c, _temp_db = client
    monkeypatch.setattr(poller, "latest", {"SJL1L10": sjc_row(), "XAUUSD": xau_row()})
    r = c.get("/api/premium")
    assert r.status_code == 503


def test_news_endpoint_from_db(client):
    c, temp_db = client
    now = int(time.time())
    temp_db.upsert_news([
        {"link": "https://ex.com/1", "title": "Giá vàng tăng", "source": "T",
         "published": now, "image": "", "fetched_at": now},
        {"link": "https://ex.com/2", "title": "Vàng thế giới", "source": "T",
         "published": now - 60, "image": "", "fetched_at": now},
    ])
    r = c.get("/api/news?limit=1")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["items"][0]["link"] == "https://ex.com/1"


def test_create_alert_requires_token_when_set(client, monkeypatch):
    c, temp_db = client
    monkeypatch.setattr(settings, "api_token", "tok")
    payload = {"code": "sjc", "direction": "up", "threshold": 1.5, "note": "t"}

    assert c.post("/api/alerts", json=payload).status_code == 401
    r = c.post("/api/alerts", json=payload, headers={"X-Api-Token": "tok"})
    assert r.status_code == 201
    assert r.json()["code"] == "SJL1L10"
    assert len(temp_db.list_alerts()) == 1


def test_create_alert_open_when_token_unset(client, monkeypatch):
    c, _temp_db = client
    monkeypatch.setattr(settings, "api_token", "")
    payload = {"code": "xauusd", "direction": "down", "threshold": 2.0}
    assert c.post("/api/alerts", json=payload).status_code == 201


def test_quote_unknown_code_404(client):
    c, _temp_db = client
    assert c.get("/api/quotes/khong-co-ma-nay").status_code == 404


def test_quotes_from_poller_latest(client, monkeypatch):
    c, _temp_db = client
    monkeypatch.setattr(poller, "latest", {"XAUUSD": xau_row()})
    r = c.get("/api/quotes")
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_sparklines_downsampled_in_one_pass(client):
    c, temp_db = client
    now = int(time.time())
    temp_db.insert_quotes([
        {"ts": now - 3600 + i, "code": "SJL1L10", "name": "SJC 9999", "buy": 100 + i,
         "sell": 0, "change_buy": 0, "change_sell": 0, "unit": "VND", "per": "lượng",
         "source": "test"}
        for i in range(300)
    ])
    body = c.get("/api/sparklines?hours=1").json()
    pts = body["series"]["SJL1L10"]
    assert 1 < len(pts) <= 60
    assert body["count"] == len(pts)
    assert pts[0]["buy"] == 100
    assert pts[-1]["buy"] == 395


class _NoHistoryProvider:
    name = "nohist"

    def supports_history(self, code: str) -> bool:
        return False

    async def fetch_history(self, code: str, days: int) -> list[dict]:
        raise AssertionError("không được gọi mạng cho mã không hỗ trợ history")


def test_history_skips_network_when_provider_has_no_history(client, monkeypatch):
    c, _temp_db = client
    monkeypatch.setattr(poller, "provider", _NoHistoryProvider())
    r = c.get("/api/history/HT_24K")
    assert r.status_code == 200
    assert r.json()["daily"] == []


class _FailingHistoryProvider:
    name = "failing"

    def __init__(self) -> None:
        self.calls = 0

    def supports_history(self, code: str) -> bool:
        return True

    async def fetch_history(self, code: str, days: int) -> list[dict]:
        self.calls += 1
        raise RuntimeError("boom")


def test_history_negative_cache_avoids_repeat_calls(client, monkeypatch):
    c, _temp_db = client
    provider = _FailingHistoryProvider()
    monkeypatch.setattr(poller, "provider", provider)

    assert c.get("/api/history/SJL1L10").status_code == 502
    assert c.get("/api/history/SJL1L10").status_code == 502
    assert provider.calls == 1


def test_symbols_returns_ordered_brands(client):
    c, _temp_db = client
    r = c.get("/api/symbols")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["items"])
    brands = body["brands"]
    assert [b["order"] for b in brands] == sorted(b["order"] for b in brands)
    assert brands[0]["label"] == "Vàng thế giới"
    assert {b["brand"] for b in brands} == {i["brand"] for i in body["items"]}
    assert sum(b["count"] for b in brands) == body["count"]
    # mọi item đều có product để bảng giá gộp theo nhà bán hiển thị đúng sản phẩm
    assert all(i.get("product") for i in body["items"])
