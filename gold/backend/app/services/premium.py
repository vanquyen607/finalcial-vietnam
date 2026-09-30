from __future__ import annotations

# 1 lượng = 37,5g ; 1 troy ounce = 31,1034768g
OZ_PER_TAEL = 37.5 / 31.1034768

# Mã SJC dùng làm chuẩn so sánh (miếng 1L/10L).
SJC_CODE = "SJL1L10"


def compute_premium(sjc_sell: float, xau_spot: float, usd_vnd: float) -> dict | None:
    """Chênh lệch giá SJC trong nước so với thế giới quy đổi.

    Trả về None khi thiếu bất kỳ đầu vào nào.
    """
    if not sjc_sell or not xau_spot or not usd_vnd:
        return None
    world = xau_spot * usd_vnd * OZ_PER_TAEL
    if world <= 0:
        return None
    gap = sjc_sell - world
    return {
        "world_vnd_luong": round(world),
        "gap_abs": round(gap),
        "gap_pct": round(gap / world * 100, 2),
    }
