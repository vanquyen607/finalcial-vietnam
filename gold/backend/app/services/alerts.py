from __future__ import annotations

import time
from typing import Any

from ..db import db


def day_change_pct(buy: float, change: float) -> float:
    prev = buy - change
    if not prev:
        return 0.0
    return round(change / prev * 100, 4)


def evaluate(quotes: dict[str, dict]) -> list[dict[str, Any]]:
    """Đánh giá cảnh báo; trả về danh sách sự kiện vừa kích hoạt.

    Hỗ trợ 2 chế độ:
      - % thay đổi trong ngày (threshold > 0, không có target_price)
      - giá tuyệt đối (target_price != None): kích hoạt khi giá mua vượt ngưỡng
    Mỗi alert chỉ kích hoạt một lần rồi tự tắt để tránh spam.
    """
    events: list[dict[str, Any]] = []
    for alert in db.active_alerts():
        q = quotes.get(alert["code"])
        if not q:
            continue
        pct = day_change_pct(q["buy"], q["change_buy"])
        target = alert.get("target_price")
        if target is not None:
            hit = (q["buy"] >= target) if alert["direction"] == "up" else (q["buy"] <= target)
            label = f'giá mua {q["buy"]:,.0f} {"≥" if alert["direction"] == "up" else "≤"} {target:,.0f}'
        else:
            hit = pct >= alert["threshold"] if alert["direction"] == "up" else pct <= -alert["threshold"]
            label = f'{abs(pct):.2f}% (ngưỡng {alert["threshold"]:.2f}%)'
        if not hit:
            continue
        db.mark_triggered(alert["id"])
        db.set_alert_active(alert["id"], False)
        events.append({
            "type": "alert",
            "alert_id": alert["id"],
            "code": alert["code"],
            "name": q["name"],
            "direction": alert["direction"],
            "threshold": alert["threshold"],
            "target_price": target,
            "pct": pct,
            "buy": q["buy"],
            "sell": q["sell"],
            "note": alert["note"],
            "ts": int(time.time()),
            "message": (
                f'{q["name"]} {"tăng" if alert["direction"] == "up" else "giảm"} '
                f'{abs(pct):.2f}% (ngưỡng {alert["threshold"]:.2f}%)'
                if target is None else
                f'{q["name"]} {"tăng" if alert["direction"] == "up" else "giảm"}: '
                f'giá mua {q["buy"]:,.0f} {"≥" if alert["direction"] == "up" else "≤"} {target:,.0f}'
            ),
        })
    return events
