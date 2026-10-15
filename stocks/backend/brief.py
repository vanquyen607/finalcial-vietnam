# -*- coding: utf-8 -*-
"""Morning brief / session summary — tong hop tu cache, khong goi API.

Gom: overview, regime, breadth, top screen, su kien som, foreign flow.
Tao on-demand khi user mo — khong can scheduler.
"""
from __future__ import annotations

import time

from backend.store import DATA, _cached


def _fmt_pct(v, d=1):
    if v is None:
        return "—"
    return f"{v:+.{d}f}%"


def _fmt_num(v, d=0):
    if v is None:
        return "—"
    return f"{v:,.{d}f}"


def build_brief() -> dict:
    now = time.time()

    # 1. Overview
    ov = _cached(DATA / "overview.json")
    indices = []
    if ov and ov.get("data"):
        for row in ov["data"].get("indices", []):
            indices.append({
                "name": row.get("name", "?"),
                "value": row.get("value"),
                "change_pct": row.get("change_pct"),
            })

    # 2. Regime
    regime_obj = _cached(DATA / "regime.json")
    regime = regime_obj.get("data", {}) if regime_obj else {}

    # 3. Breadth
    br = _cached(DATA / "breadth.json")
    breadth = br.get("data", {}) if br else {}

    # 4. Screen top
    scr = _cached(DATA / "screen.json")
    top = []
    if scr:
        rows = sorted(scr.get("rows", []),
                      key=lambda r: r.get("score", -99), reverse=True)
        for r in rows[:5]:
            top.append({
                "symbol": r.get("symbol"),
                "score": r.get("score"),
                "verdict": r.get("verdict"),
                "close": r.get("close"),
                "r20": r.get("r20"),
                "tone": r.get("tone", "neutral"),
            })

    # 5. Su kien som (7 ngay) — doc tu events cache cac ma trong BASKET
    upcoming = []
    ev_dir = DATA / "events"
    if ev_dir.exists():
        today_str = time.strftime("%Y-%m-%d")
        for p in ev_dir.glob("*.json"):
            try:
                obj = _cached(p)
                if not obj:
                    continue
                for it in obj.get("items", []):
                    d = it.get("date")
                    if not d or not (today_str <= d <= "9999-12-31"):
                        continue
                    # con trong 7 ngay? (uoc luong don gian)
                    upcoming.append({"symbol": p.stem, "date": d,
                                     "category": it.get("category"),
                                     "title": it.get("title")[:80]})
            except Exception:
                continue
        upcoming.sort(key=lambda x: x.get("date", ""))
        upcoming = upcoming[:10]

    # 6. Portfolio P&L
    port_obj = _cached(DATA / "portfolio.json")
    port_summary = None
    if port_obj and port_obj.get("positions"):
        from backend.portfolio import get_summary
        try:
            s = get_summary()
            port_summary = {"count": s["count"], "total_value": s["total_value"],
                            "total_pl": s["total_pl"], "total_pl_pct": s["total_pl_pct"]}
        except Exception:
            pass

    # 7. Alerts chua doc
    alert_count = 0
    alert_dir = DATA / "alerts"
    if alert_dir.exists():
        for p in list(alert_dir.glob("*.json"))[-20:]:
            try:
                a = _cached(p)
                if a and not a.get("read"):
                    alert_count += 1
            except Exception:
                pass

    # Tao text summary
    lines = []
    # market
    vn = next((i for i in indices if "VN" in i["name"].upper()), None)
    if vn:
        lines.append(f"VN-Index {vn['value']:,.1f} ({vn['change_pct']:+.1f}%)")
    # regime
    if regime:
        st = regime.get("state", "unknown")
        label = {"bull": "📈 Bull", "bear": "📉 Bear", "neutral": "➡️ Trung tính"}.get(st, st)
        lines.append(f"Regime: {label}")
    # breadth
    if breadth:
        up = breadth.get("hose_up", "?")
        dn = breadth.get("hose_down", "?")
        breadth_note = "tăng giá chiếm ưu thế" if isinstance(up, (int, float)) and isinstance(dn, (int, float)) and up > dn else "giảm giá chiếm ưu thế"
        lines.append(f"Breath: {up}↑ / {dn}↓ — {breadth_note}")
    # top
    if top:
        sym_str = ", ".join(f"{t['symbol']}({t['score']})" for t in top[:3])
        lines.append(f"Top màn lọc: {sym_str}")
    # alerts
    if alert_count:
        lines.append(f"🔔 {alert_count} alert chưa đọc")

    return {
        "status": "ready",
        "generated_at": now,
        "lines": lines,
        "indices": indices,
        "regime": regime,
        "breadth": breadth,
        "top_screen": top,
        "upcoming_events": upcoming,
        "portfolio": port_summary,
        "alert_count": alert_count,
    }
