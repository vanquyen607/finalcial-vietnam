from __future__ import annotations

import asyncio

import httpx
import pytest

from app.db import Database
from app.providers.base import GoldProvider, ProviderQuote
from app.providers.composite import MergedProvider
from app.providers.ngoctham import NgocThamProvider, parse_nt_time
from app.providers import privateshops
from app.providers.privateshops import (
    PrivateShopsProvider,
    ShopSpec,
    parse_huythanh,
    parse_kimnganphuc,
    parse_kimthanh,
    parse_kimtin,
)
from app.providers.simplize import PRODUCTS, SimplizeProvider

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

    assert {q.code for q in quotes} == set(PRODUCTS)
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


HT_HTML = """
<table>
<tr><th>Loại vàng</th><th>Giá mua</th><th>Giá bán</th></tr>
<tr><td>Vàng Huy Thanh 24k</td><td>13.450.000 VNĐ</td><td>13.850.000 VNĐ</td></tr>
<tr><td>Vàng thị trường 24k</td><td>12.750.000 VNĐ</td><td>-</td></tr>
<tr><td>Giá nguyên liệu 22K</td><td>12.320.000 VNĐ</td><td>12.687.000 VNĐ</td></tr>
</table>
"""

KT_HTML = """
<div id="gold-area-panel-HN" class="gold-area-panel active">
<table>
<tr><th>Thương phẩm</th><th>Tên sản phẩm</th><th>Hàm lượng</th><th>Mua vào</th><th>Bán ra</th></tr>
<tr><td>NHẪN TRÒN TRƠN</td><td>Vàng Rồng Kim Tín 999.9</td><td>999.9 (24K)</td><td>12802</td><td>13098</td></tr>
<tr><td>Vàng SJC</td><td>VÀNG MIẾNG SJC</td><td>999.9 (24K)</td><td>13502</td><td>13998</td></tr>
<tr><td>TRANG SỨC</td><td>Vàng Rồng Kim Tín 999.9</td><td>99.7 (23K)</td><td>12757</td><td>13053</td></tr>
<tr><td>Thị trường</td><td>VÀNG THỊ TRƯỜNG</td><td>999.9 (24K)</td><td>12500</td><td>-</td></tr>
</table>
</div>
"""

KTH_HTML = """
<div class="table-body">
<div class="column-brandgold"><h3>Nhẫn Trơn 99.99</h3></div>
<div class="column-typegold"><div class="box-typegold">
<div class="col-attr-typegold col-name">chỉ</div>
<div class="col-attr-typegold col-buy">12770000</div>
<div class="col-attr-typegold col-sell">13050000</div>
</div></div>
<div class="column-brandgold"><h3>Nữ trang 610</h3></div>
<div class="column-typegold"><div class="box-typegold">
<div class="col-attr-typegold col-buy">7700000</div>
<div class="col-attr-typegold col-sell">8150000</div>
</div></div>
<div class="column-brandgold"><h3>Trang sức trắng 750 ( Đính Đá )</h3></div>
<div class="column-typegold"><div class="box-typegold">
<div class="col-attr-typegold col-buy">9300000</div>
<div class="col-attr-typegold col-sell">10150000</div>
</div></div>
</div>
"""

KNP_HTML = """
<table>
<tr><th>SẢN PHẨM</th><th>MUA VÀO</th><th>BÁN RA</th></tr>
<tr><td>Nhẫn ép vỉ Kim Ngân Phúc 9999</td><td>12.700</td><td>13.000</td></tr>
<tr><td>Vàng Trang Sức 24K</td><td>12.540</td><td>12.900</td></tr>
<tr><td>Vàng Nhẫn Thị Trường 9999</td><td>12.540</td><td></td></tr>
</table>
"""


def test_parse_huythanh_scales_chi_to_luong():
    got = dict((code, (buy, sell)) for code, buy, sell in parse_huythanh(HT_HTML))
    assert got["HT_24K"] == (134_500_000.0, 138_500_000.0)
    assert got["HT_MARKET"] == (127_500_000.0, 0.0)
    assert got["HT_22K"] == (123_200_000.0, 126_870_000.0)


