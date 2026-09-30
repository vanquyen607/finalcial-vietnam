from __future__ import annotations

import asyncio

import httpx

from app.config import settings
from app.services import notify as notify_svc
from app.services import poller as poller_mod
from app.services.notify import send_telegram


def run(handler) -> bool:
    async def go() -> bool:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            return await send_telegram(client, "tok", "123", "hello")
        finally:
            await client.aclose()

    return asyncio.run(go())


def test_send_telegram_ok():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "api.telegram.org/bottok/sendMessage" in str(request.url)
        return httpx.Response(200, json={"ok": True})

    assert run(handler) is True


def test_send_telegram_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False})

    assert run(handler) is False


def test_send_telegram_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    assert run(handler) is False


def test_send_telegram_skipped_without_config():
    async def go() -> bool:
        return await send_telegram(None, "", "", "x")  # type: ignore[arg-type]

    assert asyncio.run(go()) is False


def test_error_streak_alert_once_then_recovered(monkeypatch):
    monkeypatch.setattr(settings, "telegram_alert_after_sec", 600)
    pl = poller_mod.Poller()

    assert pl._check_error_streak(1000, False) is None  # bình thường
    assert pl._check_error_streak(1000, True) is None  # mới chết
    assert pl._check_error_streak(1500, True) is None  # chưa đủ 600s
    assert pl._check_error_streak(1600, True) == "alert"  # đủ ngưỡng -> báo 1 lần
    assert pl._check_error_streak(5000, True) is None  # vẫn chết -> không spam
    assert pl._check_error_streak(5100, False) == "recovered"  # sống lại
    assert pl._check_error_streak(5200, False) is None
    # chết lại từ đầu -> báo lại
    assert pl._check_error_streak(5200, True) is None
    assert pl._check_error_streak(5800, True) == "alert"

    async def close():
        await pl.provider.aclose()
        await pl._aux.aclose()

    asyncio.run(close())
