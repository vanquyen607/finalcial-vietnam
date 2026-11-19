# -*- coding: utf-8 -*-
"""Ban do nhiet theo nganh + vu tru man loc — dung chung anh chup bang gia.

Nguon du lieu: DATA/board.json do breadth.py ghi moi lan dung do rong
(symbol, san, % thay doi, GTGD). Nganh lay tu industry map cua peers.py
(cache 7 ngay). Ca hai deu la du lieu app da co — module nay khong goi
them API nao, chi doc file cache.
"""
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.peers import _get_industry_map
from backend.store import BASKET, DATA, _cached

_VN = ZoneInfo("Asia/Ho_Chi_Minh")
BOARD_MAX_AGE = 24 * 3600      # vu tru loc / heatmap chap nhan anh chup trong 24h
HEATMAP_STALE = 15 * 60        # qua 15 phut thi danh dau stale (breadth TTL)


def _board_rows(max_age: float = BOARD_MAX_AGE) -> tuple[list, float]:
    obj = _cached(DATA / "board.json")
    if not obj:
        return [], 0.0
    ts = float(obj.get("fetched_at", 0) or 0)
    if time.time() - ts > max_age:
        return [], ts
    return obj.get("rows", []) or [], ts


def group_sectors(rows: list, ind_map: dict) -> list:
    """Gom cac ma theo nganh — ham thuan de unit test.

    % thay doi cua nganh = binh quan gia quyen theo GTGD (ma khop nhieu
    tien anh huong nhieu hon). Chi giu nganh co >= 3 ma co giao dich.
    """
    groups: dict[str, dict] = {}
    for r in rows:
        info = ind_map.get(r.get("s", ""))
        if not info or not info.get("name"):
            continue
        g = groups.setdefault(info["name"], {
            "name": info["name"], "code": info.get("code"),
            "n": 0, "up": 0, "down": 0, "flat": 0,
            "value_t": 0.0, "_wsum": 0.0, "movers": [],
        })
        chg = float(r.get("chg", 0) or 0)
        val = float(r.get("val_t", 0) or 0)
        g["n"] += 1
        g["value_t"] += val
        g["_wsum"] += chg * val
        if chg > 0.05:
            g["up"] += 1
        elif chg < -0.05:
            g["down"] += 1
        else:
            g["flat"] += 1
        g["movers"].append({"symbol": r["s"], "chg": chg, "val_t": val})
    out = []
    for g in groups.values():
        if g["n"] < 3:
            continue
        g["chg"] = round(g["_wsum"] / g["value_t"], 2) if g["value_t"] > 0 else 0.0
        g["value_t"] = round(g["value_t"], 0)
        g["movers"] = sorted(g["movers"], key=lambda m: -abs(m["chg"]))[:5]
        del g["_wsum"]
        out.append(g)
    return sorted(out, key=lambda x: -x["value_t"])


def sector_heatmap() -> dict:
    rows, ts = _board_rows()
    if not rows:
        return {"status": "empty",
                "message": "Chưa có ảnh chụp bảng giá — số liệu sẽ có sau khi độ rộng thị trường được tải."}
    ind_map = _get_industry_map()
    if not ind_map:
        return {"status": "empty", "message": "Đang tải danh mục ngành — thử lại sau ít phút."}
    sectors = group_sectors(rows, ind_map)
    if not sectors:
        return {"status": "empty", "message": "Chưa đủ dữ liệu để vẽ bản đồ ngành."}
    return {
        "status": "ready",
        "sectors": sectors,
        "updated_at": datetime.fromtimestamp(ts, _VN).strftime("%H:%M:%S %d/%m/%Y"),
        "stale": (time.time() - ts) > HEATMAP_STALE,
    }


def screen_universe(limit: int = 150) -> list:
    """Vu tru man loc: BASKET co dinh + top `limit` ma HOSE theo GTGD.

    Anh chup bang gia khong co / qua cu -> chi tra BASKET (hanh vi cu).
    """
    rows, _ = _board_rows()
    hose = sorted((r for r in rows if r.get("ex") == "hose" and float(r.get("val_t", 0) or 0) > 0),
                  key=lambda r: -float(r["val_t"]))
    extra = [r["s"] for r in hose[:limit] if r["s"] not in BASKET]
    return list(BASKET) + extra
