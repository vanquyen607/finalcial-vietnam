from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

import httpx

from ..symbols import BY_CODE
from .base import GoldProvider, ProviderQuote
from .validate import num

log = logging.getLogger("aurum.mihong")

URL = "https://api.mihong.com/v1/gold-prices"
HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)", "Accept": "application/json",
           "x-market": "mihong"}

# Mi Hồng niêm yết theo CHỈ -> app quy về lượng (x10).
PER_CHI = 10.0

# Mã API Mi Hồng -> mã nội bộ của app.
ITEMS: dict[str, str] = {
    "SJC": "MH_SJC",
    "999": "MH_9999",
    "985": "MH_985",
    "980": "MH_980",
    "750": "MH_750",
    "680": "MH_680",
    "610": "MH_610",
}

TTL = 300  # cache 5 phút

VN_TZ = timedelta(hours=7)


def parse_mh_time(text: str) -> int | None:
    """'17/11/2026 10:08' (giờ VN) -> epoch. None khi sai định dạng."""
    try:
        dt = datetime.strptime(text.strip(), "%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return None
    return int((dt - datetime(1970, 1, 1)).total_seconds() - VN_TZ.total_seconds())


def parse_mihong(payload: list, now: int) -> list[ProviderQuote]:
    """JSON Mi Hồng -> ProviderQuote (giá theo chỉ x10 về lượng)."""
    quotes: list[ProviderQuote] = []
    for row in payload or []:
        if not isinstance(row, dict):
            continue
        code = ITEMS.get(str(row.get("code") or ""))
        if code is None:
            continue
        buy, sell = num(row.get("buyingPrice")), num(row.get("sellingPrice"))
        if not buy and not sell:
            continue
        meta = BY_CODE[code]
        quotes.append(ProviderQuote(
            code=code, name=meta["name"],
            buy=(buy or 0) * PER_CHI, sell=(sell or 0) * PER_CHI,
            change_buy=(num(row.get("buyChange")) or 0) * PER_CHI,
            change_sell=(num(row.get("sellChange")) or 0) * PER_CHI,
            unit=meta["unit"], per=meta["per"], source="mihong",
            updated_at=parse_mh_time(row.get("dateTime") or "") or now,
        ))
    return quotes


class MiHongProvider(GoldProvider):
    """Giá chính chủ Mi Hồng (API JSON public của mihong.vn)."""

    name = "mihong"

    def __init__(self, timeout: float | None = None) -> None:
        self._client = httpx.AsyncClient(headers=HEADERS, timeout=timeout or 15.0)
        self._cache: list[ProviderQuote] = []
        self._cache_ts = 0

    async def fetch_current(self) -> list[ProviderQuote]:
        now = int(time.time())
        if self._cache and now - self._cache_ts < TTL:
            return self._cache
        resp = await self._client.get(URL, params={"market": "domestic"})
        resp.raise_for_status()
        quotes = parse_mihong(resp.json(), now)
        if not quotes:
            if self._cache:
                return self._cache
            raise RuntimeError("mihong trả rỗng")
        self._cache, self._cache_ts = quotes, now
        return quotes

    async def aclose(self) -> None:
        await self._client.aclose()
