# -*- coding: utf-8 -*-
"""Unit test toan phan tich (calc) + lich nghi (session) — khong go API, chay trong <5s."""
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ["VNSTOCK_DISABLE_AGENT_SETUP"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from backend.calc import _r, _tick, compute, make_entry_zone, to_dong
from backend.session import MARKET_CLOSED, is_session

fails = []


def check(name, cond, extra=""):
    if cond:
        print(f"  OK  {name}")
    else:
        fails.append(name)
        print(f"FAIL  {name} {extra}")


# ---------------------------------------------------------------- _tick / _r
print("== _tick / _r ==")
check("tick <20 = 0.1", _tick(19.9) == 0.1)
check("tick 20 = 0.2", _tick(20.0) == 0.2)
check("tick 49.9 = 0.2", _tick(49.9) == 0.2)
check("tick 50 = 0.5", _tick(50.0) == 0.5)
check("tick 99.9 = 0.5", _tick(99.9) == 0.5)
check("tick 100 = 1.0", _tick(100.0) == 1.0)
check("round 12.345 -> 12.3", _r(12.345) == 12.3)
check("round 18.76 -> 18.8", _r(18.76) == 18.8)
check("round 25.07 -> 25.0", _r(25.07) == 25.0)
check("round 76.31 -> 76.5", _r(76.31) == 76.5)
check("round 132.4 -> 132.0", _r(132.4) == 132.0)

# ---------------------------------------------------------------- to_dong
print("== to_dong ==")
tri = pd.Series([400_000.0, 100_000.0, 0.0, 250_000.0])   # trieu dong
out = to_dong(tri)
check("trieu -> dong x1e6", abs(out.iloc[0] - 4e11) < 1, out.iloc[0])
dong = pd.Series([1.2e12, 8e11, 0.0])                     # da la dong
check("dong giu nguyen", to_dong(dong).iloc[0] == 1.2e12)
check("toan 0 khong nhan", to_dong(pd.Series([0.0, 0.0])).iloc[0] == 0.0)

# ---------------------------------------------------------------- entry zone
print("== make_entry_zone ==")


def zone(last, sup, res, ma20, rsi, score):
    return make_entry_zone(last, sup, res, ma20, rsi, score)


e, note = zone(25.0, 24.0, 28.0, 25.5, 55, 8)
check("normal: tang dan", e[0] < e[1], e)
check("normal: khong vuot gia", e[1] <= 25.0, e)

e2, note2 = zone(25.0, 24.0, 25.3, 25.5, 55, 8)   # res/last-1 = 1.2% <= 3%
check("near_res: tang dan", e2[0] < e2[1], e2)

e3, note3 = zone(25.0, 24.0, 30.0, 25.5, 76, 8)
check("rsi>70: ghi qua mua", "quá mua" in note3, note3)
check("rsi>70: tang dan", e3[0] < e3[1], e3)

e4, note4 = zone(25.0, 24.0, 30.0, 25.5, 55, -3)
check("score<0: ghi KHONG mua", "KHÔNG mua" in note4, note4)

# vung khong the bang nhau sau khi fix (entry[0] < entry[1] luon)
rng = np.random.default_rng(7)
bad = 0
for _ in range(2000):
    last = float(rng.uniform(5, 500))
    sup = float(last * rng.uniform(0.85, 1.0))
    res = float(last * rng.uniform(1.0, 1.3))
    ma20 = float(last * rng.uniform(0.85, 1.15))
    rsi = float(rng.uniform(20, 90))
    score = int(rng.integers(-8, 14))
    ee, _ = zone(last, sup, res, ma20, rsi, score)
    if not (ee[0] < ee[1] and ee[0] > 0):
        bad += 1
check("fuzz 2000: tang dan + >0", bad == 0, f"bad={bad}")

# ---------------------------------------------------------------- compute
print("== compute (synthetic OHLCV) ==")


def synth(n=300, drift=0.001, seed=3):
    r = np.random.default_rng(seed)
    px = 25.0 + r.normal(0, 0.05, n).cumsum() * 0.3 + np.arange(n) * drift * 25
    px = np.maximum(px, 1.0)
    df = pd.DataFrame({
        "Open": px * (1 + r.normal(0, 0.004, n)),
        "High": px * (1 + abs(r.normal(0, 0.006, n))),
        "Low": px * (1 - abs(r.normal(0, 0.006, n))),
        "Close": px,
        "Volume": r.integers(500_000, 5_000_000, n).astype(float),
    }, index=pd.bdate_range("2025-06-02", periods=n))
    return df


d = synth()
res = compute("TEST", d)
check("compute khong None", res is not None)
if res:
    check("entry tang dan", res["entry"][0] < res["entry"][1], res["entry"])
    check("stop < gia", 0 < res["stop"] < res["close"], res["stop"])
    check("t1 > gia", res["t1"] > res["close"], res["t1"])
    check("score hop le", -11 <= res["score"] <= res["max_score"], res["score"])
    check("rsi hop le", 0 <= res["rsi"] <= 100, res["rsi"])
    check("verdict khop tone", bool(res["verdict"]) and res["tone"] in ("good", "watch", "neutral", "bad"))
    check("ohlcv 300 bar", len(res["ohlcv"]) == 300, len(res["ohlcv"]))
    check("khong NaN trong JSON", pd.notna(res["ma20"]) and pd.notna(res["vol_ratio"]))

res_short = compute("TEST", synth(n=50))
check("du lieu <60 phien -> None", res_short is None)

res_zero = synth(n=300)
res_zero["Close"] = 0.0
check("gia 0 -> None", compute("TEST", res_zero) is None)

# ---------------------------------------------------------------- is_session
print("== is_session ==")
# 2026-10-15 = Thu, 2026-10-17 = Sat, 2026-10-18 = Sun
check("T5 10:00 = True", is_session(datetime(2026, 10, 15, 10, 0)) is True)
check("T5 14:30 = True", is_session(datetime(2026, 10, 15, 14, 30)) is True)
check("T5 12:00 = False (nghi trua)", is_session(datetime(2026, 10, 15, 12, 0)) is False)
check("T5 8:00 = False", is_session(datetime(2026, 10, 15, 8, 0)) is False)
check("T5 15:30 = False", is_session(datetime(2026, 10, 15, 15, 30)) is False)
check("T7 10:00 = False (khong giao dich)", is_session(datetime(2026, 10, 17, 10, 0)) is False)
check("T7 9:20 = False", is_session(datetime(2026, 10, 17, 9, 20)) is False)
check("CN = False", is_session(datetime(2026, 10, 18, 10, 0)) is False)
check("01/01/2026 le Duong = False", is_session(datetime(2026, 1, 1, 10, 0)) is False)
check("17/02/2026 Tet = False", is_session(datetime(2026, 2, 17, 10, 0)) is False)
check("18/02/2026 Tet = False", is_session(datetime(2026, 2, 18, 14, 0)) is False)
check("27/04/2026 Hung Vuong = False", is_session(datetime(2026, 4, 27, 10, 0)) is False)
check("31/08/2026 lam bu QK = False", is_session(datetime(2026, 8, 31, 10, 0)) is False)
check("02/09/2026 QK = False", is_session(datetime(2026, 9, 2, 10, 0)) is False)
check("04/02/2027 Tet du kien = False", is_session(datetime(2027, 2, 4, 10, 0)) is False)
check("T6 16/10/2026 10:00 = True", is_session(datetime(2026, 10, 16, 10, 0)) is True)
check("2026 khong co ngay T7 trong nghi le", not any(
    datetime.fromisoformat(d).weekday() >= 5 for d in MARKET_CLOSED if d.startswith("2026")))

# ---------------------------------------------------------------- ket qua
print()
if fails:
    print(f"TOTAL FAIL: {len(fails)} -> {fails}")
    sys.exit(1)
print("TEST_CALC OK — all assertions passed")
