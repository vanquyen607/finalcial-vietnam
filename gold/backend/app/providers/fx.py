from __future__ import annotations

import logging

import httpx

log = logging.getLogger("aurum.fx")

HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)", "Accept": "application/json"}

# Tỷ giá USD/VND phục vụ quy đổi giá vàng thế giới sang VND/lượng.
# open.er-api miễn phí nhưng giới hạn ~1500 lượt/tháng -> poller cache 30 phút/lần.
PRIMARY = "https://open.er-api.com/v6/latest/USD"
SECONDARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"


async def fetch_usd_vnd(client: httpx.AsyncClient) -> tuple[float, str] | None:
    """Trả về (usd_vnd, nguồn), hoặc None nếu mọi nguồn chết."""
    try:
        resp = await client.get(PRIMARY, headers=HEADERS, timeout=10.0)
        resp.raise_for_status()
        vnd = float((resp.json().get("rates") or {}).get("VND") or 0)
        if vnd > 0:
            return vnd, "er-api"
    except Exception as exc:  # noqa: BLE001
        log.debug("er-api lỗi: %s", exc)

    try:
        resp = await client.get(SECONDARY, headers=HEADERS, timeout=10.0)
        resp.raise_for_status()
        vnd = float((resp.json().get("usd") or {}).get("vnd") or 0)
        if vnd > 0:
            return vnd, "currency-api"
    except Exception as exc:  # noqa: BLE001
        log.debug("currency-api lỗi: %s", exc)

    return None
