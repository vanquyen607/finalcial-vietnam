from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..symbols import GOLD_TYPES


@dataclass(slots=True)
class ProviderQuote:
    """Một bản ghi giá chuẩn hoá từ provider."""

    code: str
    name: str
    buy: float
    sell: float
    change_buy: float
    change_sell: float
    unit: str
    per: str
    source: str
    updated_at: int | None = None  # epoch giây

    @property
    def mid(self) -> float:
        if self.buy and self.sell:
            return round((self.buy + self.sell) / 2, 4)
        return self.buy or self.sell


def raw_snapshot_to_quotes(rows: list[dict], source: str, updated_at: int | None = None) -> list[ProviderQuote]:
    """Chuẩn hoá payload {'type_code','buy','sell','change_buy','change_sell'} -> ProviderQuote.

    Bỏ qua type_code không có trong GOLD_TYPES để dữ liệu hiển thị luôn có metadata.
    """
    known = {t["code"]: t for t in GOLD_TYPES}
    out: list[ProviderQuote] = []
    for row in rows:
        code = row.get("type_code")
        meta = known.get(code)
        if meta is None:
            continue
        out.append(ProviderQuote(
            code=code,
            name=meta["name"],
            buy=float(row.get("buy") or 0),
            sell=float(row.get("sell") or 0),
            change_buy=float(row.get("change_buy") or 0),
            change_sell=float(row.get("change_sell") or 0),
            unit=meta["unit"],
            per=meta["per"],
            source=source,
            updated_at=updated_at,
        ))
    return out


class GoldProvider(ABC):
    """Nguồn dữ liệu giá vàng. Mọi provider phải tự chịu lỗi của mình."""

    name: str = "base"

    @abstractmethod
    async def fetch_current(self) -> list[ProviderQuote]:
        """Lấy bảng giá hiện tại. Ném exception nếu nguồn chết."""

    async def fetch_history(self, code: str, days: int) -> list[dict]:
        """Lấy lịch sử theo ngày: [{'date': 'YYYY-MM-DD', 'buy': .., 'sell': ..}]."""
        raise NotImplementedError

    async def aclose(self) -> None:  # pragma: no cover
        return None
