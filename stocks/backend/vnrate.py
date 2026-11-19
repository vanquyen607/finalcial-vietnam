"""Cham phit goi vnstock — GAP, retry rate limit, uu tien live.

Day la choke point duy nhat tiep can API vnstock co pace (trong market.py cu).
"""
import contextlib
import io
import threading
import time

GAP = 7.5          # giay giua 2 lan go vnstock (guest 20 req/phut ~ 2 req/ma)
LIMIT_WAIT = 62     # cho khi bi rate limit

_lock = threading.Lock()
_next_slot = 0.0
_live_count = 0        # so yeu cau live dang cho slot (uu tien hon quet man)


def _live_enter():
    global _live_count
    with _lock:
        _live_count += 1


def _live_exit():
    global _live_count
    with _lock:
        _live_count = max(0, _live_count - 1)


def paced(fn, *args, priority: bool = False, **kwargs):
    """Goi vnstock da cham phit, tu xu ly rate limit.

    priority=True (live: chi so + ma dang mo) se cho phep di truoc cac
    yeu cau quet man de khong bi doi 5 phut.
    """
    global _next_slot
    last_err = None
    if priority:
        _live_enter()
    else:
        while _live_count > 0:
            time.sleep(0.3)
    try:
        for attempt in range(3):
            with _lock:
                now = time.time()
                wait = max(0.0, _next_slot - now)
                _next_slot = max(now, _next_slot) + GAP
            if wait:
                time.sleep(wait)
            try:
                buf = io.StringIO()
                err = io.StringIO()
                # chan ca stdout/stderr — vnstock in chuoi Viet Nam, console
                # Windows cp1252 se nem UnicodeEncodeError neu khong bat UTF-8
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                    return fn(*args, **kwargs)
            except BaseException as e:  # noqa: BLE001 - vnstock raised SystemExit on rate limit
                last_err = e
                msg = str(e)
                limited = isinstance(e, SystemExit) or "rate" in msg.lower() or "Rate Limit" in msg or "giới hạn" in msg
                if limited and attempt < 2:
                    with _lock:
                        _next_slot = max(_next_slot, time.time() + LIMIT_WAIT)
                    time.sleep(LIMIT_WAIT)
                    continue
                # SystemExit (vnstock rate limit) khong duoc thoat ra ngoai —
                # no la BaseException nen moi handler `except Exception` deu bo qua
                # va uvicorn se chet. Doi thanh loi thuong truoc khi nem.
                if isinstance(last_err, SystemExit):
                    raise RuntimeError(f"vnstock rate limit: {last_err}") from last_err
                raise last_err
    finally:
        if priority:
            _live_exit()
