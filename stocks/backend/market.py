"""Du lieu thi truong + phan tich ky thuat (vnstock) co cache va cham phit API."""
import contextlib
import io
import json
import threading
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SYM_DIR = DATA / "sym"
NEWS_DIR = DATA / "news"
for _d in (DATA, SYM_DIR, NEWS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SKILL_DATA = ROOT.parent / ".opencode" / "skills" / "vietnam-stock-analysis" / "stock-data"

_VN = ZoneInfo("Asia/Ho_Chi_Minh")


def now_vn() -> datetime:
    """Gio Viet Nam — may chu (Render) chay UTC nen khong duoc dung datetime.now() thuan."""
    return datetime.now(_VN)

BASKET = [
    "VCB", "CTG", "BID", "TCB", "MBB", "ACB", "STB", "VPB", "HDB", "LPB",
    "FPT", "CTR", "CMG", "VGI",
    "HPG", "NKG", "SMC", "DPM", "PHR",
    "VNM", "MSN", "SAB", "MWG", "FRT", "DGW", "PNJ", "SBT",
    "VHM", "VIC", "KDH", "DIG", "DXG", "IDC",
    "GAS", "PLX", "POW",
    "SSI", "VCI", "HCM", "VND",
]

GAP = 7.5          # giay giua 2 lan go vnstock (guest 20 req/phut ~ 2 req/ma)
LIMIT_WAIT = 62     # cho khi bi rate limit
CACHE_TTL = 6 * 3600

_lock = threading.Lock()
_next_slot = 0.0
_live_count = 0        # so yeu cau live dang cho slot (uu tien hon quet man)


def _live_enter():
    global _live_count
    with _lock:
        _live_count += 1


def _live_exit():
    global _live_count
    with _lock:
        _live_count = max(0, _live_count - 1)


# ---------------------------------------------------------------- rate limit
def paced(fn, *args, priority: bool = False, **kwargs):
    """Goi vnstock da cham phit, tu xu ly rate limit.

    priority=True (live: chi so + ma dang mo) se cho phep di truoc cac
    yeu cau quet man de khong bi doi 5 phut.
    """
    global _next_slot
    last_err = None
    if priority:
        _live_enter()
    else:
        while _live_count > 0:
            time.sleep(0.3)
    try:
        for attempt in range(3):
            with _lock:
                now = time.time()
                wait = max(0.0, _next_slot - now)
                _next_slot = max(now, _next_slot) + GAP
            if wait:
                time.sleep(wait)
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    return fn(*args, **kwargs)
            except BaseException as e:  # noqa: BLE001 - vnstock raised SystemExit on rate limit
                last_err = e
                msg = str(e)
                limited = isinstance(e, SystemExit) or "rate" in msg.lower() or "Rate Limit" in msg or "giới hạn" in msg
                if limited and attempt < 2:
                    with _lock:
                        _next_slot = max(_next_slot, time.time() + LIMIT_WAIT)
                    time.sleep(LIMIT_WAIT)
                    continue
                raise last_err
    finally:
        if priority:
            _live_exit()


def _quote_history(sym: str) -> pd.DataFrame:
    from vnstock import Quote
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=430)
    df = Quote(symbol=sym, source="VCI").history(
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), interval="1D")
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={"time": "Date", "open": "Open", "high": "High",
                            "low": "Low", "close": "Close", "volume": "Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    df = df[~df.index.duplicated(keep="last")].tail(260)
    return df


# ---------------------------------------------------------------- indicators
def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, 1e-12)
    return 100 - 100 / (1 + rs)


def _tick(p: float) -> float:
    return 0.1 if p < 20 else (0.2 if p < 50 else (0.5 if p < 100 else 1.0))


def _r(x: float) -> float:
    t = _tick(x)
    return round(round(x / t) * t, 2)


