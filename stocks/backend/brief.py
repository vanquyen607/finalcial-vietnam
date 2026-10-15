# -*- coding: utf-8 -*-
"""Morning brief / session summary — tong hop tu cache, khong goi API.

Gom: overview, regime, breadth, top screen, su kien som, foreign flow.
Tao on-demand khi user mo — khong can scheduler.
"""
from __future__ import annotations

import time

from backend.store import DATA, _cached


def build_brief() -> dict:
    now = time.time()

    # 1. Overview — fields: label, close, chg_pct
    ov = _cached(DATA / "overview.json")
    indices = []
    if ov and ov.get("data"):
        for row in ov["data"].get("indices", []):
            indices.append({
                "name": row.get("label") or row.get("code", "?"),
                "value": row.get("close"),
                "change_pct": row.get("chg_pct"),
            })

    # 2. Regime — field: regime (bull/bear/neutral), reason
    regime_obj = _cached(DATA / "regime.json")
    regime_raw = regime_obj.get("data", {}) if regime_obj else {}
    regime = {
        "state": regime_raw.get("regime", "unknown"),
        "note": regime_raw.get("reason", ""),
        "vn_above_ma50": regime_raw.get("vn_above_ma50"),
    }

    # 3. Breadth — fields: exchanges.hose.up/down, total.up/down
    br = _cached(DATA / "breadth.json")
    br_raw = br.get("data", {}) if br else {}
    hose = br_raw.get("exchanges", {}).get("hose", {})
    total = br_raw.get("total", {})
    breadth = {
        "hose_up": hose.get("up"),
        "hose_down": hose.get("down"),
        "total_up": total.get("up"),
        "total_down": total.get("down"),
        "fnet_t": total.get("fnet_t"),
    }

    # 4. Screen top — field: results
    scr = _cached(DATA / "screen.json")
    top = []
    if scr:
        rows = sorted(scr.get("results", []),
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

    # 5. Su kien som — doc tu events cache
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
                    if d and d >= today_str:
                        upcoming.append({"symbol": p.stem, "date": d,
                                         "category": it.get("category"),
                                         "title": (it.get("title") or "")[:80]})
            except Exception:
                continue
        upcoming.sort(key=lambda x: x.get("date", ""))
        upcoming = upcoming[:10]

    # 6. Portfolio P&L
    port_obj = _cached(DATA / "portfolio.json")
    port_summary = None
    if port_obj and port_obj.get("positions"):
        try:
            from backend.portfolio import get_summary
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
    vn = next((i for i in indices if "VN" in i["name"].upper()), None)
    if vn and vn["value"] is not None:
        chg = f" ({vn['change_pct']:+.1f}%)" if vn["change_pct"] is not None else ""
        lines.append(f"VN-Index {vn['value']:,.1f}{chg}")
    if regime["state"] != "unknown":
        label = {"bull": "📈 Bull", "bear": "📉 Bear", "neutral": "➡️ Trung tính"}.get(regime["state"], regime["state"])
        lines.append(f"Regime: {label}")
    up, dn = breadth["hose_up"], breadth["hose_down"]
    if up is not None and dn is not None:
        note = "tăng giá chiếm ưu thế" if up > dn else "giảm giá chiếm ưu thế"
        lines.append(f"Breadth HOSE: {up}↑ / {dn}↓ — {note}")
    if top:
        sym_str = ", ".join(f"{t['symbol']}({t['score']})" for t in top[:3])
        lines.append(f"Top màn lọc: {sym_str}")
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
