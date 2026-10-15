"""Chi so thi truong (VN-Index, HNX, UPCOM) — cache 6h, tu refresh khi stale."""
import json
import threading
import time

import pandas as pd

from backend.store import DATA, ROOT, _cached, _fresh, _save, now_vn
from backend.vnrate import paced


def _index_df(code: str) -> pd.DataFrame:
    from vnstock import Quote
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=430)
    df = Quote(symbol=code, source="VCI").history(
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), interval="1D")
    df = df.rename(columns={"time": "Date", "close": "Close", "high": "High", "low": "Low", "volume": "Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date").sort_index()


def _ma(s: pd.Series, n: int) -> float | None:
    """MA an toan JSON — du lieu ngan (UPCOM ~45 phien) se ra None thay vi NaN."""
    return float(s.rolling(n).mean().iloc[-1]) if len(s) >= n else None


def _build_overview(refresh: bool = False) -> dict:
    items = []
    for code, label in (("VNINDEX", "VN-Index"), ("HNXINDEX", "HNX-Index"),
                        ("UPCOMINDEX", "UPCOM-Index")):
        try:
            df = paced(_index_df, code, priority=refresh)
            c = df["Close"]
            if len(c) < 2:
                continue
            last = float(c.iloc[-1])
            prev = float(c.iloc[-2])
            ma20, ma50, ma200 = _ma(c, 20), _ma(c, 50), _ma(c, 200)
            r20 = (last / float(c.iloc[-21]) - 1) * 100 if len(c) >= 21 else None
            above20 = last > ma20 if ma20 is not None else None
            above200 = last > ma200 if ma200 is not None else None
            if above20 and (ma50 is None or last > ma50):
                trend = "hồi phục / đi ngang"
            elif ma200 is not None and last > ma200:
                trend = "điều chỉnh nhưng trên MA200"
            elif ma200 is None:
                trend = "đi ngang / dữ liệu MA dài chưa đủ"
            else:
                trend = "giảm ngắn hạn (dưới MA20/MA50)"
            items.append({
                "code": code, "label": label,
                "close": round(last, 2),
                "chg": round(last - prev, 2),
                "chg_pct": round((last / prev - 1) * 100, 2),
                "ma20": round(ma20, 1) if ma20 is not None else None,
                "ma50": round(ma50, 1) if ma50 is not None else None,
                "ma200": round(ma200, 1) if ma200 is not None else None,
                "r20": round(r20, 1) if r20 is not None else None,
                "hi30": round(float(c.tail(30).max()), 1),
                "lo30": round(float(c.tail(30).min()), 1),
                "vol_last_m": round(float(df["Volume"].iloc[-1]) / 1e6, 1),
                "vol20_m": (round(float(df["Volume"].rolling(20).mean().iloc[-1]) / 1e6, 1)
                            if len(df) >= 20 else None),
                "date": str(df.index[-1].date()),
                "trend": trend,
                "above_ma20": above20, "above_ma200": above200,
            })
        except Exception:
            continue        # 1 chi so that khong keo het overview (fail-safe)
    if not items:
        raise RuntimeError("Không lấy được chỉ số nào")
    return {"indices": items, "fetched_at": time.time(),
            "updated_at": now_vn().strftime("%H:%M:%S %d/%m/%Y")}


_ov_lock = threading.Lock()
_ov_state = {"status": "init", "data": None}


def overview(refresh: bool = False) -> dict:
    global _ov_state
    with _ov_lock:
        st = _ov_state
    if st["status"] == "ready" and not refresh:
        if time.time() - st["data"].get("fetched_at", 0) < 30 * 60:
            return {"status": "ready", **st["data"]}
        return {"status": "ready", "stale": True, **st["data"]}

    path = DATA / "overview.json"
    if not refresh:
        cached = _fresh(path) or _cached(path) or _seed_overview()
        if cached:
            inner = cached.get("data") or cached
            inner.setdefault("fetched_at", cached.get("fetched_at", time.time()))
            with _ov_lock:
                _ov_state = {"status": "ready", "data": inner}
            age = time.time() - inner.get("fetched_at", 0)
            return {"status": "ready", "stale": age > 30 * 60, **inner}

    # fetch dong bo lan dau / refresh
    with _ov_lock:
        if _ov_state["status"] == "loading":
            return {"status": "fetching"}
        _ov_state = {"status": "loading", "data": None}
    try:
        data = _build_overview(refresh=refresh)
        _save(path, {"fetched_at": time.time(), "data": data})
        with _ov_lock:
            _ov_state = {"status": "ready", "data": data}
        return {"status": "ready", **data}
    except Exception as e:
        with _ov_lock:
            _ov_state = {"status": "error", "data": None}
        return {"status": "error", "message": str(e)}


def _seed_overview():
    p = ROOT.parent / "reports" / "index_2026-10-08.json"
    if not p.exists():
        return None
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
        items = []
        for r in rows:
            label = {"VNINDEX": "VN-Index", "HNXINDEX": "HNX-Index"}.get(r["index"], r["index"])
            last = r["close"]
            items.append({
                "code": r["index"], "label": label, "close": last,
                "chg": r["chg"], "chg_pct": r["chg_pct"],
                "ma20": r["ma20"], "ma50": r["ma50"], "ma200": r["ma200"],
                "r20": r["r20"], "hi30": r["hi30"], "lo30": r["lo30"],
                "vol_last_m": round(r.get("vol_last_m", 0), 1),
                "vol20_m": round(r.get("vol20_m", 0), 1),
                "date": r["date"],
                "trend": ("hồi phục / đi ngang" if last > r["ma20"] and last > r["ma50"]
                          else ("điều chỉnh nhưng trên MA200" if last > r["ma200"] else "giảm ngắn hạn (dưới MA20/MA50)")),
                "above_ma20": last > r["ma20"], "above_ma200": last > r["ma200"],
            })
        obj = {"fetched_at": time.time(), "data": {"indices": items, "fetched_at": time.time(),
                                                   "updated_at": "seed từ reports/index_2026-10-08.json"}}
        _save(DATA / "overview.json", obj)
        return obj
    except Exception:
        return None
