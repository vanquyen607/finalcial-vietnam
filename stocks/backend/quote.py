"""Bang gia gan realtime mien phi tu SSI iBoard (khong can API key).

Nguon: POST https://iboard-query.ssi.com.vn/stock/multiple
       form: stocks=HPG&stocks=SSI&boardId=MAIN
- Tra ve nhieu ma trong 1 request (~400ms/40 ma), du truong: khop, tham chieu,
  tran/san, bid/ask 3 muc, KL + gia tri khop, room ngoai, phien.
- KHONG phai API chinh thuc: co the doi field / chan IP bat cu luc nao.
  Vi vay: cache ngan trong RAM, loi thi tra gia cu (stale=1), khong ghi Neon.

Cache: trong phien 5s/ma, ngoai phien 300s. Khong ghi Neon (tranh write 5s/lan).
"""
import threading
import time

import requests

from backend import market

_URL = "https://iboard-query.ssi.com.vn/stock/multiple"
_HDRS = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://iboard.ssi.com.vn",
    "Referer": "https://iboard.ssi.com.vn/",
    "Content-Type": "application/x-www-form-urlencoded",
}
_TTL_IN = 5.0
_TTL_OUT = 300.0
_MAX_SYMS = 60
_TIMEOUT = 6

_lock = threading.Lock()
_rows: dict = {}      # sym -> dict da chuan hoa
_ts: dict = {}        # sym -> thoi diem lay (time.time())
_state = {"err": "", "err_at": 0.0}


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _clean_syms(raw) -> list:
    out, seen = [], set()
    for s in str(raw or "").split(","):
        s = s.strip().upper()
        if not s or s in seen:
            continue
        if not s.isalnum() or not (2 <= len(s) <= 6):
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= _MAX_SYMS:
            break
    return out


def _norm(d: dict) -> dict:
    sym = str(d.get("stockSymbol") or "").upper()
    ref = _num(d.get("refPrice"))
    price = _num(d.get("matchedPrice")) or _num(d.get("expectedMatchedPrice"))
    openp = _num(d.get("openPrice")) or _num(d.get("priorClosePrice"))
    chg = round(price - ref, 2) if price > 0 and ref > 0 else None
    pct = round(chg / ref * 100, 2) if chg is not None and ref else None
    upd = _num(d.get("expectedLastUpdate"))
    return {
        "symbol": sym,
        "price": int(price) if price > 0 else None,
        "ref": int(ref) if ref > 0 else None,
        "chg": chg,
        "chg_pct": pct,
        "open": int(openp) if openp > 0 else None,
        "high": int(_num(d.get("highest"))) or None,
        "low": int(_num(d.get("lowest"))) or None,
        "avg": round(_num(d.get("avgPrice")), 1) or None,
        "vol": int(_num(d.get("nmTotalTradedQty"))) or None,
        "value": int(_num(d.get("nmTotalTradedValue"))) or None,
        "bid": int(_num(d.get("best1Bid"))) or None,
        "bid_vol": int(_num(d.get("best1BidVol"))) or None,
        "ask": int(_num(d.get("best1Offer"))) or None,
        "ask_vol": int(_num(d.get("best1OfferVol"))) or None,
        "room": int(_num(d.get("remainForeignQtty"))) or None,
        "ceil": int(_num(d.get("ceiling"))) or None,
        "floor": int(_num(d.get("floor"))) or None,
        "session": str(d.get("session") or ""),
        "live": price > 0,
        "updated_at": int(upd) if upd > 0 else None,
        "stale": False,
    }


def _fetch(syms: list) -> list:
    body = "&".join("stocks=" + s for s in syms) + "&boardId=MAIN"
    r = requests.post(_URL, data=body, headers=_HDRS, timeout=_TIMEOUT)
    r.raise_for_status()
    js = r.json()
    data = js.get("data") or []
    out = []
    for d in data:
        if isinstance(d, dict):
            row = _norm(d)
            if row["symbol"]:
                out.append(row)
    return out


def get(symbols) -> dict:
    """Tra ve bang gia cho danh sach ma (toi da 60)."""
    syms = _clean_syms(symbols)
    now = time.time()
    in_sess = market.is_session()
    ttl = _TTL_IN if in_sess else _TTL_OUT

    with _lock:
        need = [s for s in syms if s not in _rows or now - _ts.get(s, 0) > ttl]
        err = ""
        if need:
            try:
                for i in range(0, len(need), _MAX_SYMS):
                    for row in _fetch(need[i:i + _MAX_SYMS]):
                        _rows[row["symbol"]] = row
                        _ts[row["symbol"]] = now
                miss = [s for s in need if s not in _rows]
                if len(miss) == len(need) and miss:
                    err = "SSI khong tra du lieu"
            except Exception as e:  # noqa: BLE001 - nguon ngoai, khong duoc lam sap API
                err = type(e).__name__ + ": " + str(e)[:120]
            if err:
                _state["err"] = err
                _state["err_at"] = now
            else:
                _state["err"] = ""
                _state["err_at"] = 0.0

        data = []
        for s in syms:
            row = _rows.get(s)
            if row:
                row = dict(row)
                row["stale"] = (now - _ts.get(s, 0)) > max(ttl, 30)
                row["age"] = round(now - _ts.get(s, 0), 1)
                data.append(row)
            else:
                data.append({"symbol": s, "price": None, "stale": True,
                             "live": False, "age": None})
        if any(s not in _rows for s in syms):
            err = _state["err"] if now - _state["err_at"] < 120 else "SSI khong tra du lieu"
        else:
            err = ""

    return {
        "status": "ok",
        "in_session": in_sess,
        "state": market.session_state(),
        "delay_s": int(_TTL_IN) if in_sess else 0,
        "source": "ssi-iboard",
        "note": "Gia tu bang gia SSI iBoard - chi de tham khao, khong phai API chinh thuc.",
        "error": err or None,
        "ts": int(now * 1000),
        "data": data,
    }
