# -*- coding: utf-8 -*-
"""Xu huong BCTC theo quy + nam — cache 24h.

Community tier: ratio() chi tra ~3-4 quy gan nhat; income_statement() tra 4 nam.
Gop 2 nguon de ve trend: ROE, tang truong doanh thu, tang truong loi nhuan.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

import pandas as pd

from backend.store import DATA, _cached, _fresh, _save
from backend.vnrate import paced

TREND_DIR = DATA / "fundtrend"
TREND_DIR.mkdir(parents=True, exist_ok=True)

_inflight: set[str] = set()
_inflight_lock = threading.Lock()

# item_id trong ratio df
_RATIO_KEYS = {
    "roe": "roe",
    "roa": "roa",
    "net_revenue": "rev_growth",
    "gross_profit": "gp_growth",
    "profit_before_tax": "pbt_growth",
    "profit_after_tax_for_shareholders_of_the_parent_company": "pat_growth",
    "trailing_eps": "eps",
}

# item_id trong income_statement df
_IS_KEYS = {
    "revenue": "revenue",
    "net_profit": "profit",
    "profit_after_tax_for_shareholders_of_parent_company": "profit_parent",
    "gross_profit": "gross_profit",
    "earnings_per_share_vnd": "eps",
}


def _period_sort_key(col: str) -> tuple:
    """'2026-Q2' -> (2026, 2); '2026-Q2_1' -> (2026, 2)."""
    s = re.sub(r"_\d+$", "", str(col))
    m = re.match(r"(\d{4})(?:-Q(\d))?", s)
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2) or 4))


def _parse_ratio_quarterly(df) -> list[dict]:
    """Ratio df (item, item_id, 2026-Q2, ...) -> [{period, roe, rev_growth, ...}]."""
    if df is None or getattr(df, "empty", True) or "item_id" not in df.columns:
        return []
    cols = [c for c in df.columns if c not in ("item", "item_id")]
    cols = sorted(cols, key=_period_sort_key)
    # deduplicate same period (keep first = original, drop _1, _2)
    seen: set[str] = set()
    uniq_cols = []
    for c in cols:
        base = re.sub(r"_\d+$", "", str(c))
        if base not in seen:
            seen.add(base)
            uniq_cols.append(c)
    out = []
    for c in uniq_cols:
        row: dict = {"period": re.sub(r"_\d+$", "", str(c))}
        for _, r in df.iterrows():
            iid = str(r["item_id"]).strip()
            key = _RATIO_KEYS.get(iid)
            if not key:
                continue
            v = r[c]
            if pd.isna(v):
                continue
            try:
                row[key] = round(float(v), 4)
            except (TypeError, ValueError):
                continue
        if len(row) > 1:  # co du lieu
            out.append(row)
    return out


def _parse_is_annual(df) -> list[dict]:
    """Income statement df -> [{year, revenue, profit, ...}] tang dan."""
    if df is None or getattr(df, "empty", True) or "item_id" not in df.columns:
        return []
    cols = [c for c in df.columns if c not in ("item", "item_id")]
    year_cols = sorted([c for c in cols if str(c).isdigit()], key=str)
    # revenue xuat hien 2 lan (doanh thu ban hang + doanh thu thuan) — lay "3. Doanh thu thuần"
    rev_rows = df[df["item_id"] == "revenue"]
    rev_row = None
    for _, rr in rev_rows.iterrows():
        if "thuần" in str(rr["item"]).lower() or "3." in str(rr["item"]):
            rev_row = rr
            break
    if rev_row is None and not rev_rows.empty:
        rev_row = rev_rows.iloc[0]

    out = []
    for c in year_cols:
        row: dict = {"year": int(c)}
        for _, r in df.iterrows():
            iid = str(r["item_id"]).strip()
            key = _IS_KEYS.get(iid)
            if not key:
                continue
            v = r[c]
            if pd.isna(v):
                continue
            try:
                if key == "eps":
                    row[key] = round(float(v) / 1_000_000, 0)
                else:
                    row[key] = round(float(v) / 1e9, 1)  # ty VND
            except (TypeError, ValueError):
                continue
        # revenue dung (thuan) thay vi doanh thu goc
        if rev_row is not None and not pd.isna(rev_row.get(c, float("nan"))):
            try:
                row["revenue"] = round(float(rev_row[c]) / 1e9, 1)
            except (TypeError, ValueError):
                pass
        if "revenue" in row or "profit" in row:
            out.append(row)
    return out


def _fetch_and_save(sym: str) -> dict | None:
    from vnstock import Fundamental
    eq = paced(lambda: Fundamental().equity(sym), priority=True)
    ratio_df = paced(lambda: eq.ratio(frequency="quarter"), priority=True)
    is_df = paced(lambda: eq.income_statement(frequency="annual"), priority=True)
    quarters = _parse_ratio_quarterly(ratio_df)
    years = _parse_is_annual(is_df)
    if not quarters and not years:
        return None
    data = {"quarters": quarters, "years": years}
    _save(TREND_DIR / f"{sym}.json", {"fetched_at": time.time(), "data": data})
    return data


def get_fundtrend(sym: str) -> dict:
    sym = sym.upper().strip()
    if not sym.isalpha() or not 2 <= len(sym) <= 6:
        return {"status": "error", "message": "Mã không hợp lệ"}
    path = TREND_DIR / f"{sym}.json"
    cached = _fresh(path)
    if cached:
        return {"status": "ready", "data": cached.get("data", {})}
    stale = _cached(path)
    if stale and stale.get("data"):
        with _inflight_lock:
            if sym not in _inflight:
                _inflight.add(sym)
                threading.Thread(target=lambda: (_fetch_and_save(sym),
                                                 _inflight.discard(sym)), daemon=True).start()
        return {"status": "ready", "data": stale["data"], "stale": True}
    try:
        data = _fetch_and_save(sym)
        if data:
            return {"status": "ready", "data": data}
        return {"status": "error", "message": f"Không có dữ liệu BCTC {sym}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
