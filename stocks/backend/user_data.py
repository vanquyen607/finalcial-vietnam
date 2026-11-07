# -*- coding: utf-8 -*-
"""
Per-user data: watchlist, portfolio, transactions, alert_rules, alert_events,
user_prefs, stock_notes — tất cả gắn với uid (username).

Mọi hàm đều nhận uid làm tham số đầu tiên.
"""
from __future__ import annotations

import secrets
import time
from typing import Optional

from backend.db import get_conn


# ══════════════════════════════════════════════════════════════════
# SCHEMA MIGRATION (gọi khi startup)
# ══════════════════════════════════════════════════════════════════

def migrate_schema() -> None:
    """Tạo / cập nhật các bảng per-user. Idempotent — an toàn gọi nhiều lần."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id           SERIAL PRIMARY KEY,
                uid          TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                symbol       TEXT NOT NULL,
                added_at     DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
                note         TEXT NOT NULL DEFAULT '',
                price_target DOUBLE PRECISION,
                UNIQUE (uid, symbol)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id          SERIAL PRIMARY KEY,
                uid         TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                symbol      TEXT NOT NULL,
                qty         DOUBLE PRECISION NOT NULL,
                avg_price   DOUBLE PRECISION NOT NULL,
                updated_at  DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
                UNIQUE (uid, symbol)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          SERIAL PRIMARY KEY,
                uid         TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                symbol      TEXT NOT NULL,
                action      TEXT NOT NULL CHECK (action IN ('buy','sell')),
                qty         DOUBLE PRECISION NOT NULL,
                price       DOUBLE PRECISION NOT NULL,
                fee         DOUBLE PRECISION NOT NULL DEFAULT 0,
                note        TEXT NOT NULL DEFAULT '',
                executed_at DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id          TEXT PRIMARY KEY,
                uid         TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                symbol      TEXT NOT NULL,
                type        TEXT NOT NULL,
                threshold   DOUBLE PRECISION NOT NULL,
                note        TEXT NOT NULL DEFAULT '',
                active      BOOLEAN NOT NULL DEFAULT TRUE,
                created_at  DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_events (
                id           SERIAL PRIMARY KEY,
                uid          TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                rule_id      TEXT,
                symbol       TEXT NOT NULL,
                message      TEXT NOT NULL,
                triggered_at DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
                read         BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_prefs (
                uid          TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
                theme        TEXT NOT NULL DEFAULT 'dark',
                default_sym  TEXT NOT NULL DEFAULT 'VNM',
                notify_web   BOOLEAN NOT NULL DEFAULT FALSE,
                extra        JSONB NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_notes (
                uid          TEXT NOT NULL,
                symbol       TEXT NOT NULL,
                content      TEXT NOT NULL DEFAULT '',
                updated_at   DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
                PRIMARY KEY (uid, symbol)
            )
        """)
        # indexes
        for sql in [
            "CREATE INDEX IF NOT EXISTS wl_uid_idx ON watchlist(uid)",
            "CREATE INDEX IF NOT EXISTS port_uid_idx ON portfolio(uid)",
            "CREATE INDEX IF NOT EXISTS tx_uid_idx ON transactions(uid)",
            "CREATE INDEX IF NOT EXISTS tx_sym_idx ON transactions(uid, symbol)",
            "CREATE INDEX IF NOT EXISTS ar_uid_idx ON alert_rules(uid)",
            "CREATE INDEX IF NOT EXISTS ae_uid_idx ON alert_events(uid)",
            "CREATE INDEX IF NOT EXISTS ae_read_idx ON alert_events(uid, read)",
        ]:
            conn.execute(sql)
        conn.commit()


# ══════════════════════════════════════════════════════════════════
# WATCHLIST
# ══════════════════════════════════════════════════════════════════

def _validate_sym(symbol: str) -> str:
    s = symbol.upper().strip()
    if not s or not s.isalpha() or not 2 <= len(s) <= 7:
        raise ValueError(f"Mã không hợp lệ: {symbol!r}")
    return s


