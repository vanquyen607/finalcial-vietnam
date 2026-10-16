# -*- coding: utf-8 -*-
"""Market regime gate — bull/bear/neutral tu VN-Index vs MA50 + breadth.

Backtest cho thay: 2026 (bear) win rate chi 26%, excess ca ky = 0.
Rule don gian: chi tin hieu MUA khi VN-Index > MA50 HOAC breadth up > down.
Cache 5 phut (ngan hon overview de verdict bot tre) — khong go API moi request.
"""
import threading
import time

from backend.store import DATA, _cached

REGIME_TTL = 5 * 60        # 5 phut
_regime_lock = threading.Lock()
_regime_state = {"status": "init", "data": None}


def _check_regime() -> dict:
    """Doc overview + breadth da cache, xet bull/bear/neutral."""
    from backend.overview import overview
    from backend.breadth import breadth

    ov = overview()
    br = breadth()
    if br.get("status") != "ready":
        # breadth dang fetch/cu -> dung ban cache de tinh regime khop voi phan hien thi
        cached = _cached(DATA / "breadth.json")
        if cached:
            inner = cached.get("data") or cached
            if inner.get("exchanges"):
                br = {"status": "ready", **inner}

    # --- VN-Index vs MA50 ---
    vn_above_ma50 = None
    vn_label = ""
    if ov.get("status") == "ready":
        for idx in ov.get("indices", []):
            if idx.get("code") == "VNINDEX":
                close = idx.get("close")
                ma50 = idx.get("ma50")
                if close is not None and ma50 is not None:
                    vn_above_ma50 = close > ma50
                    vn_label = f"VN-Index {close:.1f} vs MA50 {ma50:.1f}"
                break

    # --- breadth up > down (HOSE) ---
    breadth_bull = None
    breadth_label = ""
    if br.get("status") == "ready":
        hose = br.get("exchanges", {}).get("hose", {})
        up = hose.get("up", 0)
        down = hose.get("down", 0)
        if up + down > 50:       # du lieu co y nghia (khong phai board reset)
            breadth_bull = up > down
            breadth_label = f"HOSE {up} tăng vs {down} giảm"

    # --- ket luan ---
    signals = [s for s in (vn_above_ma50, breadth_bull) if s is not None]
    if not signals:
        regime, reason = "neutral", "Không đủ dữ liệu thị trường"
    elif any(signals):
        # it nhat 1 tin hieu bull -> bull (rule: VN-Index > MA50 HOAC breadth up > down)
        parts = []
        if vn_above_ma50 is True:
            parts.append(vn_label)
        if breadth_bull is True:
            parts.append(breadth_label)
        regime = "bull"
        reason = " · ".join(parts) if parts else "Thị trường thuận"
    else:
        # ca 2 tin hieu bear -> bear
        parts = []
        if vn_above_ma50 is False:
            parts.append(vn_label)
        if breadth_bull is False:
            parts.append(breadth_label)
        regime = "bear"
        reason = " · ".join(parts) if parts else "Thị trường bất lợi"

    return {
        "regime": regime,
        "reason": reason,
        "vn_above_ma50": vn_above_ma50,
        "breadth_bull": breadth_bull,
        "vn_label": vn_label,
        "breadth_label": breadth_label,
        "checked_at": time.time(),
    }


def get_regime(refresh: bool = False) -> dict:
    """Tra ve {status, regime, reason, ...} — cache 30p."""
    global _regime_state

    if not refresh:
        with _regime_lock:
            st = dict(_regime_state)
        if st["status"] == "ready" and st["data"]:
            age = time.time() - st["data"].get("checked_at", 0)
            if age < REGIME_TTL:
                return {"status": "ready", **st["data"]}

    # doc file cache (neu server restart)
    if not refresh:
        cached = _cached(DATA / "regime.json")
        if cached:
            inner = cached.get("data") or cached
            age = time.time() - inner.get("checked_at", 0)
            if age < REGIME_TTL:
                with _regime_lock:
                    _regime_state = {"status": "ready", "data": inner}
                return {"status": "ready", **inner}

    try:
        data = _check_regime()
        from backend.store import _save
        _save(DATA / "regime.json", {"fetched_at": time.time(), "data": data})
        with _regime_lock:
            _regime_state = {"status": "ready", "data": data}
        return {"status": "ready", **data}
    except Exception as e:
        with _regime_lock:
            if _regime_state["status"] == "ready" and _regime_state["data"]:
                return {"status": "ready", **_regime_state["data"]}   # giu regime cu
        return {"status": "error", "message": str(e), "regime": "neutral",
                "reason": "Không xác định được regime — mặc định neutral"}


def apply_gate(data: dict, regime_info: dict | None = None) -> dict:
    """Ap regime gate vao ket qua compute() — adjust verdict neu bear market.

    - bear + score >= 10 (MUA) -> xuong THEO DÕI + canh bao
    - bear + score >= 6  (THEO DÕI) -> giu nguyen + canh bao
    - bull / neutral -> khong doi
    """
    if regime_info is None:
        regime_info = get_regime()
    regime = regime_info.get("regime", "neutral")

    data = dict(data)   # khong mutate original
    data["regime"] = regime
    data["regime_reason"] = regime_info.get("reason", "")

    if regime != "bear":
        return data

    score = data.get("score", 0)
    verdict = data.get("verdict", "")
    tone = data.get("tone", "neutral")

    if score >= 10:
        # ha xuong THEO DÕI — khong phai MUA trong bear market
        data["score_raw"] = score
        data["score"] = min(score, 9)
        data["verdict"] = "THEO DÕI (bear market)"
        data["tone"] = "watch"
        data["regime_gate"] = True
        data["regime_note"] = (
            f"⚠️ Thị trường bất lợi ({regime_info.get('reason', '')}) — "
            "hạ khuyến nghị từ MUA xuống THEO DÕI. Chỉ xem, chưa vào lệnh."
        )
    elif score >= 6:
        data["regime_gate"] = True
        data["regime_note"] = (
            f"⚠️ Thị trường bất lợi ({regime_info.get('reason', '')}) — "
            "cân nhắc chờ thị trường tốt hơn trước khi vào lệnh."
        )
    # score < 6: khong doi, da la TRUNG TINH/TRÁNH roi

    return data
