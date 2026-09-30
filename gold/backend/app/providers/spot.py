from __future__ import annotations

import logging

import httpx

log = logging.getLogger("aurum.spot")

# Nguồn giá vàng thế giới realtime, không cần API key.
# TradingView KHÔNG có giá vàng miếng SJC/DOJI/PNJ nội địa (đã kiểm tra symbol-search
# ngày 30/09/2026) — chỉ có spot thế giới. Thử theo thứ tự ưu tiên, lấy nguồn đầu tiên OK.
SCANNER = "https://scanner.tradingview.com/symbol"          # có close + change_abs
SPOT_SYMBOLS = [
    "OANDA:XAUUSD",      # spot chính
    "TVC:GOLD",          # spot tổng hợp của TradingView
    "FX:XAUUSD",
    "FOREXCOM:XAUUSD",
    "SAXO:XAUUSD",
    # token vàng crypto, giao dịch 24/7 (cuối tuần khi forex đóng cửa vẫn nhảy);
    # thường cao hơn spot vài USD, chỉ dùng khi mọi nguồn forex đều chết.
    "BINANCE:PAXGUSDT",
    "CRYPTO:PAXGUSD",
]
FALLBACK = "https://api.gold-api.com/price/XAU"              # có price, updatedAt "vừa xong"
HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)", "Accept": "application/json"}


async def fetch_world_spot(client: httpx.AsyncClient) -> tuple[float, float] | None:
    """Trả về (giá, thay đổi_abs) của vàng thế giới, hoặc None nếu mọi nguồn chết."""
    for symbol in SPOT_SYMBOLS:
        try:
            resp = await client.get(
                SCANNER,
                params={"symbol": symbol, "fields": "close,change_abs"},
                headers=HEADERS,
                timeout=8.0,
            )
            resp.raise_for_status()
            data = resp.json()
            price = float(data.get("close") or 0)
            if price > 0:
                if symbol != SPOT_SYMBOLS[0]:
                    log.debug("spot dùng nguồn dự phòng %s: %s", symbol, price)
                return price, float(data.get("change_abs") or 0)
        except Exception as exc:  # noqa: BLE001 - nguồn phụ lỗi là bình thường
            log.debug("spot %s lỗi: %s", symbol, exc)

    try:
        resp = await client.get(FALLBACK, headers=HEADERS, timeout=8.0)
        resp.raise_for_status()
        data = resp.json()
        price = float(data.get("price") or 0)
        if price > 0:
            return price, 0.0
    except Exception as exc:  # noqa: BLE001
        log.debug("gold-api lỗi: %s", exc)

    return None
