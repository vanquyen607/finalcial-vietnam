from __future__ import annotations

import asyncio
import logging
import time

from .base import GoldProvider, ProviderQuote

log = logging.getLogger("aurum.composite")


class MergedProvider(GoldProvider):
    """Gộp nhiều provider: mỗi nguồn chết thì nguồn còn lại vẫn trả dữ liệu.

    Các nguồn được gọi song song (mỗi nguồn có timeout riêng) để một nguồn chậm
    không kéo dài cả nhịp poll. `last_errors` / `last_ok` phục vụ health từng nguồn.
    fetch_history ủy quyền cho provider đầu tiên hỗ trợ mã đó.
    """

    name = "mix"

    def __init__(self, subs: list[GoldProvider], timeout: float = 25.0) -> None:
        self._subs = subs
        self._timeout = timeout
        self.last_errors: dict[str, str] = {}
        self.last_ok: dict[str, int] = {}

    async def fetch_current(self) -> list[ProviderQuote]:
        results = await asyncio.gather(*(self._run(sub) for sub in self._subs))
        out: list[ProviderQuote] = []
        for quotes in results:
            out.extend(quotes)
        if not out:
            detail = "; ".join(f"{k}: {v}" for k, v in self.last_errors.items())
            raise RuntimeError("mọi provider đều chết: " + (detail or "không rõ"))
        return out

    async def _run(self, sub: GoldProvider) -> list[ProviderQuote]:
        try:
            quotes = await asyncio.wait_for(sub.fetch_current(), timeout=self._timeout)
        except Exception as exc:  # noqa: BLE001 - nguồn lỗi là bình thường
            log.warning("provider %s lỗi: %s", sub.name, exc)
            self.last_errors[sub.name] = f"{type(exc).__name__}: {exc}"
            return []
        self.last_errors.pop(sub.name, None)
        self.last_ok[sub.name] = int(time.time())
        return quotes

    def supports_history(self, code: str) -> bool:
        return any(sub.supports_history(code) for sub in self._subs)

    async def fetch_history(self, code: str, days: int) -> list[dict]:
        for sub in self._subs:
            if not sub.supports_history(code):
                continue
            try:
                return await sub.fetch_history(code, days)
            except NotImplementedError:
                continue
        raise NotImplementedError(f"không provider nào có history cho {code}")

    async def aclose(self) -> None:
        for sub in self._subs:
            try:
                await sub.aclose()
            except Exception:  # noqa: BLE001
                pass
