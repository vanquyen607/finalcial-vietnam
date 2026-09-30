from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.deps import require_token
from app.api.ratelimit import RateLimitMiddleware
from app.config import settings


def make_request(token: str | None) -> Request:
    headers = [(b"x-api-token", token.encode())] if token else []
    return Request({"type": "http", "method": "POST", "headers": headers})


def test_require_token_open_when_unset(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "")
    asyncio.run(require_token(None))  # không ném


def test_require_token_accepts_correct(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret")
    asyncio.run(require_token("secret"))


def test_require_token_rejects_wrong_or_missing(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret")
    with pytest.raises(HTTPException) as ei:
        asyncio.run(require_token("sai"))
    assert ei.value.status_code == 401
    with pytest.raises(HTTPException) as ei2:
        asyncio.run(require_token(None))
    assert ei2.value.status_code == 401


def test_require_token_reads_header(monkeypatch):
    """Dependency đọc đúng header X-Api-Token (không phân biệt hoa thường)."""
    monkeypatch.setattr(settings, "api_token", "secret")
    req = make_request("secret")
    assert req.headers.get("x-api-token") == "secret"


def test_rate_limit_sliding_window():
    mw = RateLimitMiddleware(app=None)
    now = 1_000.0
    assert mw.allowed("1.2.3.4", now, limit=3) is True
    assert mw.allowed("1.2.3.4", now + 1, limit=3) is True
    assert mw.allowed("1.2.3.4", now + 2, limit=3) is True
    assert mw.allowed("1.2.3.4", now + 3, limit=3) is False  # vượt 3/phút
    assert mw.allowed("5.6.7.8", now + 3, limit=3) is True  # IP khác không ảnh hưởng
    assert mw.allowed("1.2.3.4", now + 61, limit=3) is True  # qua cửa sổ -> mở lại
    assert mw.allowed("9.9.9.9", now, limit=0) is True  # limit 0 = tắt


def test_rate_limit_prunes_old_entries():
    mw = RateLimitMiddleware(app=None)
    assert mw.allowed("ip", 0.0, limit=1) is True
    assert mw.allowed("ip", 1.0, limit=1) is False
    assert mw.allowed("ip", 60.0, limit=1) is True
    assert len(mw._hits["ip"]) == 1
