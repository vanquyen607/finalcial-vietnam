"""Man loc co phieu — tach tu market.py de giam kich thuoc."""
import json
import threading
import time

from backend.calc import verdict_of
from backend.market import (BASKET, DATA, ROOT, _cached, _save,
                            get_symbol, is_session)

_screen_lock = threading.Lock()
screen_state = {"status": "idle", "done": 0, "total": 0, "current": "", "results": [],
                "generated_at": None, "message": "", "auto": False, "_abort": False,
                "_kick": False, "worker_alive": False,
                "cycles": 0, "next_at": 0.0}

# chong spam: 1 lan quet tay / MANUAL_COOLDOWN giay (ton quota vnstock)
MANUAL_COOLDOWN = 90
_last_manual = 0.0


def _prefetch_fund(sym: str) -> None:
    """Tai truoc chi so co ban o nen khi quet man — user click vao la co san."""
    try:
        from backend import fund
        fund.get_fundamentals(sym)
    except Exception:
        pass


def _verdict_of(score: int) -> tuple[str, str]:
    return verdict_of(score)


def _gate_rows(rows: list[dict]) -> list[dict]:
    """Gate regime DUNG MOT LAN, tinh tu diem GOC.

    Row cu co the da bi gate (diem bi ha + co score_raw) -> khoi phuc diem goc
    truoc khi gate lai, tranh ha 2 lan lam lech ghi chu voi o chi tiet.
    """
    try:
        from backend.regime import apply_gate, get_regime
        rg = get_regime()
    except Exception:
        apply_gate, rg = None, None
    out = []
    for r in rows:
        r = dict(r)
        raw = r.pop("score_raw", None)
        if raw is None:
            raw = r.get("score", 0)
        r.pop("regime_gate", None)
        r.pop("regime_note", None)
        r["score"] = raw
        r["verdict"], r["tone"] = verdict_of(raw)
        if apply_gate is not None and raw >= 6:
            r = apply_gate(r, rg)
        out.append(r)
    return out


