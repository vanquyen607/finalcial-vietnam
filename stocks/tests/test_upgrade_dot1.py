# -*- coding: utf-8 -*-
"""Unit test nang cap dot 1 — Bollinger (calc), heatmap nganh + vu tru man loc (sectors).

Khong go API, chay trong vai giay. Phong cach theo tests/test_calc.py.
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ["VNSTOCK_DISABLE_AGENT_SETUP"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from backend import sectors
from backend.calc import compute

fails = []


def check(name, cond, extra=""):
    if cond:
        print(f"  OK  {name}")
    else:
        fails.append(name)
        print(f"FAIL  {name} {extra}")


# ---------------------------------------------------------------- compute + Bollinger
print("== compute: Bollinger Bands ==")
rng = np.random.default_rng(7)
n = 260
close = 50 + np.cumsum(rng.normal(0.05, 0.8, n))
close = np.maximum(close, 5)
idx = pd.bdate_range("2025-01-02", periods=n)
df = pd.DataFrame({
    "Open": close * 0.999, "High": close * 1.01,
    "Low": close * 0.99, "Close": close,
    "Volume": rng.integers(100_000, 5_000_000, n),
}, index=idx)

res = compute("TST", df)
check("compute tra ket qua", res is not None)
check("co du truong bb", all(k in res for k in ("bb_upper", "bb_lower", "bb_mid", "bb_pctb")), str(res.keys()))
check("bb_lower < bb_mid < bb_upper", res["bb_lower"] < res["bb_mid"] < res["bb_upper"],
      f'{res["bb_lower"]} {res["bb_mid"]} {res["bb_upper"]}')
mid = (res["bb_upper"] + res["bb_lower"]) / 2
check("bb_mid = trung binh 2 dai", abs(mid - res["bb_mid"]) < 0.02, mid)
pctb_expect = (res["close"] - res["bb_lower"]) / (res["bb_upper"] - res["bb_lower"])
check("bb_pctb nhat quan", abs(pctb_expect - res["bb_pctb"]) < 0.02, f"{pctb_expect} vs {res['bb_pctb']}")
check("max_score = 14 (them +1 Bollinger)", res["max_score"] == 14, res["max_score"])
check("score trong [-11, max_score]", -11 <= res["score"] <= res["max_score"], res["score"])
check("narrative nhac Bollinger", "Bollinger" in res["narrative"])

# doi chieu thu cong: SMA20 + 2*std mau (ddof=1) cua 20 phien cuoi
tail = df["Close"].tail(20)
sd = float(tail.std())
check("bb_upper khop tinh tay", abs(res["bb_upper"] - (float(tail.mean()) + 2 * sd)) < 0.05,
      f'{res["bb_upper"]} vs {float(tail.mean()) + 2 * sd}')

# ---------------------------------------------------------------- group_sectors
print("== sectors.group_sectors ==")
ind = {
    "AAA": {"code": "1", "name": "Ngan hang"},
    "BBB": {"code": "1", "name": "Ngan hang"},
    "CCC": {"code": "1", "name": "Ngan hang"},
    "XXX": {"code": "2", "name": "Thep"},
    "YYY": {"code": "2", "name": "Thep"},
}
rows = [
    {"s": "AAA", "ex": "hose", "chg": 2.0, "val_t": 100.0, "last": 10},
    {"s": "BBB", "ex": "hose", "chg": -1.0, "val_t": 300.0, "last": 20},
    {"s": "CCC", "ex": "hose", "chg": 0.0, "val_t": 100.0, "last": 30},
    {"s": "XXX", "ex": "hose", "chg": 5.0, "val_t": 50.0, "last": 40},
    {"s": "YYY", "ex": "hose", "chg": 5.0, "val_t": 50.0, "last": 50},
    {"s": "ZZZ", "ex": "hose", "chg": 9.0, "val_t": 999.0, "last": 60},   # khong co nganh -> bo
]
gs = sectors.group_sectors(rows, ind)
check("nganh <3 ma bi loai (Thep con 2 ma)", len(gs) == 1, str([g["name"] for g in gs]))
g = gs[0]
check("ten nganh dung", g["name"] == "Ngan hang")
check("dem up/down/flat", (g["up"], g["down"], g["flat"]) == (1, 1, 1), str(g))
check("GTGD cong don", g["value_t"] == 500, g["value_t"])
# (2*100 + -1*300 + 0*100) / 500 = -0.2
check("chg gia quyen GTGD", abs(g["chg"] - (-0.2)) < 1e-9, g["chg"])
check("movers toi da 5, sap theo |chg|", [m["symbol"] for m in g["movers"]] == ["AAA", "BBB", "CCC"])

# ---------------------------------------------------------------- screen_universe + heatmap rong
print("== sectors.screen_universe / sector_heatmap ==")
tmp = Path(tempfile.mkdtemp())
old_data = sectors.DATA
try:
    sectors.DATA = tmp
    check("khong board.json -> chi BASKET", sectors.screen_universe() == list(sectors.BASKET))
    check("khong board.json -> heatmap empty", sectors.sector_heatmap()["status"] == "empty")

    board = {"fetched_at": time.time(), "rows": [
        {"s": "HPG", "ex": "hose", "chg": 1.0, "val_t": 900.0, "last": 27},   # da trong BASKET
        {"s": "SHB", "ex": "hose", "chg": 1.0, "val_t": 800.0, "last": 15},
        {"s": "VIB", "ex": "hose", "chg": 1.0, "val_t": 700.0, "last": 19},
        {"s": "EIB", "ex": "hose", "chg": 1.0, "val_t": 0.0, "last": 20},     # GTGD 0 -> loai
        {"s": "HUT", "ex": "hnx", "chg": 1.0, "val_t": 9999.0, "last": 9},    # HNX -> khong vao vu tru HOSE
    ]}
    (tmp / "board.json").write_text(json.dumps(board), encoding="utf-8")
    # Ngu nghia: top `limit` HOSE theo GTGD, gop voi BASKET (ma da co trong
    # BASKET khong tinh lai) — tong vu tru ~ limit ma thanh khoan cao nhat.
    uni = sectors.screen_universe(limit=2)   # top2 HOSE = HPG (da co) + SHB
    check("universe = BASKET + top HOSE", uni[:len(sectors.BASKET)] == list(sectors.BASKET)
          and uni[len(sectors.BASKET):] == ["SHB"], str(uni[len(sectors.BASKET):]))
    uni3 = sectors.screen_universe(limit=3)  # top3 = HPG + SHB + VIB
    check("limit=3 them VIB", uni3[len(sectors.BASKET):] == ["SHB", "VIB"],
          str(uni3[len(sectors.BASKET):]))
finally:
    sectors.DATA = old_data

print()
if fails:
    print(f"FAILED: {len(fails)} — {fails}")
    sys.exit(1)
print("ALL PASS")
