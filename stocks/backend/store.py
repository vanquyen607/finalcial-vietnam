"""Duong dan, gio Viet Nam, gioi han va cache I/O — dung chung backend."""
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SYM_DIR = DATA / "sym"
NEWS_DIR = DATA / "news"
for _d in (DATA, SYM_DIR, NEWS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SKILL_DATA = ROOT.parent / ".opencode" / "skills" / "vietnam-stock-analysis" / "stock-data"

_VN = ZoneInfo("Asia/Ho_Chi_Minh")
CACHE_TTL = 6 * 3600


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
