"""Chi so co ban (fundamental) tu Fundamental().equity().ratio() — cache 6h."""
import re
import time

import pandas as pd

from backend import market

FUND_DIR = market.DATA / "fund"
FUND_DIR.mkdir(parents=True, exist_ok=True)

_PERIOD_RE = re.compile(r"^(\d{4})(?:-Q(\d))?")
_SKIP = {"item", "item_id"}


def _best_period_col(cols) -> object:
    """Chon cot ky ba moi nhat (2026-Q2 > 2026-Q1 > 2025-Q4_1 > ...)."""
    best, best_key = None, (-1, -1)
    for c in cols:
        s = re.sub(r"_\d+$", "", str(c))
        m = _PERIOD_RE.match(s)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2) or 4))
        if key > best_key:
            best, best_key = c, key
    return best


def _flatten_ratio(df) -> dict:
    out: dict[str, float] = {}
    if df is None or getattr(df, "empty", True) or "item_id" not in df.columns:
        return out
    cols = [c for c in df.columns if str(c) not in _SKIP]
    col = _best_period_col(cols) or (cols[-1] if cols else None)
    if col is None:
        return out
    for _, row in df.iterrows():
        k = str(row["item_id"]).strip()
        v = row[col]
        if not k or pd.isna(v):
            continue
        try:
            out[k] = round(float(v), 4)
        except (TypeError, ValueError):
            continue
    return out


def get_fundamentals(sym: str) -> dict:
    sym = sym.upper().strip()
    if not sym.isalpha() or not 2 <= len(sym) <= 6:
        return {"status": "error", "message": "Mã không hợp lệ"}
    path = FUND_DIR / f"{sym}.json"
    cached = market._fresh(path)       # TTL 6h
    if cached:
        return {"status": "ready", "data": cached.get("data", {}),
                "fetched_at": cached.get("fetched_at")}
    try:
        from vnstock import Fundamental

        def _fetch():
            return Fundamental().equity(sym).ratio()

        df = market.paced(_fetch)
        data = _flatten_ratio(df)
        if not data:
            return {"status": "error", "message": f"Không có chỉ số cơ bản cho {sym}"}
        market._save(path, {"fetched_at": time.time(), "data": data})
        return {"status": "ready", "data": data, "fetched_at": time.time()}
    except Exception as e:
        stale = market._cached(path)
        if stale:
            return {"status": "ready", "data": stale.get("data", {}),
                    "stale": True, "fetched_at": stale.get("fetched_at")}
        return {"status": "error", "message": f"Lỗi tải cơ bản {sym}: {e}"}
