# -*- coding: utf-8 -*-
"""Room ngoai + do lech tai chinh (vay) theo ma.

- Room ngoai: tu Market().equity().quote() — foreign_room, foreign_buy/sell_volume.
- Vay/con cac ma: tu Fundamental().equity().balance_sheet() — short/long_term_borrowings.
  (Dư vay ký quỹ theo mã la data broker, khong co trong community tier — thay bang leverage CTY.)
Cache 24h.
"""
from __future__ import annotations

import threading
import time

from backend.store import DATA, _cached, _fresh, _save
from backend.vnrate import paced

FLOW_DIR = DATA / "flow"
FLOW_DIR.mkdir(parents=True, exist_ok=True)
TTL = 24 * 3600

_inflight: set[str] = set()
_inflight_lock = threading.Lock()


def _fetch_flow(sym: str) -> dict:
    """Room ngoai tu quote."""
    from vnstock import Market
    df = paced(lambda: Market().equity(sym).quote(), priority=True)
    out: dict = {}
    if df is None or getattr(df, "empty", True):
        return out
    row = df.iloc[-1]
    def _f(k):
        try:
            v = row.get(k)
            return float(v) if v is not None and v == v else None  # NaN check
        except (TypeError, ValueError):
            return None
    out["foreign_room"] = _f("foreign_room")
    out["foreign_buy"] = _f("foreign_buy_volume")
    out["foreign_sell"] = _f("foreign_sell_volume")
    out["foreign_net"] = (out["foreign_buy"] - out["foreign_sell"]
                          if out["foreign_buy"] is not None and out["foreign_sell"] is not None
                          else None)
    return out


def _fetch_leverage(sym: str) -> dict:
    """Vay/con + ty le no tu balance sheet (annual, gan nhat)."""
    from vnstock import Fundamental
    bs = paced(lambda: Fundamental().equity(sym).balance_sheet(frequency="annual"),
               priority=True)
    out: dict = {}
    if bs is None or getattr(bs, "empty", True) or "item_id" not in bs.columns:
        return out
    # chon cot nam moi nhat
    year_cols = sorted([c for c in bs.columns if c not in ("item", "item_id") and str(c).isdigit()],
                       key=str)
    if not year_cols:
        return out
    col = year_cols[-1]
    vals: dict[str, float] = {}
    for _, r in bs.iterrows():
        iid = str(r["item_id"]).strip()
        v = r.get(col)
        if v is None or v != v:  # NaN
            continue
        try:
            vals[iid] = float(v)
        except (TypeError, ValueError):
            continue

    def _sum(*keys):
        return sum(vals.get(k, 0.0) for k in keys)

    st_borrow = _sum("short_term_borrowings_and_financial_leases",
                     "short_term_loans_from_other_financial_institutions",
                     "short_term_bonds_issued")
    lt_borrow = _sum("long_term_borrowings_and_financial_leases",
                     "long_term_loans_from_other_financial_institutions",
                     "long_term_bonds_issued")
    equity = _sum("owners_equity_3", "owners_equity_2",
                  "total_equity_outside_shareholders", "equity")
    assets = _sum("total_assets", "assets", "total_assets_and_other_items")
    revenue = _sum("revenue")
    profit = _sum("net_profit", "profit_after_tax_for_shareholders_of_parent_company")

    total_debt = st_borrow + lt_borrow
    out["year"] = int(col)
    out["st_borrow"] = round(st_borrow / 1e9, 1) if st_borrow else None   # ty VND
    out["lt_borrow"] = round(lt_borrow / 1e9, 1) if lt_borrow else None
    out["total_debt"] = round(total_debt / 1e9, 1) if total_debt else None
    out["equity"] = round(equity / 1e9, 1) if equity else None
    # ty le no = vay / von chu so huu
    if equity and total_debt:
        out["debt_to_equity"] = round(total_debt / equity, 2)
    # no/tai san
    if assets and total_debt:
        out["debt_to_assets"] = round(total_debt / assets * 100, 1)
    # Lợi nhuận/so voi lai vay (don vi %)
    if total_debt and profit:
        out["interest_coverage_proxy"] = round(profit / total_debt * 100, 1)
    return out


def _fetch_and_save(sym: str) -> dict | None:
    flow = _fetch_flow(sym)
    lev = _fetch_leverage(sym)
    if not flow and not lev:
        return None
    data = {**flow, **lev}
    _save(FLOW_DIR / f"{sym}.json", {"fetched_at": time.time(), "data": data})
    return data


def get_flow(sym: str) -> dict:
    sym = sym.upper().strip()
    if not sym.isalpha() or not 2 <= len(sym) <= 6:
        return {"status": "error", "message": "Mã không hợp lệ"}
    path = FLOW_DIR / f"{sym}.json"
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
        return {"status": "error", "message": f"Không có dữ liệu flow {sym}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
