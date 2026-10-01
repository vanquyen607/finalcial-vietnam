from __future__ import annotations

import logging

from .base import GoldProvider, ProviderQuote

log = logging.getLogger("aurum.composite")


class MergedProvider(GoldProvider):
    """Gộp nhiều provider: mỗi nguồn chết thì nguồn còn lại vẫn trả dữ liệu.

    fetch_history ủy quyền cho provider đầu tiên hỗ trợ mã đó.
    """

    name = "mix"

    def __init__(self, subs: list[GoldProvider]) -> None:
        self._subs = subs

    async def fetch_current(self) -> list[ProviderQuote]:
        out: list[ProviderQuote] = []
        errors: list[str] = []
        for sub in self._subs:
            try:
                out.extend(await sub.fetch_current())
            except Exception as exc:  # noqa: BLE001
                log.warning("provider %s lỗi: %s", sub.name, exc)
                errors.append(f"{sub.name}: {exc}")
        if not out:
            raise RuntimeError("mọi provider đều chết: " + "; ".join(errors))
        return out

    async def fetch_history(self, code: str, days: int) -> list[dict]:
        for sub in self._subs:
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
