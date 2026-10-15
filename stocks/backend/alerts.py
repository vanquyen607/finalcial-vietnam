# -*- coding: utf-8 -*-
"""Alert chu dong — server scheduler kiem tra dieu kien, luu su kien.

Loai alert:
  price_above / price_below  — gia cham muc
  volume_spipe               — khoi luong bat thuong (> n x TB20)
  score_at_least             — diem dat nguong
  rsi_above / rsi_below      — RSI qua mua / qua ban

Scheduler chay moi 5 phut trong gio giao dich (is_session).
Rules luu persistent; alerts luu 30 ngay.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.store import DATA, _cached, _save
from backend.session import is_session

_VN = ZoneInfo("Asia/Ho_Chi_Minh")

ALERT_DIR = DATA / "alerts"
RULES_PATH = DATA / "alert_rules.json"
ALERT_DIR.mkdir(parents=True, exist_ok=True)

CHECK_INTERVAL = 300  # 5 phut
ALERT_TTL = 30 * 24 * 3600  # giu alert 30 ngay

_rules_lock = threading.Lock()
_alerts_lock = threading.Lock()
_scheduler_started = False


# ---------------- rules ----------------
def _load_rules() -> list[dict]:
    obj = _cached(RULES_PATH)
    if not obj:
        return []
    return obj.get("rules", [])


def _save_rules(rules: list[dict]) -> None:
    _save(RULES_PATH, {"updated_at": time.time(), "rules": rules})


def list_rules() -> list[dict]:
    with _rules_lock:
        return _load_rules()


def add_rule(rule: dict) -> dict:
    """Them rule. rule: {symbol, type, threshold, note?}"""
    sym = str(rule.get("symbol", "")).strip().upper()
    rtype = str(rule.get("type", "")).strip()
    valid_types = {"price_above", "price_below", "volume_spike",
                   "score_at_least", "rsi_above", "rsi_below"}
    if not sym.isalpha() or not 2 <= len(sym) <= 6:
        raise ValueError("Mã không hợp lệ")
    if rtype not in valid_types:
        raise ValueError(f"Loại alert không hợp lệ: {rtype}. Chọn: {valid_types}")
    try:
        threshold = float(rule.get("threshold"))
    except (TypeError, ValueError):
        raise ValueError("Ngưỡng phải là số")
    if rtype == "volume_spike" and threshold <= 0:
        raise ValueError("volume_spike cần n > 0 (ví dụ 2 = 2× TB20)")

    with _rules_lock:
        rules = _load_rules()
        # trung rule cung symbol+type+threshold -> bo qua
        for r in rules:
            if (r["symbol"] == sym and r["type"] == rtype
                    and abs(r["threshold"] - threshold) < 1e-9):
                return r
        new_rule = {
            "id": f"{sym}_{rtype}_{int(threshold * 100)}",
            "symbol": sym,
            "type": rtype,
            "threshold": threshold,
            "note": str(rule.get("note", ""))[:120],
            "created_at": time.time(),
            "active": True,
            "last_triggered": None,
        }
        rules.append(new_rule)
        _save_rules(rules)
        return new_rule


def delete_rule(rule_id: str) -> bool:
    with _rules_lock:
        rules = _load_rules()
        before = len(rules)
        rules = [r for r in rules if r.get("id") != rule_id]
        if len(rules) == before:
            return False
        _save_rules(rules)
        return True


# ---------------- alerts ----------------
def _load_alerts() -> list[dict]:
    alerts = []
    for p in sorted(ALERT_DIR.glob("*.json"), reverse=True)[:200]:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            if time.time() - obj.get("ts", 0) < ALERT_TTL:
                alerts.append(obj)
        except Exception:
            continue
    alerts.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return alerts


def _push_alert(alert: dict) -> None:
    ts = int(time.time() * 1000)
    _save(ALERT_DIR / f"{ts}_{alert['symbol']}.json", alert)


def list_alerts(limit: int = 50) -> list[dict]:
    with _alerts_lock:
        return _load_alerts()[:limit]


def clear_alerts() -> int:
    with _alerts_lock:
        n = 0
        for p in ALERT_DIR.glob("*.json"):
            try:
                p.unlink()
                n += 1
            except Exception:
                pass
    return n


# ---------------- check logic ----------------
def _get_quote_data(sym: str) -> dict | None:
    """Lay close + volume 20 phien + rsi + score tu cache (khong goi API)."""
    from backend.store import _cached as _c
    obj = _c(DATA / "sym" / f"{sym}.json")
    if not obj or not obj.get("data"):
        return None
    data = obj["data"]
    close = data.get("close")
    if close is None:
        return None
    # lay ohlcv
    ohlcv = data.get("ohlcv") or []
    vol20 = [b["volume"] for b in ohlcv[-20:]] if ohlcv else []
    avg_vol = sum(vol20) / len(vol20) if vol20 else None
    last_vol = ohlcv[-1]["volume"] if ohlcv else None
    # rsi
    rsi = data.get("rsi")
    # score tu screen cache
    scr = _c(DATA / "screen.json")
    score = None
    if scr:
        for row in scr.get("rows", []):
            if row.get("symbol") == sym:
                score = row.get("score")
                break
    return {"close": close, "avg_vol": avg_vol, "last_vol": last_vol,
            "rsi": rsi, "score": score}


def _eval_rule(rule: dict, q: dict) -> str | None:
    """Tra ve message neu match, None neu khong."""
    sym = rule["symbol"]
    rtype = rule["type"]
    th = rule["threshold"]
    if rtype == "price_above" and q["close"] is not None and q["close"] >= th:
        return f"{sym} chạm {q['close']:,.1f} ≥ {th:,.1f} (alert giá tăng)"
    if rtype == "price_below" and q["close"] is not None and q["close"] <= th:
        return f"{sym} chạm {q['close']:,.1f} ≤ {th:,.1f} (alert giá giảm)"
    if (rtype == "volume_spike" and q["last_vol"] and q["avg_vol"]
            and q["avg_vol"] > 0 and q["last_vol"] / q["avg_vol"] >= th):
        ratio = q["last_vol"] / q["avg_vol"]
        return f"{sym} KL {ratio:.1f}× TB20 (≥{th:.1f}×) — bất thường"
    if rtype == "score_at_least" and q["score"] is not None and q["score"] >= th:
        return f"{sym} điểm {q['score']} ≥ {th:.0f} — đạt ngưỡng mua"
    if rtype == "rsi_above" and q["rsi"] is not None and q["rsi"] >= th:
        return f"{sym} RSI {q['rsi']:.0f} ≥ {th:.0f} — quá mua"
    if rtype == "rsi_below" and q["rsi"] is not None and q["rsi"] <= th:
        return f"{sym} RSI {q['rsi']:.0f} ≤ {th:.0f} — quá bán"
    return None


def check_once() -> int:
    """Kiem tra tat ca rules. Tra ve so alert moi."""
    if not is_session():
        return 0
    rules = list_rules()
    if not rules:
        return 0
    fired = 0
    now = time.time()
    for rule in rules:
        if not rule.get("active"):
            continue
        # khong trigger lai trong 30 phut cung 1 rule
        if rule.get("last_triggered") and now - rule["last_triggered"] < 1800:
            continue
        try:
            q = _get_quote_data(rule["symbol"])
            if not q:
                continue
            msg = _eval_rule(rule, q)
            if msg:
                alert = {
                    "symbol": rule["symbol"],
                    "rule_id": rule.get("id"),
                    "type": rule["type"],
                    "threshold": rule["threshold"],
                    "message": msg,
                    "close": q.get("close"),
                    "ts": now,
                    "read": False,
                }
                with _alerts_lock:
                    _push_alert(alert)
                # cap nhat last_triggered
                with _rules_lock:
                    rules2 = _load_rules()
                    for r in rules2:
                        if r.get("id") == rule.get("id"):
                            r["last_triggered"] = now
                    _save_rules(rules2)
                fired += 1
        except Exception:
            continue
    return fired


# ---------------- scheduler ----------------
def _scheduler_loop():
    while True:
        try:
            if is_session():
                check_once()
        except Exception:
            pass
        time.sleep(CHECK_INTERVAL)


def start_scheduler():
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="alert-scheduler")
    t.start()
