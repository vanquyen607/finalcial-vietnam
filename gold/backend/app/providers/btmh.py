from __future__ import annotations

import logging
import re
import time

import httpx
from bs4 import BeautifulSoup

from ..symbols import BY_CODE
from .base import GoldProvider, ProviderQuote

log = logging.getLogger("aurum.btmh")

URL = "https://baotinmanhhai.vn/bang-gia-vang"
HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)", "Accept": "text/html"}

# BTMH niêm yết vàng theo nghìn đồng/chỉ -> app quy về đồng/lượng (x1000 x10).
GOLD_FACTOR = 10_000.0
# Bạc: nghìn đồng/lượng (x1000); thỏi 1 kg: nghìn đồng/kg -> đồng/lượng (x37.5).
SILVER_PER_LUONG = 1_000.0
SILVER_PER_KG = 37.5

# Tên dòng trên bảng BTMH -> mã nội bộ của app (chỉ map dòng chắc chắn khớp).
GOLD_ITEMS: dict[str, str] = {
    "Kim Gia Bảo 24K": "BTMH_9999",
    "Vàng trang sức 24K 999": "BTMH_999",
}

TTL = 600  # cache 10 phút


def vn_num(text: str) -> float | None:
    """'13.350' / '-1.920.000' (chấm = ngăn nghìn) -> số. None khi không parse được."""
    try:
        return float(text.strip().replace(".", "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def _rows(html: str) -> list[tuple[str, list[float]]]:
    """(tên dòng, [số...]) từ bảng giá BTMH: số đầu là tuổi, tiếp theo mua/bán."""
    soup = BeautifulSoup(html, "lxml")
    out: list[tuple[str, list[float]]] = []
    for row in soup.select('div[role="row"]'):
        name_el = row.select_one('[role="cell"]')
        if not name_el:
            continue
        nums = [n for s in row.select("span.tabular-nums")
                if (n := vn_num(s.get_text(strip=True))) is not None]
        if len(nums) >= 2:  # ít nhất tuổi + 1 giá
            out.append((name_el.get_text(" ", strip=True), nums))
    return out


def parse_btmh_gold(html: str, now: int) -> list[ProviderQuote]:
    quotes: list[ProviderQuote] = []
    for name, nums in _rows(html):
        code = GOLD_ITEMS.get(name)
        if code is None or len(nums) < 3:
            continue
        buy, sell = nums[1] * GOLD_FACTOR, nums[2] * GOLD_FACTOR
        meta = BY_CODE[code]
        quotes.append(ProviderQuote(
            code=code, name=meta["name"], buy=buy, sell=sell,
            change_buy=0.0, change_sell=0.0,
            unit=meta["unit"], per=meta["per"], source="btmh", updated_at=now,
        ))
    return quotes


def parse_btmh_silver(html: str) -> list[dict]:
    """Dòng bạc BTMH -> {'brand','name','buy','sell'} theo đồng/lượng."""
    items: list[dict] = []
    for name, nums in _rows(html):
        if "Bạc" not in name and "Ngân Gia Bảo" not in name:
            continue
        factor = SILVER_PER_KG if "(ĐVT: kg)" in name else SILVER_PER_LUONG
        buy = nums[1] * factor if len(nums) > 1 else None
        sell = nums[2] * factor if len(nums) > 2 else None
        if not buy and not sell:
            continue
        items.append({
            "brand": "BTMH",
            "name": re.sub(r"\s*\(ĐVT:[^)]*\)", "", name),
            "buy": buy, "sell": sell, "change": None,
        })
    return items


class BtmhProvider(GoldProvider):
    """Giá vàng chính chủ Bảo Tín Mạnh Hải (bảng giá server-render trên web hãng)."""

    name = "btmh"

    def __init__(self, timeout: float | None = None) -> None:
        self._client = httpx.AsyncClient(headers=HEADERS, timeout=timeout or 15.0)
        self._cache: list[ProviderQuote] = []
        self._cache_ts = 0

    async def fetch_current(self) -> list[ProviderQuote]:
        now = int(time.time())
        if self._cache and now - self._cache_ts < TTL:
            return self._cache
        resp = await self._client.get(URL)
        resp.raise_for_status()
        quotes = parse_btmh_gold(resp.text, now)
        if not quotes:
            if self._cache:
                return self._cache
            raise RuntimeError("btmh trả rỗng")
        self._cache, self._cache_ts = quotes, now
        return quotes

    async def aclose(self) -> None:
        await self._client.aclose()
