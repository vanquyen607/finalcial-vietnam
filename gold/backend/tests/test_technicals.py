"""Test parser chỉ số kỹ thuật TradingView (payload thật ghi lại 17/11/2026)."""
from app.providers.technicals import parse_technicals, rating_of

RAW = {
    "name": "XAUUSD",
    "close": 3877.685,
    "change": 0.5488,
    "Recommend.All": -0.3545,
    "Recommend.MA": -0.4,
    "Recommend.Other": -0.3091,
    "Recommend.All|60": 0.1121,
    "Recommend.MA|60": 0.1333,
    "Recommend.Other|60": 0.0909,
    "Recommend.All|240": -0.3121,
    "Recommend.MA|240": -0.2667,
    "Recommend.Other|240": -0.3636,
}


def test_parse_frames():
    out = parse_technicals(RAW)
    assert out is not None
    assert out["symbol"] == "OANDA:XAUUSD"
    assert out["close"] == 3877.685
    d = out["frames"]["1D"]
    assert d["all"] == -0.3545 and d["rating"] == "sell" and d["label"] == "Bán"
    h1 = out["frames"]["60"]
    assert h1["all"] == 0.1121 and h1["rating"] == "buy"
    assert out["frames"]["240"]["label"] == "Bán"


def test_parse_missing_frames_skipped():
    out = parse_technicals({"Recommend.All|60": 0.6})
    assert out is not None
    assert list(out["frames"]) == ["60"]
    assert out["frames"]["60"]["rating"] == "strong_buy"
    assert out["frames"]["60"]["ma"] is None


def test_parse_empty_returns_none():
    assert parse_technicals({}) is None
    assert parse_technicals({"close": 1.0}) is None


def test_rating_bands():
    assert rating_of(-1.0)[0] == "strong_sell"
    assert rating_of(-0.5)[0] == "strong_sell"
    assert rating_of(-0.49)[0] == "sell"
    assert rating_of(-0.1)[0] == "neutral"
    assert rating_of(0.0)[0] == "neutral"
    assert rating_of(0.1)[0] == "neutral"
    assert rating_of(0.11)[0] == "buy"
    assert rating_of(0.5)[0] == "strong_buy"
    assert rating_of(1.0)[0] == "strong_buy"
