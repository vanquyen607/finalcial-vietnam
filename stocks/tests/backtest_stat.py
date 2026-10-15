# -*- coding: utf-8 -*-
"""Y nghia thong ke cua backtest — doc signals.csv (da luu), khong go API."""
import os
import sys
from pathlib import Path

os.environ["VNSTOCK_DISABLE_AGENT_SETUP"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

FEES = 0.004
HOLD = 20
sig = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "backtest" / "signals.csv",
                  parse_dates=["date", "exit_date"]).sort_values(["sym", "date"])

rows = []
for sym, g in sig.groupby("sym", sort=False):
    last_exit = pd.Timestamp.min
    for t in g.itertuples():
        if t.score < 10 or t.date <= last_exit or not np.isfinite(t.bench_fwd):
            continue
        rows.append((t.fwd - FEES, t.bench_fwd, t.date.year, t.score))
        last_exit = t.exit_date

net = np.array([r[0] for r in rows])
bench = np.array([r[1] for r in rows])
scores = np.array([r[3] for r in rows])
excess = net - bench
n = len(excess)
se = excess.std(ddof=1) / np.sqrt(n)
t = excess.mean() / se

print(f"n = {n} giao dich (threshold >= 10, khong trung lap, phi da tru)")
print(f"excess TB = {excess.mean()*100:+.3f}% / 20 phien")
print(f"sd        = {excess.std(ddof=1)*100:.2f}%   se = {se*100:.3f}%")
print(f"t-stat    = {t:.2f}  (can |t| > 1.96 de co y nghia 95%)")
print(f"CI 95%    = [{(excess.mean()-1.96*se)*100:+.2f}%, {(excess.mean()+1.96*se)*100:+.2f}%]")
print(f"sharpe/ky ~ {excess.mean()/excess.std(ddof=1):+.3f} (khong annualize)")

print("\nPhan bo giao dich theo nam:")
yrs = pd.DataFrame({"year": [r[2] for r in rows], "net": net, "bench": bench})
for y, grp in yrs.groupby("year"):
    print(f"  {y}: n={len(grp):4d}  net TB={grp['net'].mean()*100:+.2f}%  "
          f"vs VNIX={grp['bench'].mean()*100:+.2f}%  win={(grp['net']>0).mean()*100:.0f}%")

print("\nDiem so tren lenh thang vs thua:")
print(f"  lenh THANG (net>0): n={(net>0).sum():4d}  diem TB = {scores[net>0].mean():.2f}")
print(f"  lenh THUA (net<=0): n={(net<=0).sum():4d}  diem TB = {scores[net<=0].mean():.2f}")
print(f"  khac biet diem thang-thua = {scores[net>0].mean() - scores[net<=0].mean():+.2f} diem")
