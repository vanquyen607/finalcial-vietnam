"""Chi so co ban (fundamental) tu Fundamental().equity().ratio() — cache 6h.

Stale-while-revalidate: cache het han van tra ngay (stale=True), refresh o nen.
Live request dung priority=True de khong xep hang sau screen worker.
"""
import re
import threading
import time

import pandas as pd

from backend import market

FUND_DIR = market.DATA / "fund"
FUND_DIR.mkdir(parents=True, exist_ok=True)

_PERIOD_RE = re.compile(r"^(\d{4})(?:-Q(\d))?")
_SKIP = {"item", "item_id"}

_inflight: set[str] = set()
_inflight_lock = threading.Lock()


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


def _fetch_and_save(sym: str) -> dict | None:
    from vnstock import Fundamental
    df = market.paced(lambda: Fundamental().equity(sym).ratio(), priority=True)
    data = _flatten_ratio(df)
    if not data:
        return None
    market._save(FUND_DIR / f"{sym}.json", {"fetched_at": time.time(), "data": data})
    return data


def get_fundamentals(sym: str) -> dict:
    sym = sym.upper().strip()
    if not sym.isalpha() or not 2 <= len(sym) <= 6:
        return {"status": "error", "message": "Mã không hợp lệ"}
    path = FUND_DIR / f"{sym}.json"
    cached = market._fresh(path)       # TTL 6h
    if cached:
        return {"status": "ready", "data": cached.get("data", {}),
                "fetched_at": cached.get("fetched_at")}
    stale = market._cached(path)       # het han nhung van dung duoc
    if stale and stale.get("data"):
        # tra ngay, refresh o nen (khong cho 2 thread cung refresh 1 ma)
        with _inflight_lock:
            if sym not in _inflight:
                _inflight.add(sym)
                threading.Thread(target=_refresh_bg, args=(sym,), daemon=True).start()
        return {"status": "ready", "data": stale["data"], "stale": True,
                "fetched_at": stale.get("fetched_at")}
    try:
        data = _fetch_and_save(sym)
        if not data:
            return {"status": "error", "message": f"Không có chỉ số cơ bản cho {sym}"}
        return {"status": "ready", "data": data, "fetched_at": time.time()}
    except Exception as e:
        return {"status": "error", "message": f"Lỗi tải cơ bản {sym}: {e}"}


def _refresh_bg(sym: str) -> None:
    try:
        _fetch_and_save(sym)
    except Exception:
        pass
    finally:
        with _inflight_lock:
            _inflight.discard(sym)
