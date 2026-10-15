"""Do rong thi truong — tang/giam/dung + GTGD + dong tien ngoai theo san (bang gia VCI)."""
import threading
import time

import pandas as pd

from backend.calc import to_dong
from backend.store import DATA, _cached, _save, now_vn
from backend.vnrate import paced

BREADTH_TTL = 15 * 60
_breadth_lock = threading.Lock()
_breadth_state = {"status": "init", "data": None}


class _OffHours(Exception):
    """Bang gia dang reset (gio nghi) — giu cache cu thay vi ghi de bang 0."""


def _exchange_bucket(v) -> str | None:
    v = (str(v) if v is not None else "").strip().upper()
    if v in ("HSX", "HOSE"):
        return "hose"
    if v == "HNX":
        return "hnx"
    if v in ("UPCOM", "UPCOMINDEX"):
        return "upcom"
    return None


def _breadth_symbols() -> dict[str, list[str]]:
    """Nhom ma co phieu theo san. symbols_by_exchange tra toan bo kho (3683 dong)."""
    from vnstock import Listing
    lst = paced(lambda: Listing(source="VCI").symbols_by_exchange(exchange="HOSE"))
    if lst is None or lst.empty or "symbol" not in lst.columns:
        return {}
    ex_c, ty_c = ("exchange", "type")
    out: dict[str, list[str]] = {"hose": [], "hnx": [], "upcom": []}
    for _, r in lst.iterrows():
        ty = str(r.get(ty_c, "")).strip().upper()
        if ty != "STOCK":
            continue
        b = _exchange_bucket(r.get(ex_c))
        s = str(r["symbol"]).strip().upper()
        if b and s and s.isalpha() and 2 <= len(s) <= 5:
            out[b].append(s)
    return {b: sorted(set(v)) for b, v in out.items()}


def _breadth_build() -> dict:
    from vnstock import Trading
    groups = _breadth_symbols()
    all_syms = [s for v in groups.values() for s in v]
    if len(all_syms) < 100:
        raise RuntimeError("Danh sách mã quá ít — không tin được")
    board = Trading(source="VCI")
    frames = []
    for i in range(0, len(all_syms), 250):
        chunk = all_syms[i:i + 250]
        # di qua paced: dong bo voi cac goi vnstock khac (GAP 7.5s), retry rate limit
        df = paced(board.price_board, chunk)
        if df is not None and not df.empty:
            frames.append(df)
    if not frames:
        raise RuntimeError("Bảng giá rỗng")
    df = pd.concat(frames, ignore_index=True)

    last = pd.to_numeric(df[("match", "match_price")], errors="coerce").fillna(0)
    ref = pd.to_numeric(df[("match", "reference_price")], errors="coerce").fillna(0)
    val = pd.to_numeric(df[("match", "accumulated_value")], errors="coerce").fillna(0)
    fbv = pd.to_numeric(df[("match", "foreign_buy_value")], errors="coerce").fillna(0)
    fsv = pd.to_numeric(df[("match", "foreign_sell_value")], errors="coerce").fillna(0)
    live = last > 0
    if float(live.mean()) < 0.2:
        raise _OffHours()          # ngoai gio / board dang reset — giu cache cu

    # accumulated_value cua VCI dang o don vi TRIEU dong — quy ve dong truoc khi chia 1e9
    val = to_dong(val)

    bucket = df[("listing", "exchange")].map(_exchange_bucket)
    chg = pd.Series(0.0, index=df.index)
    m = live & (ref > 0)
    chg[m] = (last[m] - ref[m]) / ref[m] * 100
    up = ((chg > 0.05) & live).groupby(bucket).sum()
    down = ((chg < -0.05) & live).groupby(bucket).sum()
    flat = ((~live) | (chg.abs() <= 0.05)).groupby(bucket).sum()
    value_t = (val / 1e9).groupby(bucket).sum()
    fnet_t = ((fbv - fsv) / 1e9).groupby(bucket).sum()

    exch = {}
    for b in ("hose", "hnx", "upcom"):
        exch[b] = {
            "up": int(up.get(b, 0)), "down": int(down.get(b, 0)), "flat": int(flat.get(b, 0)),
            "value_t": round(float(value_t.get(b, 0.0)), 0),
            "fnet_t": round(float(fnet_t.get(b, 0.0)), 1),
            "n": int((bucket == b).sum()),
        }
    tot = {k: sum(exch[b][k] for b in exch) for k in ("up", "down", "flat", "value_t")}
    tot["value_t"] = round(tot["value_t"], 0)
    tot["fnet_t"] = round(sum(exch[b]["fnet_t"] for b in exch), 1)
    return {"exchanges": exch, "total": tot, "fetched_at": time.time(),
            "updated_at": now_vn().strftime("%H:%M:%S %d/%m/%Y")}


def breadth(refresh: bool = False) -> dict:
    global _breadth_state
    path = DATA / "breadth.json"
    with _breadth_lock:
        st = dict(_breadth_state)
    now = time.time()
    if st["status"] == "ready" and st["data"] and not refresh:
        if now - st["data"].get("fetched_at", 0) < BREADTH_TTL:
            return {"status": "ready", **st["data"]}
        # het TTL — xuong duoi de build lai tu dong
    if not refresh:
        cached = _cached(path)
        if cached:
            inner = cached.get("data") or cached
            if now - inner.get("fetched_at", 0) < BREADTH_TTL:
                with _breadth_lock:
                    _breadth_state = {"status": "ready", "data": inner}
                return {"status": "ready", **inner}
    with _breadth_lock:
        if _breadth_state["status"] == "loading":
            return {"status": "fetching"}
        _breadth_state = {"status": "loading", "data": None}
    try:
        data = _breadth_build()
        _save(path, {"fetched_at": time.time(), "data": data})
        with _breadth_lock:
            _breadth_state = {"status": "ready", "data": data}
        return {"status": "ready", **data}
    except _OffHours:
        old = _cached(path)
        inner = (old or {}).get("data")
        if inner:
            with _breadth_lock:
                _breadth_state = {"status": "ready", "data": inner}
            return {"status": "ready", "stale": True, **inner}
        with _breadth_lock:
            _breadth_state = {"status": "idle", "data": None}
        return {"status": "empty", "message": "Ngoài giờ giao dịch — chưa có dữ liệu"}
    except Exception as e:
        with _breadth_lock:
            _breadth_state = {"status": "error", "data": None}
        return {"status": "error", "message": str(e)}
