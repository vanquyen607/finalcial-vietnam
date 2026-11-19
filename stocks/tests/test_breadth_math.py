# -*- coding: utf-8 -*-
"""Test breadth aggregation voi fake board (server dang truoc gio mo cua)."""
import os, sys
from pathlib import Path
os.environ["VNSTOCK_DISABLE_AGENT_SETUP"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd

import vnstock
from backend import breadth as br


class FakeTrading:
    def __init__(self, **kw):
        pass

    def price_board(self, syms, **kw):
        rows = [
            # symbol, exchange, last, ref, value, fbv, fsv
            ("VCB", "HSX", 57000, 56700, 1.2e12, 5e10, 2e10),   # up, fnet +30 ty
            ("HPG", "HSX", 20100, 20700, 2.0e12, 1e10, 4e10),   # down, fnet -30 ty
            ("FPT", "HSX", 57100, 57100, 1.0e12, 0, 0),          # flat
            ("VND", "HSX", 0, 15000, 0, 0, 0),                   # halted -> flat (match=0)
            ("REE", "HNX", 25000, 24000, 3e11, 2e10, 1e10),      # up
            ("ABC", "UPCOM", 5000, 5500, 1e11, 0, 1e10),         # down
        ]
        data = [r for r in rows if r[0] in syms]
        cols = pd.MultiIndex.from_tuples([
            ("listing", "symbol"), ("listing", "exchange"),
            ("match", "match_price"), ("match", "reference_price"),
            ("match", "accumulated_value"),
            ("match", "foreign_buy_value"), ("match", "foreign_sell_value"),
        ])
        df = pd.DataFrame([list(r) for r in data], columns=cols)
        return df


br.paced = lambda fn, *a, **k: fn(*a, **k)   # bo qua sleep
filler = [f"X{str(i).zfill(3)}" for i in range(94)]   # vuot nguong 100 ma
br._breadth_symbols = lambda: {
    "hose": ["VCB", "HPG", "FPT", "VND"] + filler, "hnx": ["REE"], "upcom": ["ABC"]}
vnstock.Trading = FakeTrading

out = br._breadth_build()
import json
print(json.dumps(out, ensure_ascii=False, indent=1))
ex = out["exchanges"]
assert ex["hose"]["up"] == 1 and ex["hose"]["down"] == 1 and ex["hose"]["flat"] == 2, ex["hose"]
assert ex["hnx"]["up"] == 1 and ex["hnx"]["flat"] == 0, ex["hnx"]
assert ex["upcom"]["down"] == 1, ex["upcom"]
assert abs(ex["hose"]["fnet_t"] - 0.0) < 0.01, ex["hose"]["fnet_t"]   # +30 (VCB) -30 (HPG)
assert abs(ex["hnx"]["fnet_t"] - 10.0) < 0.01, ex["hnx"]["fnet_t"]
assert abs(ex["upcom"]["fnet_t"] - (-10.0)) < 0.01, ex["upcom"]["fnet_t"]
assert abs(ex["hose"]["value_t"] - 4200) < 1, ex["hose"]["value_t"]
assert out["total"]["up"] == 2 and out["total"]["down"] == 2 and out["total"]["flat"] == 2
print("BREADTH MATH OK")

# test OffHours: match_price = 0 het -> raise _OffHours
def zero_board(syms, **kw):
    cols = pd.MultiIndex.from_tuples([
        ("listing", "symbol"), ("listing", "exchange"),
        ("match", "match_price"), ("match", "reference_price"),
        ("match", "accumulated_value"),
        ("match", "foreign_buy_value"), ("match", "foreign_sell_value"),
    ])
    return pd.DataFrame([["VCB", "HSX", 0, 56700, 0, 0, 0]], columns=cols)
FakeTrading.price_board = staticmethod(zero_board)
try:
    br._breadth_build()
    print("FAIL: khong raise _OffHours")
except br._OffHours:
    print("OFFHOURS OK")
