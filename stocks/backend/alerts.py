# -*- coding: utf-8 -*-
"""Alert chu dong — server scheduler kiem tra dieu kien, luu su kien per-user.

Loai alert:
  price_above / price_below  — gia cham muc
  volume_spike               — khoi luong bat thuong (> n x TB20)
  score_at_least             — diem dat nguong
  rsi_above / rsi_below      — RSI qua mua / qua ban

Scheduler chay moi 5 phut trong gio giao dich (is_session).
Rules luu trong bang alert_rules (per-user, Postgres); events trong
alert_events (per-user, toi da 200/user, cooldown 30 phut/rule).
File legacy (alert_rules.json, alerts/*.json) duoc migrate cho admin lan
dau startup roi doi ten thanh .bak.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

from backend import user_data
from backend.db import get_conn
from backend.session import is_session
from backend.store import DATA

_VN_NAME = "vnstock.alerts"

CHECK_INTERVAL = 300   # 5 phut
COOLDOWN = 1800        # khong trigger lai trong 30 phut cung 1 rule

RULES_PATH = DATA / "alert_rules.json"
ALERT_DIR = DATA / "alerts"

_scheduler_started = False


# ---------------- migrate legacy (file + cache table -> bang per-user, admin) ----------------
CACHE_RULES_KEY = "data/alert_rules.json"
CACHE_ALERTS_PREFIX = "data/alerts/"


def _admin_exists() -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE username='admin'").fetchone()
    return row is not None


def _cache_delete(key: str) -> None:
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM cache WHERE key=%s", (key,))
            conn.commit()
    except Exception:
        pass


def _legacy_alert_objs() -> list[tuple[str, dict]]:
    """Legacy alerts trong cache table (Render khong con file JSON)."""
    out: list[tuple[str, dict]] = []
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT key, value FROM cache WHERE key LIKE %s",
                (CACHE_ALERTS_PREFIX + "%",),
            ).fetchall()
        for k, v in rows:
            try:
                out.append((k, v if isinstance(v, dict) else json.loads(v)))
            except Exception:
                continue
    except Exception:
        pass
    return out


def _migrate_rules() -> None:
    """alert_rules.json (file + cache table) -> bang alert_rules (uid=admin)."""
    src = RULES_PATH
    tmp = DATA / "alert_rules.json.migrating"
    dst = DATA / "alert_rules.json.bak"
    if src.exists() and not tmp.exists() and not dst.exists():
        src.rename(tmp)
    obj = None
    if tmp.exists():
        try:
            obj = json.loads(tmp.read_text(encoding="utf-8"))
        except Exception:
            obj = None
    if obj is None:
        from backend.store import _read_raw
        obj = _read_raw(RULES_PATH)   # DB cache truoc, file fallback
    if obj:
        rules = obj.get("rules", []) if isinstance(obj, dict) else []
        existing = {(r["symbol"], r["type"], round(r["threshold"], 6))
                    for r in user_data.alert_rules_get("admin")}
        for r in rules:
            try:
                sym = str(r.get("symbol", "")).upper()
                rtype = str(r.get("type", ""))
                th = round(float(r.get("threshold", 0)), 6)
            except (TypeError, ValueError):
                continue
            key = (sym, rtype, th)
            if not sym or rtype not in user_data.VALID_ALERT_TYPES or key in existing:
                continue
            try:
                user_data.alert_rule_add("admin", sym, rtype, float(r.get("threshold", 0)),
                                         str(r.get("note", ""))[:120])
                existing.add(key)
            except ValueError:
                continue  # legacy rule khong hop le -> bo qua vinh vien
            # Exception khac (DB): propagate -> khong cleanup -> lan sau chay lai (dedupe)
        logging.getLogger(_VN_NAME).info("Migrated legacy alert rules -> Postgres (admin)")
    # cleanup ca hai luong (chi chay khi insert khong raise)
    if tmp.exists():
        tmp.rename(dst)
    elif src.exists() and not dst.exists():
        src.rename(dst)
    _cache_delete(CACHE_RULES_KEY)


def _migrate_alert_dir() -> None:
    """Legacy alerts (files + cache table) -> bang alert_events (uid=admin)."""
    entries: list[tuple[str, dict]] = []   # (locator, obj) — locator = file path hay cache key
    if ALERT_DIR.exists():
        for p in sorted(ALERT_DIR.glob("*.json")):
            try:
                entries.append((str(p), json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
    entries.extend(_legacy_alert_objs())
    if not entries:
        return
    known = {(e["symbol"], e["message"], round(e["triggered_at"]))
             for e in user_data.alert_events_get("admin", limit=200)}
    done_files: list[Path] = []
    done_keys: list[str] = []
    for locator, a in entries:
        try:
            key = (a.get("symbol", ""), a.get("message", ""), round(float(a.get("ts", 0))))
            if key not in known:
                try:
                    ts = float(a.get("ts") or 0) or None
                except (TypeError, ValueError):
                    ts = None
                user_data.alert_event_add(
                    "admin", a.get("symbol", ""), a.get("message", ""),
                    a.get("rule_id"), a.get("type", ""), bool(a.get("read", False)),
                    ts,
                )
                known.add(key)
        except Exception:
            continue  # that bai -> giu lai (file/cache), lan sau chay lai (dedupe)
        if locator.startswith(CACHE_ALERTS_PREFIX):
            done_keys.append(locator)
        else:
            done_files.append(Path(locator))
    for p in done_files:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass
    for k in done_keys:
        _cache_delete(k)
    try:
        if ALERT_DIR.exists() and not any(ALERT_DIR.glob("*.json")):
            dst = DATA / "alerts.bak"
            if not dst.exists():
                ALERT_DIR.rename(dst)
    except Exception:
        pass
    logging.getLogger(_VN_NAME).info("Migrated legacy alert events -> Postgres (admin)")


def migrate_legacy() -> None:
    """Idempotent. Bo qua neu admin chua ton tai (bootstrap chua chay)."""
    try:
        if not _admin_exists():
            return
        _migrate_rules()
        _migrate_alert_dir()
    except Exception as e:
        logging.getLogger(_VN_NAME).warning(f"Legacy alert migration error: {e}")


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
    """Kiem tra toan bo rule trong DB (moi user). Tra ve so alert moi."""
    if not is_session():
        return 0
    try:
        rules = user_data.alert_rules_active_all()
        if not rules:
            return 0
        recent = user_data.alert_rules_recent_rule_ids(time.time() - COOLDOWN)
    except Exception as e:
        logging.getLogger(_VN_NAME).warning(f"check_once load rules error: {e}")
        return 0
    fired = 0
    for rule in rules:
        if rule["id"] in recent:
            continue
        try:
            q = _get_quote_data(rule["symbol"])
            if not q:
                continue
            msg = _eval_rule(rule, q)
            if msg:
                user_data.alert_event_add(rule["uid"], rule["symbol"], msg,
                                          rule["id"], rule.get("type", ""))
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
