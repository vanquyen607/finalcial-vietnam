from .base import GoldProvider, ProviderQuote, raw_snapshot_to_quotes
from .composite import MergedProvider
from .mock import MockProvider
from .ngoctham import NgocThamProvider
from .simplize import SimplizeProvider
from .vangtoday import VangTodayProvider

try:  # beautifulsoup4/lxml là tuỳ chọn: thiếu thì bỏ 4 tiệm, app vẫn chạy.
    from .privateshops import PrivateShopsProvider
except ImportError:  # pragma: no cover - phụ thuộc môi trường deploy
    PrivateShopsProvider = None  # type: ignore[assignment]

__all__ = ["GoldProvider", "ProviderQuote", "raw_snapshot_to_quotes",
           "MockProvider", "VangTodayProvider", "SimplizeProvider",
           "NgocThamProvider", "PrivateShopsProvider", "MergedProvider"]
