"""Screener ky thuat: quet universe, cham diem, xep hang."""
import sys, time, json, os, collections
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
from vnstock.api.quote import Quote
from vnstock import Market

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, os.environ.get("SC_CACHE", "_cache"))
os.makedirs(CACHE, exist_ok=True)

START = os.environ.get("SC_START", "2025-06-01")
END = os.environ.get("SC_END", "2026-09-25")
TAG = os.environ.get("SC_TAG", "")

_req_ts = collections.deque()


def _throttle(max_per_min=14):
    """Giu toi da `max_per_min` request trong 60s cuoi (guest = 20/phut)."""
    now = time.time()
    while _req_ts and now - _req_ts[0] < 60:
        _req_ts.popleft()
    if len(_req_ts) >= max_per_min:
        wait = 60 - (now - _req_ts[0]) + 0.5
        print(f"    [THROTTLE] cho {wait:.0f}s...", flush=True)
        time.sleep(wait)
        now = time.time()
        while _req_ts and now - _req_ts[0] < 60:
            _req_ts.popleft()
    _req_ts.append(time.time())

VN30 = ["ACB","BID","BSR","CTG","FPT","GAS","GVR","HDB","HPG","LPB","MBB","MCH","MSN",
        "MWG","SAB","SHB","SSB","SSI","STB","TCB","TCX","VCB","VHM","VIB","VIC","VJC",
        "VNM","VPB","VPL","VRE"]
EXTRA = ["VIX","HCM","VND","SHS","PVS","DIG","KDH","DXG","NVL","HSG","GEG","CTD","DGC","PHR","FRT"]
UNIVERSE = VN30 + EXTRA


