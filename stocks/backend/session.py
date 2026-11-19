"""Gio giao dich Viet Nam + lich nghi le chinh thuc theo thong bao So GDCK.

NGUON:
- TB 2294/TB-SGDHCM (HOSE) ve lich nghi giao dich 2026
- TB 5305/TB-SGDHN (HNX) ve lich nghi giao dich 2026
- Le co dinh ngay am lich 2027 theo phap luat (Tet Am lich CHUA co van ban So — du kien)
"""
from datetime import datetime, time as _time, timedelta

from backend.store import now_vn

# Moc phien (khop is_session): sang 09:15-11:35, chieu 12:55-15:05
_OPEN_AM = _time(9, 15)
_OPEN_PM = _time(12, 55)

MARKET_CLOSED = {
    # -------- 2026 — chinh thuc (HOSE 2294 + HNX 5305) --------
    "2026-01-01",                    # Tet Duong lich
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    # Tet Nguyen dan: 29/12/2025 am den mung 4/1/2026 am
    "2026-04-27",                    # Gio To Hung Vuong (mung 10/3 am — nghi bu)
    "2026-04-30", "2026-05-01",      # Giai phong mien Nam + Quoc te lao dong
    # Quoc khánh: 31/08 la ngay lam bu NHUNG So van khong to chuc giao dich
    "2026-08-31", "2026-09-01", "2026-09-02",
    # -------- 2027 — le co dinh ngay (phap luat) --------
    "2027-01-01",                    # Tet Duong lich (T6)
    "2027-04-16",                    # Gio To Hung Vuong (T6)
    "2027-04-30", "2027-05-01",      # 30/04 (T6) + 01/05 (T7 — le nhung van thuoc cuoi tuan)
    "2027-09-02",                    # Quoc khanh (T5)
    # -------- 2027 — Tet Am lich DU KIEN (mung 1 = 06/02/2027) --------
    # Chua co thong bao cua So — cap nhat lai khi co van ban chinh thuc.
    "2027-02-04", "2027-02-05", "2027-02-08", "2027-02-09",
}


def is_session(now: datetime | None = None) -> bool:
    """Gio giao dich Viet Nam (T2-T6, nghi le theo lich So GDCK).

    Public — main.py + screen.py dung. Co the truyen `now` de test.
    """
    now = now if now is not None else now_vn()
    if now.weekday() >= 5:
        # T7 + CN khong giao dich — ca ngay lam bu vao T7 cung khong (HOSE 2294)
        return False
    if now.strftime("%Y-%m-%d") in MARKET_CLOSED:
        return False
    hm = int(now.strftime("%H%M"))
    return 915 <= hm <= 1135 or 1255 <= hm <= 1505


def _is_trading_day(d) -> bool:
    """T2-T6 va khong nam trong lich nghi le (MARKET_CLOSED)."""
    return d.weekday() < 5 and d.strftime("%Y-%m-%d") not in MARKET_CLOSED


def session_state(now: datetime | None = None) -> str:
    """Trang thai phien: open | pre | lunch | closed | weekend | holiday."""
    now = now if now is not None else now_vn()
    if now.weekday() >= 5:
        return "weekend"
    if now.strftime("%Y-%m-%d") in MARKET_CLOSED:
        return "holiday"
    if is_session(now):
        return "open"
    t = now.time()
    if t < _OPEN_AM:
        return "pre"
    if _time(11, 35) < t < _OPEN_PM:
        return "lunch"
    return "closed"


def next_open(now: datetime | None = None) -> datetime:
    """Thoi diem mo phien ke tiep (09:15 sang hom nay, 12:55 chieu, hoac 09:15
    ngay giao dich ke tiep). Giu nguyen tzinfo cua `now` (Asia/Ho_Chi_Minh)."""
    now = now if now is not None else now_vn()
    d = now.date()
    if _is_trading_day(d):
        t = now.time()
        if t < _OPEN_AM:
            return now.replace(hour=9, minute=15, second=0, microsecond=0)
        if t < _OPEN_PM:  # dang giua phien sang / nghi trua -> mo phien chieu
            return now.replace(hour=12, minute=55, second=0, microsecond=0)
    nd = d + timedelta(days=1)
    while not _is_trading_day(nd):
        nd += timedelta(days=1)
    return now.replace(year=nd.year, month=nd.month, day=nd.day,
                       hour=9, minute=15, second=0, microsecond=0)
