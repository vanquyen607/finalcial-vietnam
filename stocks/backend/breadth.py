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


def _board_debug(msg: str) -> None:
    try:
        with open(DATA / "_board_debug.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


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
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parent / "symbols_by_exchange.json"
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        out = {}
        for b in ("hose", "hnx", "upcom"):
            out[b] = sorted(set(str(s).strip().upper() for s in (obj.get(b) or []) if s))
        if sum(len(v) for v in out.values()) >= 100:
            return out
    except Exception:
        pass
    return {}


def _breadth_build() -> dict:
    # Gen 6 khong con VCI price_board mien phi -> dung cache cu neu co.
    raise _OffHours()


def breadth(refresh: bool = False) -> dict:
    global _breadth_state
    path = DATA / "breadth.json"
    with _breadth_lock:
        st = dict(_breadth_state)
    now = time.time()
    if st["status"] == "ready" and st["data"] and not refresh:
        if now - st["data"].get("fetched_at", 0) < BREADTH_TTL:
            return {"status": "ready", **st["data"]}
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
        return {"status": "empty", "message": "Ngoai gio giao dich — chua co du lieu"}
    except Exception as e:
        with _breadth_lock:
            _breadth_state = {"status": "error", "data": None}
        return {"status": "error", "message": str(e)}
