# -*- coding: utf-8 -*-
"""Portfolio + P&L tracking — server-side JSON, 1 user.

Position: {symbol, qty, avg_price, updated_at}
P&L tinh tu close price hien tai (tu sym cache) vs avg_price.
"""
from __future__ import annotations

import time

from backend.store import DATA, _cached, _save

PORT_PATH = DATA / "portfolio.json"


def _load() -> dict:
    obj = _cached(PORT_PATH)
    if obj and "positions" in obj:
        return obj
    return {"positions": [], "updated_at": 0}


def _save_port(port: dict) -> None:
    port["updated_at"] = time.time()
    _save(PORT_PATH, port)


def _get_close(sym: str) -> float | None:
    obj = _cached(DATA / "sym" / f"{sym}.json")
    if not obj or not obj.get("data"):
        return None
    return obj["data"].get("close")


def list_positions() -> list[dict]:
    port = _load()
    out = []
    for p in port["positions"]:
        sym = p["symbol"]
        close = _get_close(sym)
        qty = p["qty"]
        avg = p["avg_price"]
        value = close * qty if close else None
        cost = avg * qty
        pl = (value - cost) if value is not None else None
        pl_pct = (pl / cost * 100) if pl is not None and cost else None
        out.append({
            **p,
            "close": close,
            "value": round(value, 0) if value is not None else None,
            "cost": round(cost, 0),
            "pl": round(pl, 0) if pl is not None else None,
            "pl_pct": round(pl_pct, 2) if pl_pct is not None else None,
        })
    return out


def add_position(symbol: str, qty: float, avg_price: float) -> dict:
    sym = symbol.upper().strip()
    if not sym.isalpha() or not 2 <= len(sym) <= 6:
        raise ValueError("Mã không hợp lệ")
    if qty <= 0:
        raise ValueError("Số lượng phải > 0")
    if avg_price <= 0:
        raise ValueError("Giá bình quân phải > 0")
    # round qty theo so le VN (100 cp)
    qty = float(qty)

    port = _load()
    # neu da co -> tinh binh quan cong them
    for p in port["positions"]:
        if p["symbol"] == sym:
            total_qty = p["qty"] + qty
            p["avg_price"] = (p["avg_price"] * p["qty"] + avg_price * qty) / total_qty
            p["qty"] = total_qty
            p["updated_at"] = time.time()
            _save_port(port)
            return {"action": "merged", "position": p}
    pos = {"symbol": sym, "qty": qty, "avg_price": avg_price,
           "updated_at": time.time()}
    port["positions"].append(pos)
    _save_port(port)
    return {"action": "added", "position": pos}


def remove_position(symbol: str) -> bool:
    sym = symbol.upper().strip()
    port = _load()
    before = len(port["positions"])
    port["positions"] = [p for p in port["positions"] if p["symbol"] != sym]
    if len(port["positions"]) == before:
        return False
    _save_port(port)
    return True


def update_position(symbol: str, qty: float, avg_price: float) -> dict:
    sym = symbol.upper().strip()
    if qty <= 0:
        return remove_position(sym) and {"action": "removed"} or (_ for _ in ()).throw(ValueError("Không tìm thấy"))
    if avg_price <= 0:
        raise ValueError("Giá bình quân phải > 0")
    port = _load()
    for p in port["positions"]:
        if p["symbol"] == sym:
            p["qty"] = float(qty)
            p["avg_price"] = avg_price
            p["updated_at"] = time.time()
            _save_port(port)
            return {"action": "updated", "position": p}
    raise ValueError(f"Không có {sym} trong danh mục")


def get_summary() -> dict:
    positions = list_positions()
    total_value = sum(p["value"] for p in positions if p["value"] is not None)
    total_cost = sum(p["cost"] for p in positions)
    total_pl = total_value - total_cost if positions else 0
    total_pl_pct = (total_pl / total_cost * 100) if total_cost else None
    # phan bo von
    alloc = []
    for p in positions:
        if p["value"] is not None and total_value:
            alloc.append({"symbol": p["symbol"],
                          "weight": round(p["value"] / total_value * 100, 1)})
    alloc.sort(key=lambda x: -x["weight"])
    return {
        "positions": positions,
        "total_value": round(total_value, 0),
        "total_cost": round(total_cost, 0),
        "total_pl": round(total_pl, 0),
        "total_pl_pct": round(total_pl_pct, 2) if total_pl_pct is not None else None,
        "allocation": alloc,
        "count": len(positions),
    }
