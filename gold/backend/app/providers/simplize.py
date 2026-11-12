from __future__ import annotations

import asyncio
import logging
import re
import time

import httpx

from ..config import settings
from ..symbols import BY_CODE
from .base import GoldProvider, ProviderQuote
from .validate import num

log = logging.getLogger("aurum.simplize")

BASE = "https://simplize.vn"
HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)", "Accept": "application/json, text/html"}

# code nội bộ -> (brand_slug, product_slug) trên Simplize.
PRODUCTS: dict[str, tuple[str, str]] = {
    "MH_SJC": ("mi-hong", "vang-mieng-sjc-mi-hong"),
    "MH_9999": ("mi-hong", "vang-999-mi-hong"),
    "MH_985": ("mi-hong", "vang-985-mi-hong"),
    "MH_980": ("mi-hong", "vang-980-mi-hong"),
    "MH_750": ("mi-hong", "vang-750-mi-hong"),
    "MH_680": ("mi-hong", "vang-680-mi-hong"),
    "MH_610": ("mi-hong", "vang-610-mi-hong"),
    "BTMH_9999": ("bao-tin-manh-hai", "vang-nu-trang-9999-btmh"),
    "BTMH_999": ("bao-tin-manh-hai", "vang-nu-trang-999-btmh"),
    "BTMH_RING": ("bao-tin-manh-hai", "nhan-ep-vi-kim-gia-bao"),
    "BTMH_DONG": ("bao-tin-manh-hai", "dong-vang-kim-gia-bao-hoa-sen"),
    "PQ_SJC": ("phu-quy", "vang-mieng-sjc-phu-quy"),
    "PQ_9999": ("phu-quy", "nhan-tron-phu-quy-9999"),
    "PQ_999": ("phu-quy", "phu-quy-1-luong-999"),
    "PQ_9999_BAR": ("phu-quy", "phu-quy-1-luong-9999"),
    "PQ_TS9999": ("phu-quy", "vang-trang-suc-9999-phu-quy"),
    "PQ_TS999": ("phu-quy", "vang-trang-suc-999-phu-quy"),
    "PQ_TS99": ("phu-quy", "vang-trang-suc-99-phu-quy"),
    "PQ_TS98": ("phu-quy", "vang-trang-suc-98-phu-quy"),
    "SJC_1CHI": ("sjc", "vang-sjc-1-chi"),
    "SJC_5CHI": ("sjc", "vang-sjc-5-chi"),
    "SJC_NHAN_05": ("sjc", "vang-nhan-sjc-9999-05-chi"),
    "SJC_NHAN_1": ("sjc", "vang-nhan-sjc-9999-1-chi"),
    "DOJI_SJC_DN": ("doji", "vang-mieng-sjc-doji-da-nang"),
    "DOJI_RING": ("doji", "nhan-tron-9999-hung-thinh-vuong"),
    "DOJI_24K": ("doji", "vang-24k-doji"),
    "DOJI_PL_HN": ("doji", "vang-mieng-phuc-long-doji-ha-noi"),
    "DOJI_PL_HCM": ("doji", "vang-mieng-phuc-long-doji-hcm"),
    "DOJI_PL_DN": ("doji", "vang-mieng-phuc-long-doji-da-nang"),
    "PNJ_KIMBAO": ("pnj", "vang-kim-bao-9999"),
    "PNJ_PHUCLOC": ("pnj", "vang-phuc-loc-tai-9999"),
    "PNJ_PHOENIX": ("pnj", "vang-mieng-pnj-phuong-hoang"),
    "BTMC_RTL": ("bao-tin-minh-chau", "vang-mieng-rong-thang-long-btmc"),
    "BTMC_TS9999": ("bao-tin-minh-chau", "trang-suc-vang-rong-thang-long-9999"),
    "BTMC_TS999": ("bao-tin-minh-chau", "trang-suc-vang-rong-thang-long-999"),
    "NT_TA": ("ngoc-tham", "vang-ta-ngoc-tham"),
    "NT_18K": ("ngoc-tham", "vang-18k-ngoc-tham"),
    "NT_TS750": ("ngoc-tham", "vang-trang-au750-ngoc-tham"),
}

TTL = 900        # giá cửa hàng đổi chậm -> cache 15 phút
BUILD_TTL = 86400  # buildId Next.js đổi theo đợt deploy


class SimplizeProvider(GoldProvider):
    """Giá các cửa hàng tư nhân qua JSON public của Simplize (không cần key).

    Luồng: lấy buildId từ HTML -> đọc _next/data JSON từng sản phẩm.
    """

    name = "simplize"

    def __init__(self, timeout: float | None = None) -> None:
        self._client = httpx.AsyncClient(headers=HEADERS, timeout=timeout or 15.0,
                                         follow_redirects=True)
        self._cache: list[ProviderQuote] = []
        self._cache_ts = 0
        self._bid = ""
        self._bid_ts = 0

    async def _build_id(self) -> str:
        now = time.time()
        if self._bid and now - self._bid_ts < BUILD_TTL:
            return self._bid
        resp = await self._client.get(f"{BASE}/gia-vang/mi-hong/vang-999-mi-hong")
        resp.raise_for_status()
        m = re.search(r'"buildId":"([A-Za-z0-9_-]+)"', resp.text)
        if not m:
            raise RuntimeError("không tìm thấy buildId Simplize")
        self._bid, self._bid_ts = m.group(1), now
        return self._bid

    async def _product(self, bid: str, brand: str, slug: str) -> dict | None:
        try:
            resp = await self._client.get(f"{BASE}/_next/data/{bid}/gia-vang/{brand}/{slug}.json")
            resp.raise_for_status()
            items = resp.json()["pageProps"]["listData"]
            return items[0] if items else None
        except Exception as exc:  # noqa: BLE001
            log.debug("simplize %s/%s lỗi: %s", brand, slug, exc)
            return None

    async def fetch_current(self) -> list[ProviderQuote]:
        now = int(time.time())
        if self._cache and now - self._cache_ts < TTL:
            return self._cache
        bid = await self._build_id()
        sem = asyncio.Semaphore(8)

        async def one(code: str, brand: str, slug: str) -> ProviderQuote | None:
            async with sem:
                item = await self._product(bid, brand, slug)
            if not item:
                return None
            buy, sell = num(item.get("priceBuy")), num(item.get("priceSell"))
            if not buy or not sell:
                return None
            meta = BY_CODE[code]
            ts = num(item.get("modifiedTime"))
            return ProviderQuote(
                code=code, name=meta["name"], buy=buy, sell=sell,
                change_buy=num(item.get("priceBuyChg")) or 0.0,
                change_sell=num(item.get("priceSellChg")) or 0.0,
                unit=meta["unit"], per=meta["per"], source=self.name,
                updated_at=int(ts // 1000) if ts else now,
            )

        results = await asyncio.gather(
            *(one(code, brand, slug) for code, (brand, slug) in PRODUCTS.items())
        )
        quotes = [q for q in results if q is not None]
        if not quotes:
            if self._cache:
                return self._cache
            raise RuntimeError("simplize trả rỗng toàn bộ sản phẩm")
        self._cache, self._cache_ts = quotes, now
        return quotes

    async def aclose(self) -> None:
        await self._client.aclose()
