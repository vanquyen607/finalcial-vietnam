from __future__ import annotations

import asyncio

import httpx

from app.providers.spot import FALLBACK, SCANNER, fetch_world_spot


def run(handler) -> tuple[float, float] | None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        return asyncio.run(fetch_world_spot(client))
    finally:
        asyncio.run(client.aclose())


def test_tradingview_is_preferred():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(SCANNER)
        return httpx.Response(200, json={"close": 4173.4, "change_abs": 19.3})

    assert run(handler) == (4173.4, 19.3)


def test_fallback_when_tradingview_fails():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "scanner.tradingview.com":
            return httpx.Response(500)
        assert str(request.url).startswith(FALLBACK)
        return httpx.Response(200, json={"price": 4180.05, "updatedAt": "just now"})

    assert run(handler) == (4180.05, 0.0)


def test_uses_next_symbol_when_first_fails():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        symbol = request.url.params.get("symbol", "")
        seen.append(symbol)
        if symbol == "OANDA:XAUUSD":
            return httpx.Response(500)
        if symbol == "TVC:GOLD":
            return httpx.Response(200, json={"close": 4180.28, "change_abs": -1.45})
        raise AssertionError(f"không nên gọi tới {symbol}")

    assert run(handler) == (4180.28, -1.45)
    assert seen == ["OANDA:XAUUSD", "TVC:GOLD"]


def test_returns_none_when_all_sources_dead():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    assert run(handler) is None


def test_ignores_non_positive_price():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "scanner.tradingview.com":
            return httpx.Response(200, json={"close": 0, "change_abs": 0})
        return httpx.Response(200, json={"price": 0})

    assert run(handler) is None
