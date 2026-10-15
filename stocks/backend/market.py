"""Façade — giữ nguyên API của market.py cũ sau khi tách thành store/vnrate/calc/session/symbol/overview/breadth.

main.py, fund.py, screen.py và tests import từ đây như trước.
"""
import warnings

warnings.filterwarnings("ignore")

from backend.store import (BASKET, CACHE_TTL, DATA, NEWS_DIR, ROOT, SKILL_DATA, SYM_DIR,
                           _cached, _fresh, _save, now_vn)
from backend.vnrate import GAP, LIMIT_WAIT, paced
from backend.calc import _r, _rsi, _tick, compute, make_entry_zone
from backend.session import MARKET_CLOSED, is_session
from backend.symbol import _quote_history, _seed_symbol, _seeded_cache, get_symbol
from backend.overview import (_build_overview, _index_df, _ma, _ov_lock, _ov_state,
                              _seed_overview, overview)
from backend.breadth import (BREADTH_TTL, _OffHours, _breadth_build, _breadth_lock,
                             _breadth_state, _breadth_symbols, _exchange_bucket, breadth)

__all__ = [
    "BASKET", "CACHE_TTL", "DATA", "NEWS_DIR", "ROOT", "SKILL_DATA", "SYM_DIR",
    "_cached", "_fresh", "_save", "now_vn",
    "GAP", "LIMIT_WAIT", "paced",
    "_r", "_rsi", "_tick", "compute", "make_entry_zone",
    "MARKET_CLOSED", "is_session",
    "_quote_history", "_seed_symbol", "_seeded_cache", "get_symbol",
    "_build_overview", "_index_df", "_ma", "_ov_lock", "_ov_state", "_seed_overview", "overview",
    "BREADTH_TTL", "_OffHours", "_breadth_build", "_breadth_lock", "_breadth_state",
    "_breadth_symbols", "_exchange_bucket", "breadth",
]

# ---------------------------------------------------------------- bootstrap
if _cached(DATA / "overview.json") is None:
    _seed_overview()
