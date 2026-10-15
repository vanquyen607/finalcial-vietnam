"""Du lieu tung ma co phieu — lich su gia, phan tich ky thuat, cache 6h."""
import json
import time

import pandas as pd

from backend.calc import compute
from backend.store import SKILL_DATA, SYM_DIR, _cached, _fresh, _save
from backend.vnrate import paced


def _quote_history(sym: str) -> pd.DataFrame:
    from vnstock import Quote
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=430)
    df = Quote(symbol=sym, source="VCI").history(
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), interval="1D")
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={"time": "Date", "open": "Open", "high": "High",
                            "low": "Low", "close": "Close", "volume": "Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    df = df[~df.index.duplicated(keep="last")].tail(260)
    return df


def _seed_symbol(sym: str) -> dict | None:
    """Khai pha du lieu da co trong skill (khong can go API)."""
    p = SKILL_DATA / f"{sym.lower()}_data.json"
    if not p.exists():
        return None
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        data = compute(sym, df)
        if data:
            data["seed"] = True
            return data
    except Exception:
        return None
    return None


def _seeded_cache(sym: str):
    """Seed chi dung trong bo nho khi khong co cache, khong ghi de du lieu live."""
    data = _seed_symbol(sym)
    if data:
        return {"fetched_at": time.time(), "data": data}
    return None


def get_symbol(sym: str, refresh: bool = False, priority: bool = False) -> dict:
    sym = sym.upper().strip()
    if not sym.isalpha() or not 2 <= len(sym) <= 6:
        return {"status": "error", "message": "Mã không hợp lệ"}
    path = SYM_DIR / f"{sym}.json"
    if not refresh:
        cached = _fresh(path)
        if cached:
            return {"status": "ready", "data": cached["data"]}
    try:
        df = paced(_quote_history, sym, priority=priority)
        data = compute(sym, df)
        if data is None:
            return {"status": "error", "message": f"Không lấy được dữ liệu {sym}"}
        _save(path, {"fetched_at": time.time(), "data": data})
        return {"status": "ready", "data": data}
    except Exception as e:
        cached = _fresh(path) or _cached(path) or _seeded_cache(sym)
        if cached:
            return {"status": "ready", "data": cached.get("data", cached), "stale": True}
        return {"status": "error", "message": f"Lỗi tải {sym}: {e}"}
