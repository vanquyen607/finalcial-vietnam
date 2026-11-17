"""Test parser cho nguồn phụ: tỷ giá Vietcombank + giá xăng (không gọi mạng)."""
from app.providers.extras import parse_fuel, parse_vcb_fx

VCB_XML = """<ExrateList>
  <DateTime>11/17/2026 12:05:08 PM</DateTime>
  <Exrate CurrencyCode="USD" CurrencyName="US DOLLAR" Buy="25,900.00" Transfer="25,930.00" Sell="26,310.00" />
  <Exrate CurrencyCode="EUR" CurrencyName="EURO" Buy="27,601.48" Transfer="27,880.29" Sell="29,057.60" />
  <Exrate CurrencyCode="DKK" CurrencyName="DANISH KRONE" Buy="-" Transfer="3,719.96" Sell="3,862.33" />
  <Exrate CurrencyCode="JPY" CurrencyName="JAPANESE YEN" Buy="165.10" Transfer="166.77" Sell="172.05" />
</ExrateList>"""

FUEL_HTML = """
<table>
  <tr><th>Xăng/dầu</th><th>Tăng giảm</th><th>Tăng giảm kỳ trước*</th><th>Giá vùng 1</th><th>Giá vùng 2</th></tr>
  <tr><td>Xăng E5 RON 92 Mức 2</td><td>0</td><td>-1,500</td><td>19,390</td><td>19,770</td></tr>
  <tr><td>Xăng E10 RON 95 Mức 3</td><td>-200</td><td>-1,310</td><td>19,840</td><td>20,230</td></tr>
  <tr><td>DO 0,05S Mức 2</td><td>0</td><td>-1,870</td><td>26,820</td><td>27,350</td></tr>
  <tr><td>Mặt hàng lạ</td><td>0</td><td>0</td><td>1,000</td><td>1,100</td></tr>
</table>
<table>
  <tr><th>Xăng/dầu</th><th>Giá</th></tr>
  <tr><td>Xăng E5 RON 92 Mức 2</td><td>99,999</td></tr>
</table>"""


def test_parse_vcb_fx_order_and_values():
    items = parse_vcb_fx(VCB_XML)
    # Chỉ giữ mã trong FX_ORDER, đúng thứ tự ưu tiên (DKK không nằm trong danh sách).
    assert [i["code"] for i in items] == ["USD", "EUR", "JPY"]
    usd = items[0]
    assert usd["buy"] == 25900.0 and usd["sell"] == 26310.0


def test_parse_vcb_fx_dash_is_none():
    xml = VCB_XML.replace('CurrencyCode="DKK"', 'CurrencyCode="THB"')
    items = parse_vcb_fx(xml)
    thb = next(i for i in items if i["code"] == "THB")
    assert thb["buy"] is None and thb["sell"] == 3862.33


def test_parse_fuel_picks_zone_table_and_filters():
    items = parse_fuel(FUEL_HTML)
    assert [i["name"] for i in items] == [
        "Xăng E5 RON 92 Mức 2", "Xăng E10 RON 95 Mức 3", "DO 0,05S Mức 2",
    ]
    e5 = items[0]
    assert e5["zone1"] == 19390.0 and e5["zone2"] == 19770.0 and e5["change"] == 0.0
    assert items[1]["change"] == -200.0


def test_parse_fuel_empty_when_no_table():
    assert parse_fuel("<html><body>không có bảng</body></html>") == []
