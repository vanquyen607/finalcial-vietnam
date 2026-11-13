"""Bảng giá các tiệm vàng tư nhân — scrape HTML công khai.

Mỗi tiệm niêm yết theo CHỈ với đơn vị khác nhau, tất cả được quy về VND/lượng
(1 lượng = 10 chỉ) để khớp phần còn lại của app.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Callable

import httpx
from bs4 import BeautifulSoup

from ..symbols import BY_CODE
from .base import GoldProvider, ProviderQuote

log = logging.getLogger("aurum.shops")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "vi,en;q=0.8",
}

PER_CHI = 10.0          # VND/chỉ -> VND/lượng
NGHIN_PER_CHI = 10_000.0  # nghìn VND/chỉ -> VND/lượng

# Giá 1 lượng vàng hợp lý; ngoài khoảng này coi là parse lỗi / dữ liệu rác.
MIN_PRICE = 20_000_000.0
MAX_PRICE = 500_000_000.0

TTL = 300

# Render (IP datacenter) bị kimtin.com.vn chặn kết nối. Khi đó đọc qua
# r.jina.ai (trả HTML gốc bằng header x-return-format) rồi parse như thường.
# Tắt bằng KIMTIN_PROXY=0.
KIMTIN_PROXY = os.environ.get("KIMTIN_PROXY", "1") != "0"
KIMTIN_PROXY_URL = "https://r.jina.ai/https://kimtin.com.vn/"
PROXY_HEADERS = {"x-return-format": "html"}

# Trực tiếp thử nhanh để còn kịp fallback trong timeout 25s của MergedProvider.
DIRECT_TIMEOUT = 8.0
PROXY_TIMEOUT = 15.0


@dataclass(slots=True)
class ShopSpec:
    key: str
    url: str
    parse: Callable[[str], list[tuple[str, float, float]]]
    proxy_url: str | None = None


def _price(text: str, mult: float) -> float | None:
    digits = re.sub(r"[^\d]", "", text or "")
    if not digits:
        return None
    value = float(digits) * mult
    return value if MIN_PRICE <= value <= MAX_PRICE else None


def _cells(row) -> list[str]:
    return [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]


def _rows(html: str, selector: str = "table") -> list[list[str]]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one(selector)
    if table is None:
        return []
    return [_cells(tr) for tr in table.find_all("tr")]


def parse_huythanh(html: str) -> list[tuple[str, float, float]]:
    labels = [
        ("vàng huy thanh 24k", "HT_24K"),
        ("vàng thị trường 24k", "HT_MARKET"),
        ("22k", "HT_22K"),
        ("18k", "HT_18K"),
        ("14k", "HT_14K"),
        ("10k", "HT_10K"),
    ]
    out: list[tuple[str, float, float]] = []
    seen: set[str] = set()
    for cells in _rows(html):
        if len(cells) < 3:
            continue
        label = cells[0].lower()
        code = next((c for needle, c in labels if needle in label), None)
        if not code or code in seen:
            continue
        buy = _price(cells[1], PER_CHI)
        if buy is None:
            continue
        sell = _price(cells[2], PER_CHI) or 0.0
        out.append((code, buy, sell))
        seen.add(code)
    return out


def parse_kimtin(html: str) -> list[tuple[str, float, float]]:
    soup = BeautifulSoup(html, "lxml")
    panel = soup.select_one("#gold-area-panel-HN") or soup.select_one(".gold-area-panel")
    if panel is None:
        return []
    table = panel.find("table")
    if table is None:
        return []
    out: list[tuple[str, float, float]] = []
    seen: set[str] = set()
    for tr in table.find_all("tr"):
        cells = _cells(tr)
        if len(cells) < 4:
            continue
        text = " ".join(cells).upper()
        content = cells[-3]
        if "VÀNG MIẾNG SJC" in text:
            code = "KT_SJC"
        elif "NHẪN TRÒN TRƠN" in text:
            code = "KT_RING9999"
        elif "TRANG SỨC" in text:
            if "99.7" in content:
                code = "KT_TS23K"
            elif "999.9" in content:
                code = "KT_TS9999"
            elif "99.9" in content:
                code = "KT_TS999"
            else:
                code = "KT_TS9999"
        else:
            continue
        if code in seen:
            continue
        buy = _price(cells[-2], NGHIN_PER_CHI)
        if buy is None:
            continue
        sell = _price(cells[-1], NGHIN_PER_CHI) or 0.0
        out.append((code, buy, sell))
        seen.add(code)
    return out


KIMTHANH_ITEMS = [
    ("nhẫn trơn 99.99", "KTH_RING9999"),
    ("nhẫn trơn 990", "KTH_RING990"),
    ("nữ trang 980", "KTH_TS980"),
    ("nữ trang 610", "KTH_TS610"),
    ("trang sức trắng 750", "KTH_TS750"),
    ("trang sức 10k", "KTH_TS416"),
]


def parse_kimthanh(html: str) -> list[tuple[str, float, float]]:
    soup = BeautifulSoup(html, "lxml")
    out: list[tuple[str, float, float]] = []
    seen: set[str] = set()
    for block in soup.select(".column-brandgold"):
        name = block.get_text(" ", strip=True).lower()
        if "đính đá" in name:
            continue
        code = next((c for needle, c in KIMTHANH_ITEMS if needle in name), None)
        if not code or code in seen:
            continue
        body = block.find_next_sibling(class_="column-typegold")
        if body is None:
            continue
        buy_cell = body.select_one(".col-buy")
        sell_cell = body.select_one(".col-sell")
        if buy_cell is None or sell_cell is None:
            continue
        buy = _price(buy_cell.get_text(" ", strip=True), PER_CHI)
        if buy is None:
            continue
        sell = _price(sell_cell.get_text(" ", strip=True), PER_CHI) or 0.0
        out.append((code, buy, sell))
        seen.add(code)
    return out


def parse_kimnganphuc(html: str) -> list[tuple[str, float, float]]:
    items = [
        ("nhẫn ép vỉ", "KNP_RING9999"),
        ("vàng trang sức 24k", "KNP_TS24K"),
    ]
    out: list[tuple[str, float, float]] = []
    seen: set[str] = set()
    for cells in _rows(html):
        if len(cells) < 3:
            continue
        label = cells[0].lower()
        code = next((c for needle, c in items if needle in label), None)
        if not code or code in seen:
            continue
        buy = _price(cells[1], NGHIN_PER_CHI)
        if buy is None:
            continue
        sell = _price(cells[2], NGHIN_PER_CHI) or 0.0
        out.append((code, buy, sell))
        seen.add(code)
    return out


SHOPS: list[ShopSpec] = [
    ShopSpec("huythanh", "https://huythanhjewelry.vn/gia-vang-hom-nay", parse_huythanh),
    ShopSpec("kimtin", "https://kimtin.com.vn/", parse_kimtin, KIMTIN_PROXY_URL),
    ShopSpec("kimthanh", "https://kimthanhh.com/gia-vang", parse_kimthanh),
    ShopSpec("kimnganphuc", "https://kimnganphuc.vn/gia-vang", parse_kimnganphuc),
]


class PrivateShopsProvider(GoldProvider):
    """Gộp nhiều tiệm vàng tư nhân; mỗi tiệm chết không ảnh hưởng tiệm khác."""

    name = "shops"

    def __init__(self, timeout: float | None = None, shops: list[ShopSpec] | None = None) -> None:
        self._client = httpx.AsyncClient(
            headers=HEADERS, timeout=timeout or 20.0, follow_redirects=True,
        )
        self._shops = shops or SHOPS
        self._cache: list[ProviderQuote] = []
        self._cache_ts = 0

    async def _text(self, url: str, timeout: float, headers: dict | None = None) -> str:
        resp = await self._client.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
        return resp.text

    async def _load(self, spec: ShopSpec) -> str:
        fast = DIRECT_TIMEOUT if spec.proxy_url else 20.0
        try:
            return await self._text(spec.url, fast)
        except Exception as exc:
            if not (spec.proxy_url and KIMTIN_PROXY):
                raise
            log.info("tiệm %s trực tiếp lỗi (%s), thử proxy", spec.key, exc)
            return await self._text(spec.proxy_url, PROXY_TIMEOUT, PROXY_HEADERS)

    async def _one(self, spec: ShopSpec) -> list[ProviderQuote]:
        html = await self._load(spec)
        quotes: list[ProviderQuote] = []
        for code, buy, sell in spec.parse(html):
            meta = BY_CODE.get(code)
            if meta is None:
                continue
            quotes.append(ProviderQuote(
                code=code, name=meta["name"], buy=buy, sell=sell,
                change_buy=0.0, change_sell=0.0,
                unit=meta["unit"], per=meta["per"], source=f"shops:{spec.key}",
            ))
        if not quotes:
            raise RuntimeError(f"{spec.key}: không parse được giá nào")
        return quotes

    async def fetch_current(self) -> list[ProviderQuote]:
        now = int(time.time())
        if self._cache and now - self._cache_ts < TTL:
            return self._cache
        results = await asyncio.gather(
            *(self._one(spec) for spec in self._shops), return_exceptions=True,
        )
        quotes: list[ProviderQuote] = []
        for spec, result in zip(self._shops, results):
            if isinstance(result, Exception):
                log.warning("tiệm %s lỗi: %s", spec.key, result)
                continue
            quotes.extend(result)
        if not quotes:
            if self._cache:
                return self._cache
            raise RuntimeError("không tiệm nào trả được giá")
        self._cache, self._cache_ts = quotes, now
        return quotes

    async def aclose(self) -> None:
        await self._client.aclose()
