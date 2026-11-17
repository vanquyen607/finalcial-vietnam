from .base import GoldProvider, ProviderQuote, raw_snapshot_to_quotes
from .composite import MergedProvider
from .mihong import MiHongProvider
from .mock import MockProvider
from .ngoctham import NgocThamProvider
from .simplize import SimplizeProvider
from .vangtoday import VangTodayProvider

try:  # beautifulsoup4/lxml là tuỳ chọn: thiếu thì bỏ qua nguồn cần parse HTML.
    from .btmh import BtmhProvider
    from .privateshops import PrivateShopsProvider
except ImportError:  # pragma: no cover - phụ thuộc môi trường deploy
    BtmhProvider = None  # type: ignore[assignment]
    PrivateShopsProvider = None  # type: ignore[assignment]

__all__ = ["GoldProvider", "ProviderQuote", "raw_snapshot_to_quotes",
           "MockProvider", "VangTodayProvider", "SimplizeProvider",
           "NgocThamProvider", "MiHongProvider", "BtmhProvider",
           "PrivateShopsProvider", "MergedProvider"]