def compute(sym: str, df: pd.DataFrame) -> dict | None:
    if df is None or len(df) < 60:
        return None
    c, v, hi, lo = df["Close"], df["Volume"], df["High"], df["Low"]
    last = float(c.iloc[-1])
    if last <= 0:
        return None

    ma = {p: float(c.rolling(p).mean().iloc[-1]) for p in (20, 50, 200) if len(c) >= p}
    rsi = float(_rsi(c).iloc[-1])
    macd_line = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sig = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - sig
    hist_val, hist_prev = float(hist.iloc[-1]), float(hist.iloc[-5])
    vol20 = float(v.rolling(20).mean().iloc[-1]) or 1.0
    vr = float(v.iloc[-1]) / vol20
    r5 = (last / float(c.iloc[-6]) - 1) * 100
    r20 = (last / float(c.iloc[-21]) - 1) * 100 if len(c) > 21 else 0.0
    hi52, lo52 = float(c.tail(250).max()), float(c.tail(250).min())
    sup, res = float(lo.tail(20).min()), float(hi.tail(20).max())
    ma20, ma50 = ma.get(20, last), ma.get(50, last)
    ma200 = ma.get(200, last)

    score = 0
    score += 2 if last > ma20 else -2
    score += 2 if ma20 > ma50 else -2
    score += 2 if last > ma200 else -2
    score += 2 if hist_val > 0 and hist_val > hist_prev else (-2 if hist_val < 0 else 0)
    score += 1 if 45 <= rsi <= 72 else (-2 if rsi > 75 else 0)
    score += 1 if vr >= 1.0 else 0
    score += 2 if r20 > 0 else -1
    score += 1 if r5 > 0 else 0

    atr = float((hi - lo).tail(14).mean())
    stop = _r(max(sup * 0.985, last - 2.2 * atr))
    t1 = _r(min(res * 1.02, last * 1.06))
    t2 = _r(max(hi52, last * 1.12))

    # xu huong
    if last > ma20 > ma50 and last > ma200:
        trend = "xu hướng tăng, giá trên MA20/MA50/MA200"
    elif last > ma20 and last > ma50:
        trend = "hồi phục ngắn hạn, giá đã vượt MA20 và MA50"
    elif last > ma20:
        trend = "vừa vượt MA20 nhưng còn dưới MA50/MA200"
    elif last > ma50:
        trend = "đi ngang, giá dưới MA20"
    else:
        trend = "xu hướng giảm, giá dưới MA20 và MA50"

    # xu the + diem
    if score >= 10:
        verdict, tone = "MUA / TÍCH LŨY", "good"
    elif score >= 6:
        verdict, tone = "THEO DÕI", "watch"
    elif score >= 0:
        verdict, tone = "TRUNG TÍNH", "neutral"
    else:
        verdict, tone = "TRÁNH / GIẢM", "bad"

    # vung vao lenh
    near_res = res / last - 1 <= 0.03
    if rsi > 70:
        entry = [_r(ma20 * 0.99), _r(ma20 * 1.02)]
        entry_note = f"RSI {rsi:.0f} đang quá mua — KHÔNG mua đuổi, chờ pullback về vùng {entry[0]}–{entry[1]}"
    elif near_res:
        entry = [_r(last * 0.998), _r(res * 1.005)]
        entry_note = (f"Chờ đóng cửa trên kháng cự {res:.1f} với thanh khoản cao để mua, "
                      f"hoặc tích lũy trong vùng {entry[0]}–{entry[1]}")
    else:
        entry = [_r(max(sup * 0.99, ma20 * 0.985)), _r(last)]
        entry_note = f"Mua tích lũy trong vùng {entry[0]}–{entry[1]} (gần hỗ trợ {sup:.1f})"

    if score < 0:
        entry_note = (f"KHÔNG mua lúc này — cấu trúc kỹ thuật đang xấu. Vùng {entry[0]}–{entry[1]} "
                      f"chỉ là nơi nhiều người cắt lỗ; chờ giá vượt MA20 với thanh khoản tốt rồi tính tiếp")

    risk = (last - stop) / last * 100
    rr = (t1 - last) / max(last - stop, 1e-9)
    vol_txt = "thanh khoản thấp" if vr < 0.8 else ("thanh khoản cao" if vr >= 1.3 else "thanh khoản trung bình")

    narrative = (f"Giá {last:,.1f} đang {trend}. RSI {rsi:.0f}, MACD "
                 f"{'tích cực' if hist_val > 0 else 'tiêu cực'}, {vol_txt} ({vr:.2f}× TB20 phiên), "
                 f"20 phiên thay đổi {r20:+.1f}%. {entry_note}. Cắt lỗ {stop:.1f} "
                 f"(rủi ro {risk:.1f}%), chốt lời từng phần tại {t1:.1f} rồi hướng {t2:.1f} "
                 f"(risk:reward ~1:{rr:.1f})."
                 + ("" if score >= 0 else " Cấu trúc kỹ thuật đang xấu — ưu tiên đứng ngoài."))

    ohlcv = [
        {"time": d.strftime("%Y-%m-%d"), "open": round(float(o), 2), "high": round(float(h), 2),
         "low": round(float(l), 2), "close": round(float(x), 2), "volume": int(q)}
        for d, o, h, l, x, q in zip(df.index, df["Open"], df["High"], df["Low"], df["Close"], df["Volume"])
    ]

    return {
        "symbol": sym,
        "close": last,
        "date": str(df.index[-1].date()),
        "rsi": round(rsi, 1),
        "ma20": round(ma20, 2), "ma50": round(ma50, 2), "ma200": round(ma200, 2),
        "macd_hist": round(hist_val, 3),
        "vol_ratio": round(vr, 2),
        "r5": round(r5, 1), "r20": round(r20, 1),
        "sup": round(sup, 2), "res": round(res, 2),
        "hi52": round(hi52, 2), "lo52": round(lo52, 2),
        "score": score, "max_score": 13,
        "verdict": verdict, "tone": tone, "trend": trend,
        "entry": entry, "entry_note": entry_note,
        "stop": stop, "t1": t1, "t2": t2,
        "risk_pct": round(risk, 1), "rr": round(rr, 1),
        "narrative": narrative,
        "ohlcv": ohlcv,
        "updated_at": now_vn().isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------- cache I/O
def _fresh(path: Path) -> dict | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - obj.get("fetched_at", 0) < CACHE_TTL:
            return obj
    except Exception:
        pass
    return None


def _cached(path: Path) -> dict | None:
    """Doc cache bat ke het han (khong ghi de du lieu moi hon bang seed)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _seed_symbol(sym: str) -> dict | None:
    """Khai pha du lieu da co trong skill (khong can go API)."""
    p = SKILL_DATA / f"{sym.lower()}_data.json"
    if not p.exists():
        return None
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        data = compute(sym, df)
        if data:
            data["seed"] = True
            return data
    except Exception:
        return None
    return None


def get_symbol(sym: str, refresh: bool = False, priority: bool = False) -> dict:
    sym = sym.upper().strip()
    if not sym.isalpha() or not 2 <= len(sym) <= 6:
        return {"status": "error", "message": "Mã không hợp lệ"}
    path = SYM_DIR / f"{sym}.json"
    if not refresh:
        cached = _fresh(path)
        if cached:
            return {"status": "ready", "data": cached["data"]}
    try:
        df = paced(_quote_history, sym, priority=priority)
        data = compute(sym, df)
        if data is None:
            return {"status": "error", "message": f"Không lấy được dữ liệu {sym}"}
        _save(path, {"fetched_at": time.time(), "data": data})
        return {"status": "ready", "data": data}
    except Exception as e:
        cached = _fresh(path) or _cached(path) or _seeded_cache(sym)
        if cached:
            return {"status": "ready", "data": cached.get("data", cached), "stale": True}
        return {"status": "error", "message": f"Lỗi tải {sym}: {e}"}


def _seeded_cache(sym: str):
    """Seed chi dung trong bo nho khi khong co cache, khong ghi de du lieu live."""""
    data = _seed_symbol(sym)
    if data:
        return {"fetched_at": time.time(), "data": data}
    return None


# ---------------------------------------------------------------- overview
def _index_df(code: str) -> pd.DataFrame:
    from vnstock import Quote
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=430)
    df = Quote(symbol=code, source="VCI").history(
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), interval="1D")
    df = df.rename(columns={"time": "Date", "close": "Close", "high": "High", "low": "Low", "volume": "Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date").sort_index()


def _build_overview(refresh: bool = False) -> dict:
    items = []
    for code, label in (("VNINDEX", "VN-Index"), ("HNXINDEX", "HNX-Index")):
        df = paced(_index_df, code, priority=refresh)
        c = df["Close"]
        last = float(c.iloc[-1])
        prev = float(c.iloc[-2])
        ma20 = float(c.rolling(20).mean().iloc[-1])
        ma50 = float(c.rolling(50).mean().iloc[-1])
        ma200 = float(c.rolling(200).mean().iloc[-1])
        r20 = (last / float(c.iloc[-21]) - 1) * 100
        if last > ma20 and last > ma50:
            trend = "hồi phục / đi ngang"
        elif last > ma200:
            trend = "điều chỉnh nhưng trên MA200"
        else:
            trend = "giảm ngắn hạn (dưới MA20/MA50)"
        items.append({
            "code": code, "label": label,
            "close": round(last, 2),
            "chg": round(last - prev, 2),
            "chg_pct": round((last / prev - 1) * 100, 2),
            "ma20": round(ma20, 1), "ma50": round(ma50, 1), "ma200": round(ma200, 1),
            "r20": round(r20, 1),
            "hi30": round(float(c.tail(30).max()), 1),
            "lo30": round(float(c.tail(30).min()), 1),
            "vol_last_m": round(float(df["Volume"].iloc[-1]) / 1e6, 1),
            "vol20_m": round(float(df["Volume"].rolling(20).mean().iloc[-1]) / 1e6, 1),
            "date": str(df.index[-1].date()),
            "trend": trend,
            "above_ma20": last > ma20, "above_ma200": last > ma200,
        })
    return {"indices": items, "fetched_at": time.time(),
            "updated_at": now_vn().strftime("%H:%M:%S %d/%m/%Y")}


_ov_lock = threading.Lock()
_ov_state = {"status": "init", "data": None}


def overview(refresh: bool = False) -> dict:
    global _ov_state
    with _ov_lock:
        st = _ov_state
    if st["status"] == "ready" and not refresh:
        if time.time() - st["data"].get("fetched_at", 0) < 30 * 60:
            return {"status": "ready", **st["data"]}
        return {"status": "ready", "stale": True, **st["data"]}

    path = DATA / "overview.json"
    if not refresh:
        cached = _fresh(path) or _cached(path) or _seed_overview()
        if cached:
            inner = cached.get("data") or cached
            inner.setdefault("fetched_at", cached.get("fetched_at", time.time()))
            with _ov_lock:
                _ov_state = {"status": "ready", "data": inner}
            age = time.time() - inner.get("fetched_at", 0)
            return {"status": "ready", "stale": age > 30 * 60, **inner}

    # fetch dong bo lan dau / refresh
    with _ov_lock:
        if _ov_state["status"] == "loading":
            return {"status": "fetching"}
        _ov_state = {"status": "loading", "data": None}
    try:
        data = _build_overview(refresh=refresh)
        _save(path, {"fetched_at": time.time(), "data": data})
        with _ov_lock:
            _ov_state = {"status": "ready", "data": data}
        return {"status": "ready", **data}
    except Exception as e:
        with _ov_lock:
            _ov_state = {"status": "error", "data": None}
        return {"status": "error", "message": str(e)}


def _seed_overview():
    p = ROOT.parent / "reports" / "index_2026-10-08.json"
    if not p.exists():
        return None
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
        items = []
        for r in rows:
            label = {"VNINDEX": "VN-Index", "HNXINDEX": "HNX-Index"}.get(r["index"], r["index"])
            last = r["close"]
            items.append({
                "code": r["index"], "label": label, "close": last,
                "chg": r["chg"], "chg_pct": r["chg_pct"],
                "ma20": r["ma20"], "ma50": r["ma50"], "ma200": r["ma200"],
                "r20": r["r20"], "hi30": r["hi30"], "lo30": r["lo30"],
                "vol_last_m": round(r.get("vol_last_m", 0), 1),
                "vol20_m": round(r.get("vol20_m", 0), 1),
                "date": r["date"],
                "trend": ("hồi phục / đi ngang" if last > r["ma20"] and last > r["ma50"]
                          else ("điều chỉnh nhưng trên MA200" if last > r["ma200"] else "giảm ngắn hạn (dưới MA20/MA50)")),
                "above_ma20": last > r["ma20"], "above_ma200": last > r["ma200"],
            })
        obj = {"fetched_at": time.time(), "data": {"indices": items, "fetched_at": time.time(),
                                                   "updated_at": "seed từ reports/index_2026-10-08.json"}}
        _save(DATA / "overview.json", obj)
        return obj
    except Exception:
        return None


# ---------------------------------------------------------------- screen
_screen_lock = threading.Lock()
screen_state = {"status": "idle", "done": 0, "total": 0, "current": "", "results": [],
                "generated_at": None, "message": "", "auto": False, "_abort": False,
                "_kick": False, "worker_alive": False,
                "cycles": 0, "next_at": 0.0}


def _in_session() -> bool:
    """Gio giao dich Viet Nam (T2-T6, T7 chi buoi sang)."""
    now = now_vn()
    hm = int(now.strftime("%H%M"))
    if now.weekday() == 6:
        return False
    if now.weekday() == 5:          # thu 7: 9:15 - 11:35
        return 915 <= hm <= 1135
    return 915 <= hm <= 1135 or 1255 <= hm <= 1505


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
        return rows
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
            merged[sym] = {k: d[k] for k in (
                "symbol", "close", "date", "rsi", "ma20", "ma50", "ma200", "vol_ratio",
                "r5", "r20", "sup", "res", "hi52", "lo52", "score", "verdict", "tone",
                "stop", "t1", "t2", "risk_pct", "rr")}
        with _screen_lock:
            screen_state.update({"done": i,
                                 "results": sorted(merged.values(), key=lambda x: -x["score"])})
    return sorted(merged.values(), key=lambda x: -x["score"])


def _wait_between_passes() -> bool:
    """Ngu giua 2 vong quet. Tra ve False neu phai dung."""
    while True:
        with _screen_lock:
            if not screen_state["auto"] or screen_state["_kick"]:
                return screen_state["auto"]
        if _in_session():
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
            rows.sort(key=lambda x: -x["score"])
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
    finally:
        with _screen_lock:
            if screen_state["status"] == "running":
                screen_state["status"] = "ready"
            screen_state.update({"worker_alive": False, "current": "", "next_at": 0.0,
                                 "_kick": False})


# ---------------------------------------------------------------- bootstrap
_seed_screen()
if _cached(DATA / "overview.json") is None:
    _seed_overview()
