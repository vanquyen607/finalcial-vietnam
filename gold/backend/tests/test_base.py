from __future__ import annotations

from app.providers.base import ProviderQuote, raw_snapshot_to_quotes


def test_raw_snapshot_maps_known_codes_only():
    rows = [
        {"type_code": "SJL1L10", "buy": 144_600_000, "sell": 147_600_000,
         "change_buy": 100_000, "change_sell": 200_000},
        {"type_code": "KHONG_CO", "buy": 1, "sell": 2},
        {"type_code": "XAUUSD", "buy": 4173.4, "sell": 0},
    ]
    quotes = raw_snapshot_to_quotes(rows, source="vangtoday", updated_at=1_790_740_809)

    assert [q.code for q in quotes] == ["SJL1L10", "XAUUSD"]
    sjc = quotes[0]
    assert (sjc.buy, sjc.sell) == (144_600_000, 147_600_000)
    assert (sjc.change_buy, sjc.change_sell) == (100_000, 200_000)
    assert (sjc.unit, sjc.per, sjc.source) == ("VND", "lượng", "vangtoday")
    assert sjc.updated_at == 1_790_740_809

    xau = quotes[1]
    assert (xau.unit, xau.per) == ("USD", "ounce")
    assert xau.sell == 0


def test_raw_snapshot_float_coercion():
    quotes = raw_snapshot_to_quotes(
        [{"type_code": "SJL1L10", "buy": "144600000", "sell": None}], source="x"
    )
    assert quotes[0].buy == 144_600_000.0
    assert quotes[0].sell == 0.0


def test_mid_property():
    both = ProviderQuote(code="A", name="A", buy=100, sell=110, change_buy=0,
                         change_sell=0, unit="VND", per="lượng", source="t")
    assert both.mid == 105

    only_buy = ProviderQuote(code="B", name="B", buy=4173.4, sell=0, change_buy=0,
                             change_sell=0, unit="USD", per="ounce", source="t")
    assert only_buy.mid == 4173.4
