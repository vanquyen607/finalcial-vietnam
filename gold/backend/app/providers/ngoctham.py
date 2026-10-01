from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

import httpx

from ..symbols import BY_CODE
from .base import GoldProvider, ProviderQuote
from .validate import num

log = logging.getLogger("aurum.ngoctham")

URL = "https://ngoctham.com/ajax/proxy_banggia.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)", "Accept": "application/json"}

# Ngọc Thẩm niêm yết theo CHỈ -> app quy về lượng (x10).
PER_CHI = 10.0

# code nội bộ -> danh sách tên loại vàng trong JSON Ngọc Thẩm.
# Ngọc Thẩm đổi tên danh mục theo thời gian -> thử lần lượt các ứng viên.
ITEMS: dict[str, list[str]] = {
    "NT_9999": ["Nhẫn 999.9", "Nhẫn Trơn 24K", "Vàng 24K"],
    "NT_SJC": ["Vàng Miếng SJC (Loại 10 chỉ)", "Vàng Miếng SJC"],
}

TTL = 900  # cache 15 phút

VN_TZ = timedelta(hours=7)


def parse_nt_time(text: str) -> int | None:
    """'2026-09-30 14:41:00' (giờ VN) -> epoch. None khi sai định dạng."""
    try:
        dt = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None
    return int((dt - datetime(1970, 1, 1)).total_seconds() - VN_TZ.total_seconds())


class NgocThamProvider(GoldProvider):
    """Giá chính chủ Ngọc Thẩm (JSON public, hỗ trợ ETag/304)."""

    name = "ngoctham"

    def __init__(self, timeout: float | None = None) -> None:
        self._client = httpx.AsyncClient(headers=HEADERS, timeout=timeout or 15.0)
        self._cache: list[ProviderQuote] = []
        self._cache_ts = 0
        self._etag = ""

    async def fetch_current(self) -> list[ProviderQuote]:
        now = int(time.time())
        if self._cache and now - self._cache_ts < TTL:
            return self._cache
        headers = dict(HEADERS)
        if self._etag:
            headers["If-None-Match"] = self._etag
        resp = await self._client.get(URL, headers=headers)
        if resp.status_code == 304 and self._cache:
            self._cache_ts = now
            return self._cache
        resp.raise_for_status()
        self._etag = resp.headers.get("etag", self._etag)
        payload = resp.json()
        ts = parse_nt_time(payload.get("date") or "") or now
        by_name = {r.get("loaivang"): r for r in payload.get("chitiet") or []
                   if isinstance(r, dict)}
        quotes: list[ProviderQuote] = []
        for code, wanted in ITEMS.items():
            row = next((by_name[n] for n in wanted if n in by_name), None)
            if not row:
                continue
            buy, sell = num(row.get("giamua")), num(row.get("giaban"))
            if not buy or not sell:
                continue
            meta = BY_CODE[code]
            quotes.append(ProviderQuote(
                code=code, name=meta["name"], buy=buy * PER_CHI, sell=sell * PER_CHI,
                change_buy=0.0, change_sell=0.0,
                unit=meta["unit"], per=meta["per"], source=self.name, updated_at=ts,
            ))
        if not quotes:
            if self._cache:
                return self._cache
            raise RuntimeError("ngoctham trả rỗng")
        self._cache, self._cache_ts = quotes, now
        return quotes

    async def aclose(self) -> None:
        await self._client.aclose()
