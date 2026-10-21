"""Duong dan, gio Viet Nam, gioi han va cache I/O — dung chung backend."""
import json
import os
import threading
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


# Cache uu tien Postgres (Neon) khi co DATABASE_URL; khong co thi doc/ghi file JSON.
# Van ghi file song song de local/seed chay duoc va lam fallback khi DB loi.
_DB_LOCK = threading.RLock()
_DB = {"conn": None, "fail_at": 0.0, "url": "__unset__"}


def _db_url() -> str | None:
    if _DB["url"] != "__unset__":
        return _DB["url"]
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            p = ROOT.parent / ".env.local"
            for line in p.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s.startswith("DATABASE_URL="):
                    url = s.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        except Exception:
            pass
    _DB["url"] = url or None
    return _DB["url"]


def _db_conn():
    """Connection dung chung; None neu khong cau hinh / dang loi (backoff 60s)."""
    url = _db_url()
    if not url:
        return None
    c = _DB["conn"]
    if c is not None and not getattr(c, "closed", True):
        return c
    if time.time() - _DB["fail_at"] < 60:
        return None
    try:
        import psycopg
        c = psycopg.connect(url, autocommit=True, connect_timeout=10)
        c.execute("CREATE TABLE IF NOT EXISTS cache ("
                  "key text primary key, value jsonb not null, "
                  "updated_at timestamptz not null default now())")
        _DB["conn"] = c
        return c
    except Exception:
        _DB["conn"] = None
        _DB["fail_at"] = time.time()
        return None


def _db_key(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return path.name


def _db_get(key: str):
    """(ok, value): ok=False khi khong co DB/loi -> doc file; ok=True + None = miss."""
    with _DB_LOCK:
        c = _db_conn()
        if c is None:
            return False, None
        try:
            row = c.execute("SELECT value FROM cache WHERE key=%s", (key,)).fetchone()
            if row is None:
                return True, None
            v = row[0]
            return True, (v if isinstance(v, dict) else json.loads(v))
        except Exception:
            _DB["conn"] = None
            _DB["fail_at"] = time.time()
            return False, None


def _db_put(key: str, text: str) -> bool:
    with _DB_LOCK:
        c = _db_conn()
        if c is None:
            return False
        try:
            c.execute("INSERT INTO cache(key,value) VALUES(%s,%s::jsonb) "
                      "ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()",
                      (key, text))
            return True
        except Exception:
            _DB["conn"] = None
            _DB["fail_at"] = time.time()
            return False


def _read_raw(path: Path) -> dict | None:
    ok, val = _db_get(_db_key(path))
    if ok and val is not None:
        return val
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _fresh(path: Path) -> dict | None:
    obj = _read_raw(path)
    if obj and time.time() - obj.get("fetched_at", 0) < CACHE_TTL:
        return obj
    return None


def _cached(path: Path) -> dict | None:
    """Doc cache bat ke het han (khong ghi de du lieu moi hon bang seed)."""
    return _read_raw(path)


def _save(path: Path, obj: dict) -> None:
    text = json.dumps(obj, ensure_ascii=False)
    _db_put(_db_key(path), text)
    try:
        path.write_text(text, encoding="utf-8")
    except Exception:
        pass