def _normalize(df, date_col):
    df = df.rename(columns={date_col: "Date", "open": "Open", "high": "High",
                            "low": "Low", "close": "Close", "volume": "Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")


def _read_cache(name):
    p = os.path.join(CACHE, name + ".csv")
    if os.path.exists(p):
        df = pd.read_csv(p, index_col=0, parse_dates=True)
        if len(df) > 0:
            return df
    return None


def _write_cache(df, name):
    df.to_csv(os.path.join(CACHE, name + ".csv"))


def fetch_history(sym, retries=4):
    cached = _read_cache(sym)
    if cached is not None:
        return cached
    last = None
    for a in range(retries):
        try:
            _throttle()
            df = Quote(symbol=sym, source="VCI").history(
                start=START, end=END, interval="1D")
            if df is not None and len(df) > 0:
                df = _normalize(df, "time")
                _write_cache(df, sym)
                return df
            last = "empty"
        except SystemExit:
            last = "rate-limit"
            time.sleep(35)
        except Exception as e:
            last = e
            time.sleep(2 * (a + 1))
    print(f"  [SKIP] {sym}: {last}")
    return None


def fetch_index():
    cached = _read_cache("_VNINDEX")
    if cached is not None:
        return cached
    for a in range(4):
        try:
            _throttle()
            df = Market().index(symbol="VNINDEX").ohlcv(
                start=START, end=END, interval="1D", count=300)
            df = _normalize(df, "time")
            _write_cache(df, "_VNINDEX")
            return df
        except SystemExit:
            time.sleep(35)
        except Exception as e:
            print("  [INDEX ERR]", e)
            time.sleep(3)
    return None


def score(df, bench):
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    if len(df) < 210:
        return None
    px = float(c.iloc[-1]) * 1000  # VCI tra ve nghin dong
    ma = {n: float(c.rolling(n).mean().iloc[-1]) * 1000 for n in (5, 20, 50, 200)}

    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = float((100 - 100 / (1 + gain / loss)).iloc[-1])

    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig = macd.ewm(span=9, adjust=False).mean()
    hist = float((macd - sig).iloc[-1])
    hist_prev = float((macd - sig).iloc[-2])

    vol_last = float(v.iloc[-1])
    vol_ma5 = float(v.rolling(5).mean().iloc[-1])
    vol_ma20 = float(v.rolling(20).mean().iloc[-1])
    vol_val_ma20 = float((v * c).rolling(20).mean().iloc[-1]) / 1e6  # ty VND/phiên

    # --- Chi so 1: XU HUONG (0-3) ---
    t = 0
    t += 1 if px > ma[50] else 0
    t += 1 if px > ma[200] else 0
    t += 1 if ma[20] > ma[50] else 0

    # --- Chi so 2: MOMENTUM (0-3) ---
    m = 0
    m += 1 if float(macd.iloc[-1]) > float(sig.iloc[-1]) else 0
    m += 1 if hist > 0 and hist > hist_prev else 0
    if 50 <= rsi <= 70:
        m += 1
    elif 45 <= rsi < 50 or 70 < rsi <= 75:
        m += 0.5

    # --- Chi so 3: DONG TIEN (0-2) ---
    f = 0
    f += 1 if vol_last > vol_ma20 else 0
    f += 1 if vol_ma5 > vol_ma20 else 0

    # --- Chi so 4: VI TRI GIA (0-2) ---
    p = 0
    p += 1 if px > ma[20] else 0
    ext = px / ma[50] - 1
    p += 1 if ext < 0.15 else 0  # khong keo dai qua muc

    # --- Chi so 5: SUC MANH TUONG DOI vs VNINDEX (0-2) ---
    r = 0
    if bench is not None and "Close" in bench.columns:
        bx = bench.copy()
        bx.index = bx.index.normalize()
        bb = bx["Close"].reindex(c.index).ffill().dropna()
        for win, pt in ((20, 1), (60, 1)):
            if len(c) > win and len(bb) > win:
                try:
                    rs = (px / float(c.iloc[-win])) - (float(bb.iloc[-1]) / float(bb.iloc[-win]))
                    if rs > 0:
                        r += pt
                except Exception:
                    pass

    total = t + m + f + p + r
    atr14 = float(pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                            axis=1).max(axis=1).ewm(alpha=1 / 14, adjust=False).mean().iloc[-1])

    return dict(
        sym=df.attrs.get("sym"), as_of=str(df.index[-1])[:10],
        px=px, chg=float((c.iloc[-1] / c.iloc[-2] - 1) * 100),
        ret20=round((float(c.iloc[-1]) / float(c.iloc[-21]) - 1) * 100, 1),
        ret60=round((float(c.iloc[-1]) / float(c.iloc[-61]) - 1) * 100, 1),
        ma20=round(ma[20], 0), ma50=round(ma[50], 0), ma200=round(ma[200], 0),
        vs_ma50=round((px / ma[50] - 1) * 100, 2), vs_ma200=round((px / ma[200] - 1) * 100, 2),
        rsi=round(rsi, 1), macd_hist=round(hist, 4),
        macd_up=hist > hist_prev,
        vol_ratio=round(vol_last / vol_ma20, 2),
        liq_yen=round(vol_val_ma20, 1),
        atr_pct=round(atr14 * 1000 / px * 100, 2),
        hi52=round(float(h.max()) * 1000), lo52=round(float(l.min()) * 1000),
        dd_from_hi=round((px / float(h.max()) - 1) * 100, 1),
        score_xh=t, score_mom=m, score_dt=f, score_vp=p, score_rs=r,
        total=round(total, 1), n=len(df),
    )


def main():
    print(f"Universe: {len(UNIVERSE)} ma")
    bench = fetch_index()
    print("VNINDEX:", "OK" if bench is not None else "FAIL")
    rows = []
    for i, sym in enumerate(UNIVERSE, 1):
        df = fetch_history(sym)
        if df is None:
            continue
        df.attrs["sym"] = sym
        s = score(df, bench)
        if s:
            rows.append(s)
            print(f"[{i:2d}/{len(UNIVERSE)}] {sym}: {s['total']}  "
                  f"px={s['px']} rsi={s['rsi']} liq={s['liq_yen']}ty "
                  f"n={s['n']}", flush=True)
        else:
            print(f"[{i:2d}/{len(UNIVERSE)}] {sym}: SKIP (n={len(df)} cho phep)", flush=True)
        time.sleep(0.8)

    out = pd.DataFrame(rows).sort_values("total", ascending=False)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        f"screener_result{TAG}.json")
    out.to_json(path, orient="records", indent=2, force_ascii=False)
    print("\n=== TOP 15 ===")
    cols = ["sym", "px", "chg", "total", "score_xh", "score_mom", "score_dt",
            "score_vp", "score_rs", "rsi", "vol_ratio", "liq_yen", "vs_ma50", "vs_ma200"]
    print(out.head(15)[cols].to_string(index=False))
    print("\n=== BOTTOM 5 ===")
    print(out.tail(5)[cols].to_string(index=False))
    print("\nSaved:", path)


if __name__ == "__main__":
    main()