def watchlist_get(uid: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT symbol, added_at, note, price_target FROM watchlist WHERE uid=%s ORDER BY added_at DESC",
            (uid,),
        ).fetchall()
    return [{"symbol": r[0], "added_at": r[1], "note": r[2], "price_target": r[3]} for r in rows]


def watchlist_add(uid: str, symbol: str, note: str = "", price_target: Optional[float] = None) -> dict:
    sym = _validate_sym(symbol)
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO watchlist (uid, symbol, note, price_target, added_at)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (uid, symbol) DO UPDATE
                 SET note=EXCLUDED.note, price_target=EXCLUDED.price_target""",
            (uid, sym, note, price_target, time.time()),
        )
        conn.commit()
    return {"symbol": sym, "note": note, "price_target": price_target}


def watchlist_remove(uid: str, symbol: str) -> bool:
    sym = _validate_sym(symbol)
    with get_conn() as conn:
        n = conn.execute(
            "DELETE FROM watchlist WHERE uid=%s AND symbol=%s", (uid, sym)
        ).rowcount
        conn.commit()
    return n > 0


def watchlist_update(uid: str, symbol: str, note: Optional[str] = None, price_target: Optional[float] = None) -> dict:
    sym = _validate_sym(symbol)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT note, price_target FROM watchlist WHERE uid=%s AND symbol=%s", (uid, sym)
        ).fetchone()
        if not row:
            raise ValueError(f"{sym} không có trong watchlist")
        new_note = note if note is not None else row[0]
        new_pt = price_target if price_target is not None else row[1]
        conn.execute(
            "UPDATE watchlist SET note=%s, price_target=%s WHERE uid=%s AND symbol=%s",
            (new_note, new_pt, uid, sym),
        )
        conn.commit()
    return {"symbol": sym, "note": new_note, "price_target": new_pt}


# ══════════════════════════════════════════════════════════════════
# PORTFOLIO (per-user)
# ══════════════════════════════════════════════════════════════════

def _get_close_price(sym: str) -> Optional[float]:
    """Lấy giá đóng cửa từ cache Neon (store.py logic)."""
    try:
        from backend.store import _cached, DATA
        obj = _cached(DATA / "sym" / f"{sym}.json")
        if obj and obj.get("data"):
            return obj["data"].get("close")
    except Exception:
        pass
    return None


def portfolio_get(uid: str) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT symbol, qty, avg_price, updated_at FROM portfolio WHERE uid=%s ORDER BY updated_at DESC",
            (uid,),
        ).fetchall()
    positions = []
    total_cost = 0.0
    total_value = 0.0
    for sym, qty, avg_price, updated_at in rows:
        close = _get_close_price(sym)
        cost = avg_price * qty
        value = close * qty if close else None
        pl = (value - cost) if value is not None else None
        pl_pct = (pl / cost * 100) if pl is not None and cost else None
        total_cost += cost
        if value is not None:
            total_value += value
        positions.append({
            "symbol": sym, "qty": qty, "avg_price": avg_price,
            "close": close, "cost": round(cost),
            "value": round(value) if value is not None else None,
            "pl": round(pl) if pl is not None else None,
            "pl_pct": round(pl_pct, 2) if pl_pct is not None else None,
            "updated_at": updated_at,
        })
    total_pl = total_value - total_cost
    alloc = []
    if total_value:
        for p in positions:
            if p["value"]:
                alloc.append({"symbol": p["symbol"],
                               "weight": round(p["value"] / total_value * 100, 1)})
        alloc.sort(key=lambda x: -x["weight"])
    return {
        "positions": positions,
        "total_cost": round(total_cost),
        "total_value": round(total_value),
        "total_pl": round(total_pl),
        "total_pl_pct": round(total_pl / total_cost * 100, 2) if total_cost else None,
        "allocation": alloc,
        "count": len(positions),
    }


def portfolio_add(uid: str, symbol: str, qty: float, avg_price: float) -> dict:
    sym = _validate_sym(symbol)
    if qty <= 0:
        raise ValueError("Số lượng phải > 0")
    if avg_price <= 0:
        raise ValueError("Giá bình quân phải > 0")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT qty, avg_price FROM portfolio WHERE uid=%s AND symbol=%s", (uid, sym)
        ).fetchone()
        if row:
            old_qty, old_avg = row
            new_qty = old_qty + qty
            new_avg = (old_avg * old_qty + avg_price * qty) / new_qty
            conn.execute(
                "UPDATE portfolio SET qty=%s, avg_price=%s, updated_at=%s WHERE uid=%s AND symbol=%s",
                (new_qty, new_avg, time.time(), uid, sym),
            )
            action = "merged"
        else:
            conn.execute(
                "INSERT INTO portfolio (uid, symbol, qty, avg_price, updated_at) VALUES (%s,%s,%s,%s,%s)",
                (uid, sym, qty, avg_price, time.time()),
            )
            action = "added"
        # ghi transaction
        conn.execute(
            "INSERT INTO transactions (uid,symbol,action,qty,price,executed_at) VALUES (%s,%s,'buy',%s,%s,%s)",
            (uid, sym, qty, avg_price, time.time()),
        )
        conn.commit()
    return {"action": action, "symbol": sym, "qty": qty, "avg_price": avg_price}


def portfolio_update(uid: str, symbol: str, qty: float, avg_price: float) -> dict:
    sym = _validate_sym(symbol)
    if qty <= 0:
        portfolio_remove(uid, sym)
        return {"action": "removed", "symbol": sym}
    with get_conn() as conn:
        n = conn.execute(
            "UPDATE portfolio SET qty=%s, avg_price=%s, updated_at=%s WHERE uid=%s AND symbol=%s",
            (qty, avg_price, time.time(), uid, sym),
        ).rowcount
        if not n:
            raise ValueError(f"Không có {sym} trong danh mục")
        conn.commit()
    return {"action": "updated", "symbol": sym, "qty": qty, "avg_price": avg_price}


def portfolio_remove(uid: str, symbol: str) -> bool:
    sym = _validate_sym(symbol)
    with get_conn() as conn:
        n = conn.execute(
            "DELETE FROM portfolio WHERE uid=%s AND symbol=%s", (uid, sym)
        ).rowcount
        conn.commit()
    return n > 0


def portfolio_sell(uid: str, symbol: str, qty: float, price: float, fee: float = 0, note: str = "") -> dict:
    """Ghi nhận bán — giảm qty hoặc xóa vị thế."""
    sym = _validate_sym(symbol)
    if qty <= 0 or price <= 0:
        raise ValueError("Số lượng và giá phải > 0")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT qty, avg_price FROM portfolio WHERE uid=%s AND symbol=%s", (uid, sym)
        ).fetchone()
        if not row:
            raise ValueError(f"Không có {sym} trong danh mục")
        old_qty, avg_price = row
        if qty > old_qty:
            raise ValueError(f"Số lượng bán ({qty}) vượt quá sở hữu ({old_qty})")
        new_qty = old_qty - qty
        pl = (price - avg_price) * qty - fee
        if new_qty <= 0:
            conn.execute("DELETE FROM portfolio WHERE uid=%s AND symbol=%s", (uid, sym))
        else:
            conn.execute(
                "UPDATE portfolio SET qty=%s, updated_at=%s WHERE uid=%s AND symbol=%s",
                (new_qty, time.time(), uid, sym),
            )
        conn.execute(
            "INSERT INTO transactions (uid,symbol,action,qty,price,fee,note,executed_at) VALUES (%s,%s,'sell',%s,%s,%s,%s,%s)",
            (uid, sym, qty, price, fee, note, time.time()),
        )
        conn.commit()
    return {"symbol": sym, "sold_qty": qty, "price": price, "pl": round(pl, 0), "remaining_qty": new_qty}


# ══════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ══════════════════════════════════════════════════════════════════

def transactions_get(uid: str, symbol: Optional[str] = None, limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        if symbol:
            rows = conn.execute(
                "SELECT id,symbol,action,qty,price,fee,note,executed_at FROM transactions WHERE uid=%s AND symbol=%s ORDER BY executed_at DESC LIMIT %s",
                (uid, symbol.upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,symbol,action,qty,price,fee,note,executed_at FROM transactions WHERE uid=%s ORDER BY executed_at DESC LIMIT %s",
                (uid, limit),
            ).fetchall()
    return [
        {"id": r[0], "symbol": r[1], "action": r[2], "qty": r[3], "price": r[4],
         "fee": r[5], "note": r[6], "executed_at": r[7],
         "total": round(r[3] * r[4])}
        for r in rows
    ]


def transactions_delete(uid: str, tx_id: int) -> bool:
    with get_conn() as conn:
        n = conn.execute(
            "DELETE FROM transactions WHERE id=%s AND uid=%s", (tx_id, uid)
        ).rowcount
        conn.commit()
    return n > 0


# ══════════════════════════════════════════════════════════════════
# ALERT RULES (per-user)
# ══════════════════════════════════════════════════════════════════

VALID_ALERT_TYPES = {"price_above", "price_below", "volume_spike", "score_at_least", "rsi_above", "rsi_below"}


def alert_rules_get(uid: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id,symbol,type,threshold,note,active,created_at FROM alert_rules WHERE uid=%s ORDER BY created_at DESC",
            (uid,),
        ).fetchall()
    return [{"id": r[0], "symbol": r[1], "type": r[2], "threshold": r[3],
              "note": r[4], "active": r[5], "created_at": r[6]} for r in rows]


def alert_rule_add(uid: str, symbol: str, atype: str, threshold: float, note: str = "") -> dict:
    sym = _validate_sym(symbol)
    if atype not in VALID_ALERT_TYPES:
        raise ValueError(f"Loại alert không hợp lệ: {atype}")
    rule_id = secrets.token_hex(8)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO alert_rules (id,uid,symbol,type,threshold,note,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (rule_id, uid, sym, atype, threshold, note, time.time()),
        )
        conn.commit()
    return {"id": rule_id, "symbol": sym, "type": atype, "threshold": threshold, "note": note}


def alert_rule_delete(uid: str, rule_id: str) -> bool:
    with get_conn() as conn:
        n = conn.execute(
            "DELETE FROM alert_rules WHERE id=%s AND uid=%s", (rule_id, uid)
        ).rowcount
        conn.commit()
    return n > 0


def alert_events_get(uid: str, unread_only: bool = False, limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        if unread_only:
            rows = conn.execute(
                "SELECT id,symbol,message,triggered_at,read FROM alert_events WHERE uid=%s AND read=FALSE ORDER BY triggered_at DESC LIMIT %s",
                (uid, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,symbol,message,triggered_at,read FROM alert_events WHERE uid=%s ORDER BY triggered_at DESC LIMIT %s",
                (uid, limit),
            ).fetchall()
    return [{"id": r[0], "symbol": r[1], "message": r[2], "triggered_at": r[3], "read": r[4]} for r in rows]


def alert_events_mark_read(uid: str) -> int:
    with get_conn() as conn:
        n = conn.execute(
            "UPDATE alert_events SET read=TRUE WHERE uid=%s AND read=FALSE", (uid,)
        ).rowcount
        conn.commit()
    return n


def alert_event_add(uid: str, symbol: str, message: str, rule_id: Optional[str] = None) -> None:
    """Dùng bởi scheduler để ghi event."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO alert_events (uid,rule_id,symbol,message,triggered_at) VALUES (%s,%s,%s,%s,%s)",
            (uid, rule_id, symbol, message, time.time()),
        )
        # giữ tối đa 200 events/user
        conn.execute(
            """DELETE FROM alert_events WHERE uid=%s AND id NOT IN (
               SELECT id FROM alert_events WHERE uid=%s ORDER BY triggered_at DESC LIMIT 200)""",
            (uid, uid),
        )
        conn.commit()