def _seed_screen():
    p = DATA / "screen.json"
    if p.exists():
        return
    src = ROOT / "reports" / "screen_2026-10-08.json"
    if src.exists():
        try:
            rows = json.loads(src.read_text(encoding="utf-8"))
            for r in rows:
                if "verdict" not in r:
                    r["verdict"], r["tone"] = _verdict_of(r.get("score", 0))
            rows.sort(key=lambda x: -x.get("score", 0))
            p.write_text(json.dumps({"results": rows, "generated_at": src.stat().st_mtime,
                                     "source": "seed"}, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


def screen() -> dict:
    path = DATA / "screen.json"
    with _screen_lock:
        st = dict(screen_state)
    if path.exists() and st["status"] != "running":
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            results = _gate_rows(obj["results"])
            results.sort(key=lambda x: -x.get("score", 0))
            st.update({"status": "ready", "results": results,
                       "generated_at": obj.get("generated_at"),
                       "source": obj.get("source")})
        except Exception:
            pass
    if st["status"] == "running":
        st["running"] = True
    for k in ("_abort", "_kick"):
        st.pop(k, None)
    if st.get("next_at"):
        st["next_in"] = max(0, int(st["next_at"] - time.time()))
    else:
        st["next_in"] = 0
    return st


def start_screen(auto: bool = False) -> dict:
    global _last_manual
    with _screen_lock:
        if auto:
            screen_state["auto"] = True
        else:
            now = time.time()
            wait = MANUAL_COOLDOWN - (now - _last_manual)
            if wait > 0 and screen_state["status"] != "running":
                return {"status": "cooldown", "retry_in": int(wait) + 1,
                        "message": f"Vừa chạy xong — đợi {int(wait) + 1}s để tránh hết quota."}
            _last_manual = now
        if screen_state.get("worker_alive"):
            # worker dang chay: auto -> khong canh gi; quet tay -> day chong ngu
            if not auto and screen_state["status"] != "running":
                screen_state["_kick"] = True
            return {"status": screen_state["status"], "auto": screen_state["auto"]}
        screen_state.update({"status": "running", "done": 0, "total": len(BASKET),
                             "current": "", "_abort": False, "_kick": False,
                             "worker_alive": True, "message": ""})
    threading.Thread(target=_screen_worker, daemon=True).start()
    return {"status": "running", "auto": auto}


def stop_screen() -> dict:
    with _screen_lock:
        screen_state["auto"] = False
        screen_state["_abort"] = True
        screen_state["next_at"] = 0.0
    return {"status": screen_state["status"], "auto": False}


def _screen_file_rows() -> list[dict]:
    try:
        obj = json.loads((DATA / "screen.json").read_text(encoding="utf-8"))
        return _gate_rows(obj.get("results", []))
    except Exception:
        return []


def _run_pass() -> list[dict] | None:
    with _screen_lock:
        screen_state["_kick"] = False
        base = screen_state.get("results") or _screen_file_rows()
        merged = {r["symbol"]: dict(r) for r in base}
        screen_state.update({"status": "running", "done": 0, "total": len(BASKET),
                             "results": sorted(merged.values(), key=lambda x: -x.get("score", 0))})
    for i, sym in enumerate(BASKET, 1):
        with _screen_lock:
            if screen_state["_abort"]:
                return None
            screen_state.update({"done": i - 1, "current": sym})
        res = get_symbol(sym, refresh=True)
        if res["status"] == "ready":
            d = res["data"]
            merged[sym] = {k: d.get(k) for k in (
                "symbol", "close", "date", "rsi", "ma20", "ma50", "ma200", "vol_ratio",
                "r5", "r20", "sup", "res", "hi52", "lo52", "score", "verdict", "tone",
                "stop", "t1", "t2", "risk_pct", "rr")}
            threading.Thread(target=_prefetch_fund, args=(sym,), daemon=True).start()
        with _screen_lock:
            screen_state.update({"done": i,
                                 "results": sorted(merged.values(),
                                                   key=lambda x: -x.get("score", 0))})
    return sorted(merged.values(), key=lambda x: -x.get("score", 0))


def _wait_between_passes() -> bool:
    """Ngu giua 2 vong quet. Tra ve False neu phai dung."""
    while True:
        with _screen_lock:
            if not screen_state["auto"] or screen_state["_kick"]:
                return screen_state["auto"]
        if is_session():
            for k in range(60, 0, -1):
                time.sleep(1)
                with _screen_lock:
                    screen_state["next_at"] = time.time() + k
                    if not screen_state["auto"] or screen_state["_kick"]:
                        return screen_state["auto"]
            return True
        # ngoai gio: cho den khi vao gio
        time.sleep(15)
        with _screen_lock:
            screen_state["next_at"] = 0.0


def _screen_worker():
    try:
        while True:
            rows = _run_pass()
            if rows is None:
                break
            rows.sort(key=lambda x: -x.get("score", 0))
            obj = {"results": rows, "generated_at": time.time(), "source": "live"}
            _save(DATA / "screen.json", obj)
            with _screen_lock:
                screen_state.update({"status": "ready", "results": rows,
                                     "generated_at": obj["generated_at"], "current": "",
                                     "cycles": screen_state["cycles"] + 1})
                if not screen_state["auto"]:
                    break
            if not _wait_between_passes():
                break
    except Exception as e:          # khoong de worker chet im — bao UI ro loi
        with _screen_lock:
            screen_state["message"] = f"Lỗi quét: {e}"
    finally:
        with _screen_lock:
            if screen_state["status"] == "running":
                screen_state["status"] = "ready"
            screen_state.update({"worker_alive": False, "current": "", "next_at": 0.0,
                                 "_kick": False})


# ---------------------------------------------------------------- bootstrap
_seed_screen()
