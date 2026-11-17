"""Chỉ số sức mua/bán (Technical Rating) của TradingView cho vàng thế giới.

TradingView công khai các điểm tổng hợp Recommend.All / Recommend.MA /
Recommend.Other qua scanner API — chính là số liệu đứng sau đồng hồ
"Bán mạnh … Mua mạnh" trên trang XAUUSD của họ. Thang điểm −1…+1:

    ≤ −0,5  Bán mạnh      −0,5…−0,1  Bán        −0,1…0,1  Trung lập
    0,1…0,5 Mua           ≥ 0,5      Mua mạnh
"""
from __future__ import annotations

import logging

import httpx

log = logging.getLogger("aurum.technicals")

SCANNER_URL = "https://scanner.tradingview.com/symbol"
SYMBOL = "OANDA:XAUUSD"
HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)"}

# khung thời gian -> hậu tố field của scanner (ngày = không hậu tố)
TF_SUFFIX = {"15": "|15", "60": "|60", "240": "|240", "1D": "", "1W": "|1W"}


def rating_of(value: float) -> tuple[str, str]:
    """Điểm −1…+1 -> (key, nhãn tiếng Việt) theo đúng dải của TradingView."""
    if value <= -0.5:
        return "strong_sell", "Bán mạnh"
    if value < -0.1:
        return "sell", "Bán"
    if value <= 0.1:
        return "neutral", "Trung lập"
    if value < 0.5:
        return "buy", "Mua"
    return "strong_buy", "Mua mạnh"


def _num(raw: dict, field: str) -> float | None:
    v = raw.get(field)
    try:
        return round(float(v), 4) if v is not None else None
    except (TypeError, ValueError):
        return None


def parse_technicals(raw: dict) -> dict | None:
    """Scanner payload -> {symbol, close, change, frames{tf: {...}}}."""
    frames: dict[str, dict] = {}
    for tf, suffix in TF_SUFFIX.items():
        total = _num(raw, f"Recommend.All{suffix}")
        if total is None:
            continue
        key, label = rating_of(total)
        frames[tf] = {
            "all": total,
            "ma": _num(raw, f"Recommend.MA{suffix}"),
            "other": _num(raw, f"Recommend.Other{suffix}"),
            "rating": key,
            "label": label,
        }
    if not frames:
        return None
    return {
        "symbol": SYMBOL,
        "close": _num(raw, "close"),
        "change": _num(raw, "change"),
        "frames": frames,
    }


async def fetch_technicals(client: httpx.AsyncClient) -> dict | None:
    fields = ["name", "close", "change"]
    for suffix in TF_SUFFIX.values():
        fields += [f"Recommend.All{suffix}", f"Recommend.MA{suffix}",
                   f"Recommend.Other{suffix}"]
    try:
        r = await client.get(
            SCANNER_URL,
            params={"symbol": SYMBOL, "fields": ",".join(fields),
                    "no_404": "false"},
            headers=HEADERS, timeout=15,
        )
        r.raise_for_status()
        return parse_technicals(r.json())
    except Exception as exc:  # noqa: BLE001
        log.warning("technicals lỗi: %s", exc)
        return None
