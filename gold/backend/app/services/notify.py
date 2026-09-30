from __future__ import annotations

import logging

import httpx

log = logging.getLogger("aurum.notify")


async def send_telegram(client: httpx.AsyncClient, token: str, chat_id: str, text: str) -> bool:
    """Gửi tin nhắn Telegram. Trả False khi chưa cấu hình hoặc gửi lỗi."""
    if not token or not chat_id:
        return False
    try:
        resp = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return bool(resp.json().get("ok"))
    except Exception as exc:  # noqa: BLE001
        log.warning("gửi Telegram lỗi: %s", exc)
        return False
