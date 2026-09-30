from __future__ import annotations

import asyncio

import httpx

from app.providers.fx import PRIMARY, SECONDARY, fetch_usd_vnd


def run(handler) -> tuple[float, str] | None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        return asyncio.run(fetch_usd_vnd(client))
    finally:
        asyncio.run(client.aclose())


def test_primary_er_api():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(PRIMARY)
        return httpx.Response(200, json={"result": "success", "rates": {"VND": 26270.5}})

    assert run(handler) == (26270.5, "er-api")


def test_fallback_currency_api():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if str(request.url).startswith(PRIMARY):
            return httpx.Response(500)
        assert str(request.url).startswith(SECONDARY)
        return httpx.Response(200, json={"usd": {"vnd": 26310}})

    assert run(handler) == (26310.0, "currency-api")
    assert len(seen) == 2


def test_none_when_all_dead():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    assert run(handler) is None


def test_ignores_missing_vnd():
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).startswith(PRIMARY):
            return httpx.Response(200, json={"result": "success", "rates": {}})
        return httpx.Response(200, json={"usd": {}})

    assert run(handler) is None
