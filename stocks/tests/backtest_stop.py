# -*- coding: utf-8 -*-
"""Backtest stop ATR + T1/T2 — so voi hold 20 phien co dinh.

Su dung OHLCV cache (data/backtest/*.pkl) + signals.csv da luu.
Moi tin hieu score >= 10 duoc mo phong 2 chien luoc:
  A) Hold 20 phien (baseline — backtest truoc da lam)
  B) Active: stop ATR + T1 + T2, thoat som khi cham muc

Phi 0.4% ca 2 chien luoc. Khong overlap trong cung ma.
"""
import os
import sys
from pathlib import Path

os.environ["VNSTOCK_DISABLE_AGENT_SETUP"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

FEES = 0.004
HOLD = 20
THRESHOLD = 10
BT_DIR = Path(__file__).resolve().parent.parent / "data" / "backtest"


def _r(x):
    return round(x, 1) if x < 50 else round(x, 0)


def compute_levels(df: pd.DataFrame) -> dict | None:
    """Tinh stop/t1/t2 tu OHLCV den ngay hien tai (giong calc.py)."""
    if len(df) < 60:
        return None
    c, hi, lo = df["Close"], df["High"], df["Low"]
    last = float(c.iloc[-1])
    if last <= 0:
        return None
    ma20 = float(c.rolling(20).mean().iloc[-1])
    ma50 = float(c.rolling(50).mean().iloc[-1]) if len(c) >= 50 else last
    ma200 = float(c.rolling(200).mean().iloc[-1]) if len(c) >= 200 else last
    sup = float(lo.tail(20).min())
    res = float(hi.tail(20).max())
    hi52 = float(c.tail(250).max())

    # RSI nhanh
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = float((100 - 100 / (1 + rs)).iloc[-1])

    # MACD hist
    macd_line = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sig_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - sig_line
    hist_val = float(hist.iloc[-1])
    hist_prev = float(hist.iloc[-5]) if len(hist) >= 5 else hist_val

    v = df["Volume"]
    vol20 = float(v.rolling(20).mean().iloc[-1]) or 1.0
    vr = float(v.iloc[-1]) / vol20
    r5 = (last / float(c.iloc[-6]) - 1) * 100
    r20 = (last / float(c.iloc[-21]) - 1) * 100 if len(c) > 21 else 0.0

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
    return {"score": score, "stop": stop, "t1": t1, "t2": t2, "last": last}


def simulate_active(df: pd.DataFrame, entry_i: int, stop: float, t1: float,
                     t2: float, t1_mult: float = 1.0, atr_mult: float = 2.2) -> float | None:
    """Mo phong active trading. atr_mult dieu chinh do rong stop (2.2 = goc)."""
    n = len(df)
    if entry_i + 1 >= n:
        return None
    entry_price = float(df["Open"].iloc[entry_i + 1])
    if entry_price <= 0:
        return None

    # tinh lai stop theo atr_mult
    window = df.iloc[:entry_i + 1]
    hi, lo = window["High"], window["Low"]
    atr = float((hi - lo).tail(14).mean())
    sup = float(lo.tail(20).min())
    stop_adj = max(sup * 0.985, entry_price - atr_mult * atr)
    if stop_adj >= entry_price:
        return None   # stop o tren entry — khong hop le

    t1_adj = entry_price + (t1 - entry_price) * t1_mult if t1 > entry_price else t1

    for day in range(entry_i + 1, min(entry_i + 1 + HOLD, n)):
        o = float(df["Open"].iloc[day])
        h = float(df["High"].iloc[day])
        l = float(df["Low"].iloc[day])

        if o <= stop_adj:
            return (stop_adj / entry_price - 1) - FEES
        if o >= t2:
            return (o / entry_price - 1) - FEES
        if o >= t1_adj:
            return (o / entry_price - 1) - FEES
        if l <= stop_adj:
            return (stop_adj / entry_price - 1) - FEES
        if h >= t2:
            return (t2 / entry_price - 1) - FEES
        if h >= t1_adj:
            return (t1_adj / entry_price - 1) - FEES

    exit_i = min(entry_i + HOLD, n - 1)
    exit_price = float(df["Close"].iloc[exit_i])
    return (exit_price / entry_price - 1) - FEES


def main():
    # load OHLCV cache
    ohlcv = {}
    for p in BT_DIR.glob("*.pkl"):
        sym = p.stem
        if sym in ("VNINDEX",):
            continue
        try:
            ohlcv[sym] = pd.read_pickle(p)
        except Exception:
            pass

    bench_df = None
    bp = BT_DIR / "VNINDEX.pkl"
    if bp.exists():
        bench_df = pd.read_pickle(bp)

    rows_hold = []
    rows_active = {}   # (t1_mult, atr_mult) -> list
    # test: T1 x1.0 voi cac do rong stop khac nhau, va stop-only voi do rong stop
    CONFIGS = [
        (1.0, 2.2), (1.0, 3.0), (1.0, 4.0),   # T1 goc + stop rong dan
        (99, 2.2), (99, 3.0), (99, 4.0),      # stop-only + stop rong dan
    ]

    for sym, df in sorted(ohlcv.items()):
        n = len(df)
        if n < 80 or bench_df is None:
            continue
        last_exit = pd.Timestamp.min
        for i in range(60, n - 1):
            date = df.index[i]
            if date <= last_exit:
                continue
            window = df.iloc[:i + 1]
            lv = compute_levels(window)
            if lv is None or lv["score"] < THRESHOLD:
                continue

            entry_i = i + 1
            if entry_i >= n:
                break
            entry_date = df.index[entry_i]
            exit_date_hold = df.index[min(entry_i + HOLD, n - 1)]

            bi0 = bench_df.index.searchsorted(entry_date)
            bi1 = bench_df.index.searchsorted(exit_date_hold, side="right") - 1
            if bi0 >= len(bench_df) or bi1 <= bi0:
                continue
            b0 = float(bench_df["Close"].iloc[bi0])
            b1 = float(bench_df["Close"].iloc[bi1])
            bench_ret = b1 / b0 - 1 if b0 > 0 else None
            if bench_ret is None:
                continue

            entry_price = float(df["Open"].iloc[entry_i])
            if entry_price <= 0:
                continue

            exit_price_hold = float(df["Close"].iloc[min(entry_i + HOLD, n - 1)])
            hold_net = (exit_price_hold / entry_price - 1) - FEES
            rows_hold.append((sym, date, hold_net, bench_ret))

            for cfg in CONFIGS:
                active_net = simulate_active(df, i, lv["stop"], lv["t1"], lv["t2"],
                                             t1_mult=cfg[0], atr_mult=cfg[1])
                if active_net is not None:
                    rows_active.setdefault(cfg, []).append((sym, date, active_net, bench_ret))

            last_exit = exit_date_hold

    net = np.array([r[2] for r in rows_hold])
    bench = np.array([r[3] for r in rows_hold])
    excess = net - bench
    n = len(excess)
    se = excess.std(ddof=1) / np.sqrt(n) if n > 1 else 0
    t = excess.mean() / se if se > 0 else 0
    print(f"\n=== HOLD 20 PHIEN (baseline) ===")
    print(f"  n={n}  win={(net > 0).mean()*100:.1f}%  TB={net.mean()*100:+.2f}%  "
          f"excess={excess.mean()*100:+.2f}%  t={t:.2f}  median={np.median(net)*100:+.2f}%")
    print(f"  p10={np.percentile(net,10)*100:+.1f}%  p90={np.percentile(net,90)*100:+.1f}%  "
          f"max={net.max()*100:+.1f}%  min={net.min()*100:+.1f}%")

    hold_map = {(r[0], r[1]): r[2] for r in rows_hold}
    print(f"\n=== ACTIVE (tat ca threshold >={THRESHOLD}) ===")
    print(f"{'config':<22} {'n':>4} {'win%':>5} {'TB%':>7} {'excess%':>8} {'t':>6} "
          f"{'med%':>7} {'p10%':>7} {'p90%':>7} {'vs hold':>8}")
    for cfg in CONFIGS:
        rows = rows_active.get(cfg, [])
        if not rows:
            continue
        net = np.array([r[2] for r in rows])
        bench = np.array([r[3] for r in rows])
        excess = net - bench
        n = len(excess)
        se = excess.std(ddof=1) / np.sqrt(n) if n > 1 else 0
        t = excess.mean() / se if se > 0 else 0
        act_map = {(r[0], r[1]): r[2] for r in rows}
        common = set(hold_map) & set(act_map)
        diff = np.mean([act_map[k] - hold_map[k] for k in common]) * 100 if common else 0
        t1m, atrm = cfg
        label = f"T1x{t1m}_stop{atrm}x" if t1m < 99 else f"stopOnly_{atrm}x"
        print(f"  {label:<20} {n:>4} {(net > 0).mean()*100:>5.1f} {net.mean()*100:>+7.2f} "
              f"{excess.mean()*100:>+8.2f} {t:>6.2f} {np.median(net)*100:>+7.2f} "
              f"{np.percentile(net,10)*100:>+7.1f} {np.percentile(net,90)*100:>+7.1f} "
              f"{diff:>+8.2f}")

    print("\nHoan tat.")


if __name__ == "__main__":
    main()
