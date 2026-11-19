# -*- coding: utf-8 -*-
"""Backtest diem so ky thuat (backend.calc.compute) tren du lieu lich su ~3 nam.

- Du lieu: BASKET (40 ma) + VNINDEX, 2022-10-01 -> nay, goi qua paced (7.5s/goi), cache pkl.
- Vinh vien dung PRODUCTION compute() — moi phien doc cung 260 phien cuoi (giong app chay that).
- Tin hieu: diem so tai close phien t -> mua tai OPEN phien t+1, ban tai CLOSE phien t+20.
- Chi phi luu ky 0.4% (0.15% mua + 0.15% ban + 0.1% thue ban) tru truoc.
- Mo phong theo tung ma, khong lenh nao vo lien lap trong cung ma (thoat het roi moi vao tiep).
- Bench: VNINDEX cung ky mo/ban -> excess return.
- File: stocks/data/backtest/ (cache + signals.csv) — gitignore, rerun mien phi.
"""
import os
import sys
import time
from pathlib import Path

os.environ["VNSTOCK_DISABLE_AGENT_SETUP"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from backend.calc import compute
from backend.store import BASKET
from backend.vnrate import paced

CACHE = Path(__file__).resolve().parent.parent / "data" / "backtest"
CACHE.mkdir(parents=True, exist_ok=True)

START, END = "2022-10-01", "2026-10-15"
WARMUP = 260          # production luon doc tail(260)
HOLD = 20             # phien
FEES = 0.004          # phi luu ky round trip
REQUIRED = {"Open", "High", "Low", "Close", "Volume"}


def _normalize(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns={"time": "Date", "open": "Open", "high": "High",
                             "low": "Low", "close": "Close", "volume": "Volume"})
    if "Date" not in df.columns:
        df = df.copy()
        df["Date"] = df.index
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df[~df.index.duplicated(keep="last")]


def fetch(sym: str) -> pd.DataFrame | None:
    p = CACHE / f"{sym}.pkl"
    if p.exists():
        try:
            return pd.read_pickle(p)
        except Exception:
            pass

    def _go():
        from vnstock import Quote
        return Quote(symbol=sym, source="VCI").history(
            start=START, end=END, interval="1D")

    try:
        raw = paced(_go)
    except Exception as e:
        print(f"  ! {sym}: {type(e).__name__} {e}", flush=True)
        return None
    if raw is None or raw.empty:
        print(f"  ! {sym}: rong", flush=True)
        return None
    df = _normalize(raw)
    if not REQUIRED.issubset(df.columns):
        print(f"  ! {sym}: thieu cot {REQUIRED - set(df.columns)}", flush=True)
        return None
    df.to_pickle(p)
    return df


def evaluate(sym: str, df: pd.DataFrame, bo: pd.Series, bc: pd.Series) -> list[dict]:
    """Duyet tung phien, cham diem bang compute() that, lay forward return 20 phien."""
    n = len(df)
    rows = []
    for i in range(WARMUP - 1, n - HOLD - 2):
        w = df.iloc[i - WARMUP + 1:i + 1]
        try:
            r = compute(sym, w)
        except Exception:
            continue
        if r is None:
            continue
        e, x = i + 1, i + 1 + HOLD
        op = float(df["Open"].iloc[e])
        cl = float(df["Close"].iloc[x])
        if not np.isfinite(op) or op <= 0 or not np.isfinite(cl):
            continue
        b_o, b_c = float(bo.iloc[e]), float(bc.iloc[x])
        rows.append({
            "sym": sym,
            "date": df.index[i],
            "exit_date": df.index[x],
            "score": r["score"],
            "fwd": cl / op - 1,
            "bench_fwd": (b_c / b_o - 1) if np.isfinite(b_o) and b_o > 0 else np.nan,
        })
    return rows


def simulate(rows: pd.DataFrame, threshold: int) -> dict:
    trades = []
    for sym, g in rows.groupby("sym", sort=False):
        last_exit = pd.Timestamp.min
        for t in g.itertuples():
            if t.score < threshold or t.date <= last_exit:
                continue
            if not np.isfinite(t.bench_fwd):
                continue
            trades.append(t)
            last_exit = t.exit_date
    if not trades:
        return {"n": 0}
    net = np.array([t.fwd for t in trades]) - FEES
    bench = np.array([t.bench_fwd for t in trades])
    excess = net - bench
    return {
        "n": len(trades),
        "syms": len({t.sym for t in trades}),
        "win": float((net > 0).mean()),
        "beat": float((excess > 0).mean()),
        "avg": float(net.mean()),
        "med": float(np.median(net)),
        "bench": float(bench.mean()),
        "excess": float(excess.mean()),
        "p10": float(np.percentile(net, 10)),
        "p90": float(np.percentile(net, 90)),
        "min": float(net.min()),
        "max": float(net.max()),
    }


def show(title: str, m: dict):
    if m["n"] == 0:
        print(f"\n=== {title}: khong co giao dich ===")
        return
    print(f"\n=== {title} ===")
    print(f"  so giao dich      : {m['n']} (tren {m['syms']} ma)")
    print(f"  ty le THANG       : {m['win']*100:.1f}%  (loi sau phi > 0)")
    print(f"  ty le DUNG hon HNX: {m['beat']*100:.1f}%  (excess > 0 vs VN-Index)")
    print(f"  loi TB            : {m['avg']*100:+.2f}%   median {m['med']*100:+.2f}%  / 20 phien")
    print(f"  VN-Index cung ky  : {m['bench']*100:+.2f}%")
    print(f"  excess TB          : {m['excess']*100:+.2f}%")
    print(f"  phan bo           : p10 {m['p10']*100:+.1f}%  p90 {m['p90']*100:+.1f}%  "
          f"min {m['min']*100:+.1f}%  max {m['max']*100:+.1f}%")


t0 = time.time()

# ---------------------------------------------------------------- fetch
print(f"Fetch {len(BASKET)} ma + VNINDEX ({START} -> {END}) qua paced 7.5s/goi...", flush=True)
data = {}
for k, sym in enumerate(BASKET + ["VNINDEX"], 1):
    df = fetch(sym)
    if df is not None:
        data[sym] = df
    print(f"  [{k}/{len(BASKET)+1}] {sym}: {0 if df is None else len(df)} phien "
          f"({time.time()-t0:.0f}s)", flush=True)

bench = data.pop("VNINDEX", None)
if bench is None or len(bench) < WARMUP + HOLD + 2:
    print("FAIL: VNINDEX thieu du lieu", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------- evaluate
print("\nCham diem tung phien bang compute() PRODUCTION...", flush=True)
all_rows = []
for k, (sym, df) in enumerate(data.items(), 1):
    bo = bench["Open"].reindex(df.index)
    bc = bench["Close"].reindex(df.index)
    rows = evaluate(sym, df, bo, bc)
    all_rows.extend(rows)
    print(f"  [{k}/{len(data)}] {sym}: {len(rows)} phien danh gia", flush=True)

if not all_rows:
    print("FAIL: khong co phien danh gia nao", file=sys.stderr)
    sys.exit(1)

sig = pd.DataFrame(all_rows).sort_values(["date", "sym"]).reset_index(drop=True)
sig.to_csv(CACHE / "signals.csv", index=False)
print(f"\nTong phien danh gia: {len(sig)} (trong {sig['sym'].nunique()} ma), "
      f"luu signals.csv", flush=True)

# ---------------------------------------------------------------- phan bo diem so
print("\n=== Phan bo diem so -> loi 20 phien tiep theo (chua tru phi, co trung lap) ===")
buckets = [(-99, -1, "diem < 0  (TRÁNH)"), (0, 5, "diem 0-5  (TRUNG TINH)"),
           (6, 9, "diem 6-9  (THEO DÕI)"), (10, 99, "diem >=10 (MUA/TÍCH LŨY)")]
for lo, hi, label in buckets:
    sub = sig[(sig["score"] >= lo) & (sig["score"] <= hi)]
    if not len(sub):
        continue
    print(f"  {label:28s} n={len(sub):6d}  TB={sub['fwd'].mean()*100:+.2f}%  "
          f"median={sub['fwd'].median()*100:+.2f}%  win={(sub['fwd']>0).mean()*100:.1f}%  "
          f"vs VNIX={sub['bench_fwd'].mean()*100:+.2f}%")

# ---------------------------------------------------------------- mo phong
show("SCENARIO A: diem >= 10 (MUA/TÍCH LŨY), hold 20 phien, phi 0.4%", simulate(sig, 10))
show("SCENARIO B: diem >= 6 (THEO DÕI tro len), hold 20 phien, phi 0.4%", simulate(sig, 6))

# ---------------------------------------------------------------- buy&hold
first, last = sig["date"].min(), sig["date"].max()
b0 = bench.loc[bench.index >= first, "Close"]
print(f"\n=== VN-Index buy & hold tu {first.date()} den {last.date()} ===")
if len(b0) > 1:
    print(f"  {((float(b0.iloc[-1]) / float(b0.iloc[0]) - 1) * 100):+.1f}% "
          f"({len(b0)} phien danh gia)")

print(f"\nHoan tat trong {time.time()-t0:.0f}s.", flush=True)
