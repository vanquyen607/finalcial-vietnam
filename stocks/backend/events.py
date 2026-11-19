# -*- coding: utf-8 -*-
"""Lich su kien co phieu — CafeF NewsType=2 (GDKHQ, niem yet, phat hanh).

Cache 24h. Trich ngay tu title (format DD.MM.YYYY hoac DD/MM/YYYY).
Canh bao su kien trong 7 ngay toi — mua truoc KQKD/AGM la rui ro su kien.
"""
import json
import re
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

_VN = ZoneInfo("Asia/Ho_Chi_Minh")

ROOT = Path(__file__).resolve().parent.parent
EVENT_DIR = ROOT / "data" / "events"
EVENT_DIR.mkdir(parents=True, exist_ok=True)

TTL = 24 * 3600       # 24h
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

# regex trich ngay tu title CafeF
_DATE_RE = re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{4})")

# keyword phan loai su kien
_CATEGORIES = [
    ("dividend", ["GDKHQ", "cổ tức", "thưởng cổ phiếu", "cổ phiếu thưởng",
                   "tỷ lệ:", "tỷ lệ "]),
    ("listing", ["niêm yết", "đăng ký giao dịch", "UPCOM", "HOSE", "HNX"]),
    ("issuance", ["phát hành", "tăng vốn", "chuyển đổi", "quyền mua"]),
    ("agm", ["đại hội", "AGM", "ĐHCĐ", "đại hội cổ đông"]),
    ("earnings", ["kết quả kinh doanh", "KQKD", "báo cáo tài chính", "BCTC"]),
]

_inflight: set[str] = set()
_inflight_lock = threading.Lock()


def _parse_date(title: str) -> datetime | None:
    m = _DATE_RE.search(title)
    if not m:
        return None
    try:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return datetime(y, mo, d, tzinfo=_VN)
    except ValueError:
        return None


def _classify(title: str) -> str:
    low = title.lower()
    for cat, kws in _CATEGORIES:
        for kw in kws:
            if kw.lower() in low:
                return cat
    return "other"


def _fetch_events(sym: str) -> list[dict]:
    url = f"https://cafef.vn/du-lieu/Ajax/PageNew/News.ashx?symbol={sym.lower()}&NewsType=2"
    r = requests.get(url, headers=UA, timeout=15)
    r.raise_for_status()
    payload = r.json()
    items = []
    for it in (payload.get("Data") or [])[:20]:
        title = (it.get("Title") or "").strip()
        if not title:
            continue
        # loai bo prefix "FPT: "
        clean = re.sub(r"^[A-Z]{2,6}:\s*", "", title)
        ev_date = _parse_date(clean)
        cat = _classify(clean)
        link = (it.get("LinkDetail") or "").split("?")[0]
        if link.startswith("/"):
            link = "https://cafef.vn" + link
        items.append({
            "title": clean,
            "date": ev_date.strftime("%Y-%m-%d") if ev_date else None,
            "category": cat,
            "url": link if link.startswith("http") else None,
        })
    return items


def get_events(sym: str, refresh: bool = False) -> dict:
    sym = sym.upper().strip()
    if not sym.isalpha() or not 2 <= len(sym) <= 6:
        return {"status": "error", "message": "Mã không hợp lệ"}
    path = EVENT_DIR / f"{sym}.json"

    if not refresh and path.exists():
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - obj.get("fetched_at", 0) < TTL:
                return _with_warnings(sym, obj.get("items", []), obj.get("fetched_at"))
        except Exception:
            pass

    try:
        items = _fetch_events(sym)
        obj = {"fetched_at": time.time(), "items": items}
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return _with_warnings(sym, items, obj["fetched_at"])
    except Exception as e:
        if path.exists():
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
                return _with_warnings(sym, obj.get("items", []), obj.get("fetched_at"),
                                      stale=True)
            except Exception:
                pass
        return {"status": "error", "message": f"Lỗi tải sự kiện {sym}: {e}"}


def _with_warnings(sym: str, items: list[dict], fetched_at: float,
                   stale: bool = False) -> dict:
    """Gan canh bao su kien som (7 ngay toi) vao response."""
    today = datetime.now(_VN).date()
    horizon = today + timedelta(days=7)
    upcoming = []
    for it in items:
        if not it.get("date"):
            continue
        try:
            d = datetime.strptime(it["date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= d <= horizon:
            days = (d - today).days
            upcoming.append({**it, "days_from_now": days})

    upcoming.sort(key=lambda x: x.get("days_from_now", 99))
    has_near = any(u["category"] in ("earnings", "agm", "dividend") and
                   u["days_from_now"] <= 3 for u in upcoming)
    return {
        "status": "ready",
        "items": items[:15],
        "upcoming": upcoming,
        "has_near_event": has_near,
        "fetched_at": fetched_at,
        "stale": stale,
    }
