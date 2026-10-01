from __future__ import annotations

import asyncio

import httpx
import pytest

from app.db import Database
from app.providers.base import GoldProvider, ProviderQuote
from app.providers.composite import MergedProvider
from app.providers.ngoctham import NgocThamProvider, parse_nt_time
from app.providers.simplize import SimplizeProvider

HTML = '<html><script>{"buildId":"abc123"}</script></html>'

PRODUCT_TMPL = {
    "pageProps": {
        "listData": [{
            "symbol": "X", "name": "Test", "modifiedTime": 1_790_757_857_609,
            "priceBuy": 141_500_000, "priceSell": 142_500_000,
            "priceBuyChg": 500_000, "priceSellChg": 0,
        }]
    }
}

NT_JSON = {
    "date": "2026-09-30 14:41:00",
    "chitiet": [
        {"loaivang": "Nhẫn 999.9", "giamua": "13450000", "giaban": "13800000"},
        {"loaivang": "Vàng Miếng SJC (Loại 10 chỉ)", "giamua": "14000000", "giaban": "14350000"},
        {"loaivang": "Vàng Ta 990", "giamua": "x", "giaban": "y"},
    ],
}


def run(provider, coro):
    async def go():
        try:
            return await coro
        finally:
            await provider.aclose()

    return asyncio.run(go())


def test_simplize_parses_products_and_caches():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "_next/data" in str(request.url):
            return httpx.Response(200, json=PRODUCT_TMPL)
        return httpx.Response(200, text=HTML)

    p = SimplizeProvider()
    p._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        quotes = asyncio.run(p.fetch_current())
        n_calls = len(calls)
        quotes2 = asyncio.run(p.fetch_current())  # cache -> không gọi thêm
    finally:
        asyncio.run(p._client.aclose())

    assert {q.code for q in quotes} == {"MH_SJC", "MH_9999", "BTMH_9999", "PQ_SJC", "PQ_9999"}
    mh = next(q for q in quotes if q.code == "MH_9999")
    assert (mh.buy, mh.sell, mh.change_buy) == (141_500_000, 142_500_000, 500_000)
    assert mh.source == "simplize"
    assert mh.updated_at == 1_790_757_857
    assert quotes2 == quotes
    assert len(calls) == n_calls  # lần 2 không gọi mạng


def test_simplize_raises_when_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        if "_next/data" in str(request.url):
            return httpx.Response(200, json={"pageProps": {"listData": []}})
        return httpx.Response(200, text=HTML)

    p = SimplizeProvider()
    p._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(RuntimeError):
            asyncio.run(p.fetch_current())
    finally:
        asyncio.run(p._client.aclose())


def test_ngoctham_converts_chi_to_luong_and_etag():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "if-none-match" in request.headers:
            return httpx.Response(304)
        return httpx.Response(200, json=NT_JSON, headers={"ETag": '"v1"'})

    p = NgocThamProvider()
    p._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        quotes = asyncio.run(p.fetch_current())
        quotes2 = asyncio.run(p.fetch_current())  # TTL còn hiệu lực
        p._cache_ts = 0  # ép hết TTL -> gọi lại, server 304
        quotes3 = asyncio.run(p.fetch_current())
    finally:
        asyncio.run(p._client.aclose())

    assert {q.code for q in quotes} == {"NT_9999", "NT_SJC"}
    nt = next(q for q in quotes if q.code == "NT_9999")
    assert (nt.buy, nt.sell) == (134_500_000.0, 138_000_000.0)
    assert nt.updated_at == parse_nt_time("2026-09-30 14:41:00")
    assert quotes2 == quotes and quotes3 == quotes
    assert len(calls) == 2  # lần 2 dùng cache, lần 3 gặp 304
    assert parse_nt_time("không phải ngày") is None


class _Ok(GoldProvider):
    name = "ok"

    def __init__(self, quotes):
        self._q = quotes

    async def fetch_current(self):
        return self._q


class _Dead(GoldProvider):
    name = "dead"

    async def fetch_current(self):
        raise RuntimeError("chết")


class _NoHist(GoldProvider):
    name = "nohist"

    async def fetch_current(self):
        return []


def q(code: str) -> ProviderQuote:
    return ProviderQuote(code=code, name=code, buy=1, sell=2, change_buy=0,
                         change_sell=0, unit="VND", per="lượng", source="t")


def test_merged_provider_partial_failure():
    m = MergedProvider([_Dead(), _Ok([q("A")]), _Ok([q("B")])])
    out = asyncio.run(m.fetch_current())
    assert [x.code for x in out] == ["A", "B"]
    asyncio.run(m.aclose())


def test_merged_provider_all_dead():
    m = MergedProvider([_Dead()])
    with pytest.raises(RuntimeError, match="mọi provider"):
        asyncio.run(m.fetch_current())
    asyncio.run(m.aclose())


def test_merged_history_delegates():
    m = MergedProvider([_NoHist(), _Dead()])
    with pytest.raises(NotImplementedError):
        asyncio.run(m.fetch_history("X", 3))
    asyncio.run(m.aclose())


def test_upsert_daily_snapshot_preserves_updates(tmp_path):
    db = Database(tmp_path / "snap.db")
    try:
        db.upsert_daily([{"code": "MH_SJC", "date": "2026-09-30", "buy": 1, "sell": 2,
                          "day_change_buy": 0, "day_change_sell": 0, "updates": 5}])
        db.upsert_daily_snapshot([{"code": "MH_SJC", "date": "2026-09-30", "buy": 10,
                                   "sell": 20, "day_change_buy": 1, "day_change_sell": 2}])
        rows = db.daily("MH_SJC", 5)
        assert len(rows) == 1
        assert (rows[0]["buy"], rows[0]["sell"]) == (10, 20)
        assert rows[0]["updates"] == 5  # giữ nguyên bộ đếm
        # ngày mới -> thêm dòng
        db.upsert_daily_snapshot([{"code": "MH_SJC", "date": "2026-10-01", "buy": 11,
                                   "sell": 21, "day_change_buy": 0, "day_change_sell": 0}])
        assert len(db.daily("MH_SJC", 5)) == 2
    finally:
        db.close()
