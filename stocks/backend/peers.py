# -*- coding: utf-8 -*-
"""So sanh nganh (peer) — ROE, P/E, P/B cua cac ma cung sector.

Cache mapping industry theo 7 ngay; lay metric tu fund cache (khong goi API them).
Neu khong du 3 peers trong BASKET, lay them tu sectors list nhung chi hien ROE neu co.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from backend.store import BASKET, DATA, _cached, _fresh, _save

PEER_DIR = DATA / "peers"
PEER_DIR.mkdir(parents=True, exist_ok=True)
FUND_DIR = DATA / "fund"
IND_TTL = 7 * 24 * 3600  # 7 ngay

_ind_lock = threading.Lock()
_ind_inflight = False


def _fetch_industry_map() -> dict[str, dict] | None:
    """symbol -> {industry_code, industry_name}."""
    from vnstock import Reference
    df = Reference().industry.sectors()
    if df is None or getattr(df, "empty", True):
        return None
    out = {}
    for _, r in df.iterrows():
        sym = str(r.get("symbol", "")).strip().upper()
        if not sym:
            continue
        out[sym] = {
            "code": r.get("industry_code"),
            "name": r.get("industry_name"),
        }
    return out


def _get_industry_map() -> dict[str, dict]:
    path = PEER_DIR / "industry_map.json"
    cached = _fresh(path)
    if cached and time.time() - cached.get("fetched_at", 0) < IND_TTL:
        return cached.get("map", {})
    stale = _cached(path)
    if stale and time.time() - stale.get("fetched_at", 0) < IND_TTL:
        return stale.get("map", {})
    # fetch o nen
    global _ind_inflight
    with _ind_lock:
        if not _ind_inflight:
            _ind_inflight = True
            threading.Thread(target=lambda: _bg_refresh(), daemon=True).start()
    if stale:
        return stale.get("map", {})
    return {}


def _bg_refresh():
    global _ind_inflight
    try:
        m = _fetch_industry_map()
        if m:
            _save(PEER_DIR / "industry_map.json", {"fetched_at": time.time(), "map": m})
    except Exception:
        pass
    finally:
        with _ind_lock:
            _ind_inflight = False


def _load_fund(sym: str) -> dict:
    p = FUND_DIR / f"{sym}.json"
    obj = _cached(p)
    if obj:
        return obj.get("data", {})
    return {}


def _metric(data: dict, key: str) -> float | None:
    """Trich 1 metric (percent)."""
    v = data.get(key)
    if v is None:
        return None
    try:
        f = float(v)
        # ratio tra ve % (e.g. 18.5) — neu <1 co the la decimal, x2 de %
        if 0 < abs(f) < 1:
            f *= 100
        return round(f, 2)
    except (TypeError, ValueError):
        return None


def get_peers(sym: str) -> dict:
    sym = sym.upper().strip()
    if not sym.isalpha() or not 2 <= len(sym) <= 6:
        return {"status": "error", "message": "Mã không hợp lệ"}

    ind_map = _get_industry_map()
    my_ind = ind_map.get(sym)
    if not my_ind:
        return {"status": "error",
                "message": f"Không tìm thấy ngành của {sym}. Thử lại sau.",
                "map_ready": False}

    peers_in_sector = [
        s for s, info in ind_map.items()
        if info.get("code") == my_ind.get("code") and s != sym
    ]

    # uu tien peers trong BASKET (da co fund cache)
    basket_peers = [s for s in peers_in_sector if s in BASKET]
    others = [s for s in peers_in_sector if s not in BASKET]
    # gioi han 10 peers
    peer_list = basket_peers[:10] + others[:max(0, 10 - len(basket_peers))]

    # lay metrics
    rows = []
    my_fund = _load_fund(sym)
    my_row = {
        "symbol": sym,
        "is_self": True,
        "roe": _metric(my_fund, "roe"),
        "roa": _metric(my_fund, "roa"),
        "pe": _metric(my_fund, "pe_ratio"),
        "pb": _metric(my_fund, "pb_ratio"),
        "eps": _metric(my_fund, "trailing_eps"),
    }
    rows.append(my_row)

    peer_stats = {"roe": [], "roa": [], "pe": [], "pb": []}
    for p in peer_list:
        f = _load_fund(p)
        if not f:
            continue
        row = {
            "symbol": p,
            "is_self": False,
            "roe": _metric(f, "roe"),
            "roa": _metric(f, "roa"),
            "pe": _metric(f, "pe_ratio"),
            "pb": _metric(f, "pb_ratio"),
            "eps": _metric(f, "trailing_eps"),
        }
        rows.append(row)
        for k in peer_stats:
            if row.get(k) is not None:
                peer_stats[k].append(row[k])

    # tinh trung binh peers (khong tinh self)
    def _avg(vals):
        return round(sum(vals) / len(vals), 2) if vals else None

    avg = {k: _avg(v) for k, v in peer_stats.items()}

    # xep hang: 1 = tot nhat trong nganh
    def _rank(key, higher_better=True, valid_only=True):
        vals = [(r["symbol"], r.get(key)) for r in rows if r.get(key) is not None]
        if not vals:
            return None
        vals.sort(key=lambda x: x[1], reverse=higher_better)
        for i, (s, _) in enumerate(vals, 1):
            if s == sym:
                return i
        return None

    ranks = {
        "roe": _rank("roe", higher_better=True),
        "pe": _rank("pe", higher_better=False),  # PE thap = re hon
        "pb": _rank("pb", higher_better=False),
    }

    # so sanh voi trung binh
    comp = {}
    for k in ("roe", "roa", "pe", "pb"):
        my_v = my_row.get(k)
        avg_v = avg.get(k)
        if my_v is not None and avg_v is not None and avg_v != 0:
            comp[k] = round((my_v - avg_v) / abs(avg_v) * 100, 1)  # %

    return {
        "status": "ready",
        "industry": my_ind,
        "rows": rows,
        "avg": avg,
        "ranks": ranks,
        "comp_vs_avg": comp,
        "peer_count": len(rows) - 1,
        "sector_total": len(peers_in_sector),
        "map_ready": True,
    }
