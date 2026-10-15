"""Man loc co phieu — tach tu market.py de giam kich thuoc."""
import json
import threading
import time

from backend.market import (BASKET, DATA, ROOT, _cached, _save,
                            get_symbol, is_session)

_screen_lock = threading.Lock()
screen_state = {"status": "idle", "done": 0, "total": 0, "current": "", "results": [],
                "generated_at": None, "message": "", "auto": False, "_abort": False,
                "_kick": False, "worker_alive": False,
                "cycles": 0, "next_at": 0.0}


def _prefetch_fund(sym: str) -> None:
    """Tai truoc chi so co ban o nen khi quet man — user click vao la co san."""
    try:
        from backend import fund
        fund.get_fundamentals(sym)
    except Exception:
        pass


def _verdict_of(score: int) -> tuple[str, str]:
    if score >= 10:
        return "MUA / TÍCH LŨY", "good"
    if score >= 6:
        return "THEO DÕI", "watch"
    if score >= 0:
        return "TRUNG TÍNH", "neutral"
    return "TRÁNH / GIẢM", "bad"


def _seed_screen():
    p = DATA / "screen.json"
    if p.exists():
        return
    src = ROOT.parent / "reports" / "screen_2026-10-08.json"
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
            results = obj["results"]
            for r in results:
                if "verdict" not in r:
                    r["verdict"], r["tone"] = _verdict_of(r.get("score", 0))
            # ap regime gate cho ket qua screen
            try:
                from backend.regime import apply_gate, get_regime
                rg = get_regime()
                results = [apply_gate(r, rg) if r.get("score", 0) >= 6 else r
                           for r in results]
            except Exception:
                pass
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
    with _screen_lock:
        if auto:
            screen_state["auto"] = True
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
        rows = obj.get("results", [])
        for r in rows:
            if "verdict" not in r:
                r["verdict"], r["tone"] = _verdict_of(r.get("score", 0))
        # ap regime gate cho ket qua cache
        try:
            from backend.regime import apply_gate, get_regime
            rg = get_regime()
            rows = [apply_gate(r, rg) if r.get("score", 0) >= 6 else r
                    for r in rows]
        except Exception:
            pass
        return rows
    except Exception:
        return []


def _run_pass() -> list[dict] | None:
    from backend.regime import get_regime
    try:
        _regime_cache = get_regime()
    except Exception:
        _regime_cache = {"regime": "neutral"}
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
            from backend.regime import apply_gate
            d = apply_gate(d, _regime_cache)
            merged[sym] = {k: d.get(k) for k in (
                "symbol", "close", "date", "rsi", "ma20", "ma50", "ma200", "vol_ratio",
                "r5", "r20", "sup", "res", "hi52", "lo52", "score", "verdict", "tone",
                "stop", "t1", "t2", "risk_pct", "rr")}
            if d.get("regime_gate"):
                merged[sym]["regime_gate"] = True
                merged[sym]["regime_note"] = d.get("regime_note", "")
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
