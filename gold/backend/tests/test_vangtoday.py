from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from app.providers.vangtoday import BASE_URL, HEADERS, VangTodayProvider

NOW = 1_790_740_809

CURRENT = {
    "success": True,
    "current_time": NOW,
    "data": [
        {"type_code": "SJL1L10", "buy": 144_600_000, "sell": 147_600_000,
         "change_buy": 100_000, "change_sell": 200_000},
        {"type_code": "XAUUSD", "buy": 4174.6, "sell": 0, "change_buy": 19.3, "change_sell": 0},
        {"type_code": "KHONG_CO_TRONG_DANH_MUC", "buy": 1, "sell": 2},
    ],
}

HISTORY = {
    "success": True,
    "history": [
        {"date": "2026-09-29", "prices": {"SJL1L10": {
            "buy": 145_000_000, "sell": 148_000_000,
            "day_change_buy": 400_000, "day_change_sell": 400_000, "updates": 3}}},
        {"date": "2026-09-28", "prices": {"SJL1L10": {
            "buy": 144_600_000, "sell": 147_600_000,
            "day_change_buy": 0, "day_change_sell": 0, "updates": 1}}},
        {"date": "2026-09-27", "prices": {}},
    ],
}


def make_provider(handler) -> VangTodayProvider:
    provider = VangTodayProvider()
    asyncio.run(provider.aclose())
    provider._client = httpx.AsyncClient(
        base_url=BASE_URL,
        headers=HEADERS,
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )
    return provider


def route(current: dict | None = None, history: dict | None = None,
          spot: dict | int | None = None):
    """Handler giả lập vang.today + nguồn spot."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "scanner.tradingview.com":
            if isinstance(spot, int):
                return httpx.Response(spot)
            if spot is None:
                return httpx.Response(503)
            return httpx.Response(200, json=spot)
        if request.url.host == "api.gold-api.com":
            return httpx.Response(503)
        if request.url.params.get("days"):
            return httpx.Response(200, json=history or {"success": True, "history": []})
        return httpx.Response(200, json=current or CURRENT)

    return handler


def test_fetch_current_upgrades_xauusd_with_spot():
    provider = make_provider(route(spot={"close": 4173.4, "change_abs": 18.9}))
    try:
        quotes = asyncio.run(provider.fetch_current())
    finally:
        asyncio.run(provider.aclose())

    by_code = {q.code: q for q in quotes}
    assert set(by_code) == {"SJL1L10", "XAUUSD"}  # mã lạ bị loại bỏ

    sjc = by_code["SJL1L10"]
    assert sjc.buy == 144_600_000
    assert sjc.source == "vangtoday"
    assert sjc.updated_at == NOW

    xau = by_code["XAUUSD"]
    assert (xau.buy, xau.change_buy) == (4173.4, 18.9)
    assert xau.source == "spot"
    assert abs(xau.updated_at - int(time.time())) < 60


def test_fetch_current_keeps_vangtoday_when_spot_dead():
    provider = make_provider(route(spot=503))
    try:
        quotes = asyncio.run(provider.fetch_current())
    finally:
        asyncio.run(provider.aclose())

    xau = next(q for q in quotes if q.code == "XAUUSD")
    assert (xau.buy, xau.change_buy) == (4174.6, 19.3)
    assert xau.source == "vangtoday"
    assert xau.updated_at == NOW


def test_fetch_current_rejects_bad_payload():
    provider = make_provider(route(current={"success": False, "error": "x"}))
    try:
        with pytest.raises(RuntimeError, match="success=false"):
            asyncio.run(provider.fetch_current())
    finally:
        asyncio.run(provider.aclose())

    provider = make_provider(route(current={"success": True, "data": []}))
    try:
        with pytest.raises(RuntimeError, match="data rỗng"):
            asyncio.run(provider.fetch_current())
    finally:
        asyncio.run(provider.aclose())


def test_fetch_history_sorted_and_skips_empty_days():
    provider = make_provider(route(history=HISTORY))
    try:
        rows = asyncio.run(provider.fetch_history("SJL1L10", days=30))
    finally:
        asyncio.run(provider.aclose())

    assert [r["date"] for r in rows] == ["2026-09-28", "2026-09-29"]
    assert rows[1]["buy"] == 145_000_000
    assert rows[1]["day_change_buy"] == 400_000
    assert rows[1]["updates"] == 3