def alert_events_clear(uid: str) -> int:
    with get_conn() as conn:
        n = conn.execute("DELETE FROM alert_events WHERE uid=%s", (uid,)).rowcount
        conn.commit()
    return n


# ══════════════════════════════════════════════════════════════════
# USER PREFERENCES
# ══════════════════════════════════════════════════════════════════

def prefs_get(uid: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT theme, default_sym, notify_web, extra FROM user_prefs WHERE uid=%s", (uid,)
        ).fetchone()
    if not row:
        return {"theme": "dark", "default_sym": "VNM", "notify_web": False, "extra": {}}
    return {"theme": row[0], "default_sym": row[1], "notify_web": row[2], "extra": row[3] or {}}


def prefs_update(uid: str, theme: Optional[str] = None, default_sym: Optional[str] = None,
                 notify_web: Optional[bool] = None) -> dict:
    cur = prefs_get(uid)
    new_theme = theme if theme in ("dark", "light") else cur["theme"]
    new_sym = default_sym.upper() if default_sym else cur["default_sym"]
    new_notify = notify_web if notify_web is not None else cur["notify_web"]
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO user_prefs (uid, theme, default_sym, notify_web)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (uid) DO UPDATE
                 SET theme=EXCLUDED.theme, default_sym=EXCLUDED.default_sym,
                     notify_web=EXCLUDED.notify_web""",
            (uid, new_theme, new_sym, new_notify),
        )
        conn.commit()
    return {"theme": new_theme, "default_sym": new_sym, "notify_web": new_notify}


# ══════════════════════════════════════════════════════════════════
# STOCK NOTES
# ══════════════════════════════════════════════════════════════════

def note_get(uid: str, symbol: str) -> str:
    sym = _validate_sym(symbol)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT content FROM stock_notes WHERE uid=%s AND symbol=%s", (uid, sym)
        ).fetchone()
    return row[0] if row else ""


def note_save(uid: str, symbol: str, content: str) -> None:
    sym = _validate_sym(symbol)
    if len(content) > 5000:
        raise ValueError("Ghi chú tối đa 5000 ký tự")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO stock_notes (uid, symbol, content, updated_at)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (uid, symbol) DO UPDATE
                 SET content=EXCLUDED.content, updated_at=EXCLUDED.updated_at""",
            (uid, sym, content, time.time()),
        )
        conn.commit()


