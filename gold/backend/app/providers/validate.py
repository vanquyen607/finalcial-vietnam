from __future__ import annotations

import math


def num(value: object) -> float | None:
    """Ép số, trả None khi không phải số hữu hạn (chống payload bẩn)."""
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None