def test_parse_kimtin_reads_hn_panel_and_nghin_unit():
    got = dict((code, (buy, sell)) for code, buy, sell in parse_kimtin(KT_HTML))
    assert got["KT_RING9999"] == (128_020_000.0, 130_980_000.0)
    assert got["KT_SJC"] == (135_020_000.0, 139_980_000.0)
    assert got["KT_TS23K"] == (127_570_000.0, 130_530_000.0)
    assert "KT_TS9999" not in got  # bảng HN không có dòng 999.9 trang sức riêng


def test_parse_kimthanh_skips_dinh_da():
    got = dict((code, (buy, sell)) for code, buy, sell in parse_kimthanh(KTH_HTML))
    assert got["KTH_RING9999"] == (127_700_000.0, 130_500_000.0)
    assert got["KTH_TS610"] == (77_000_000.0, 81_500_000.0)
    assert "KTH_TS750" not in got


def test_parse_kimnganphuc_thousands_per_chi():
    got = dict((code, (buy, sell)) for code, buy, sell in parse_kimnganphuc(KNP_HTML))
    assert got["KNP_RING9999"] == (127_000_000.0, 130_000_000.0)
    assert got["KNP_TS24K"] == (125_400_000.0, 129_000_000.0)


def test_private_shops_partial_failure_and_cache():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "ok" in str(request.url):
            return httpx.Response(200, text=KNP_HTML)
        return httpx.Response(500)

    shops = [
        ShopSpec("ok", "https://ok.test/gia-vang", parse_kimnganphuc),
        ShopSpec("dead", "https://dead.test/gia-vang", parse_kimnganphuc),
    ]
    p = PrivateShopsProvider(shops=shops)
    p._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        quotes = asyncio.run(p.fetch_current())
        n_calls = len(calls)
        quotes2 = asyncio.run(p.fetch_current())
    finally:
        asyncio.run(p._client.aclose())

    assert {q.code for q in quotes} == {"KNP_RING9999", "KNP_TS24K"}
    assert all(q.source == "shops:ok" for q in quotes)
    assert quotes2 == quotes
    assert len(calls) == n_calls  # cache TTL


def test_kimtin_falls_back_to_proxy_when_direct_blocked():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "r.jina.ai" in str(request.url):
            assert request.headers.get("x-return-format") == "html"
            return httpx.Response(200, text=KT_HTML)
        return httpx.Response(500)

    shops = [ShopSpec("kimtin", "https://kimtin.com.vn/", parse_kimtin,
                      "https://r.jina.ai/https://kimtin.com.vn/")]
    p = PrivateShopsProvider(shops=shops)
    p._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        quotes = asyncio.run(p.fetch_current())
    finally:
        asyncio.run(p._client.aclose())

    assert {q.code for q in quotes} == {"KT_RING9999", "KT_SJC", "KT_TS23K"}
    assert all(q.source == "shops:kimtin" for q in quotes)
    assert any("r.jina.ai" in c for c in calls)


def test_kimtin_proxy_can_be_disabled(monkeypatch):
    monkeypatch.setattr(privateshops, "KIMTIN_PROXY", False)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    shops = [ShopSpec("kimtin", "https://kimtin.com.vn/", parse_kimtin,
                      "https://r.jina.ai/https://kimtin.com.vn/")]
    p = PrivateShopsProvider(shops=shops)
    p._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(RuntimeError, match="không tiệm nào"):
            asyncio.run(p.fetch_current())
    finally:
        asyncio.run(p._client.aclose())


def test_private_shops_all_dead_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    p = PrivateShopsProvider(shops=[ShopSpec("dead", "https://dead.test/", parse_kimnganphuc)])
    p._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(RuntimeError):
            asyncio.run(p.fetch_current())
    finally:
        asyncio.run(p._client.aclose())


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