# ══════════════════════════════════════════════════════════════════
# BREAK-EVEN CALCULATOR
# ══════════════════════════════════════════════════════════════════

def calc_breakeven(avg_price: float, fee_buy_pct: float = 0.25, fee_sell_pct: float = 0.25,
                   tax_pct: float = 0.1) -> dict:
    """Tính giá hòa vốn sau thuế và phí môi giới (VN market)."""
    buy_fee = avg_price * fee_buy_pct / 100
    total_cost_per_share = avg_price + buy_fee
    sell_overhead_pct = (fee_sell_pct + tax_pct) / 100
    breakeven = total_cost_per_share / (1 - sell_overhead_pct)
    return {
        "avg_price": avg_price,
        "fee_buy": round(buy_fee, 2),
        "breakeven": round(breakeven, 0),
        "breakeven_pct": round((breakeven / avg_price - 1) * 100, 2),
        "fee_buy_pct": fee_buy_pct,
        "fee_sell_pct": fee_sell_pct,
        "tax_pct": tax_pct,
    }


# ══════════════════════════════════════════════════════════════════
# P&L HISTORY  (từ transactions)
# ══════════════════════════════════════════════════════════════════

def pl_summary(uid: str) -> dict:
    """Tổng lãi/lỗ đã chốt từ các lệnh bán."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT symbol, SUM((price - (
                   SELECT avg_price FROM portfolio WHERE uid=t.uid AND symbol=t.symbol
               )) * qty) as pl
               FROM transactions t WHERE uid=%s AND action='sell'
               GROUP BY symbol""",
            (uid,),
        ).fetchall()
    realized = sum((r[1] or 0) for r in rows)
    return {"realized_pl": round(realized, 0), "by_symbol": [
        {"symbol": r[0], "pl": round(r[1] or 0, 0)} for r in rows
    ]}

