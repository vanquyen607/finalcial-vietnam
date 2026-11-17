"""Parser của các nguồn chính chủ mới: Mi Hồng (JSON), BTMH (HTML), WebGia bạc."""
from app.providers.btmh import parse_btmh_gold, parse_btmh_silver
from app.providers.extras import parse_webgia_silver
from app.providers.mihong import parse_mihong

MIHONG_SAMPLE = [
    {"buyingPrice": 13620000, "sellingPrice": 13770000, "code": "SJC",
     "buyChange": 50000, "sellChange": 50000, "dateTime": "17/11/2026 10:08"},
    {"buyingPrice": 9050000, "sellingPrice": 9350000, "code": "750",
     "buyChange": 0, "sellChange": 0, "dateTime": "17/11/2026 10:08"},
    {"buyingPrice": 1, "sellingPrice": 2, "code": "XXX",
     "buyChange": 0, "sellChange": 0, "dateTime": "17/11/2026 10:08"},
]


def test_mihong_chi_to_luong_and_mapping():
    quotes = parse_mihong(MIHONG_SAMPLE, now=0)
    assert [q.code for q in quotes] == ["MH_SJC", "MH_750"]  # mã lạ bị bỏ
    sjc = quotes[0]
    assert sjc.buy == 136_200_000 and sjc.sell == 137_700_000  # theo chỉ x10
    assert sjc.change_buy == 500_000 and sjc.source == "mihong"
    assert sjc.updated_at and sjc.updated_at > 0  # parse được giờ VN


BTMH_HTML = """
<div role="row"><div role="cell">Kim Gia Bảo 24K</div>
  <span class="tabular-nums">99.99</span><span class="tabular-nums">13.350</span>
  <span class="tabular-nums">13.750</span></div>
<div role="row"><div role="cell">Ngân Gia Bảo - Bạc thỏi 5 lượng, 10 lượng (ĐVT: lượng)</div>
  <span class="tabular-nums">99.9</span><span class="tabular-nums">1.460</span>
  <span class="tabular-nums">1.505</span></div>
<div role="row"><div role="cell">Bạc thỏi 1 kg (ĐVT: kg)</div>
  <span class="tabular-nums">99.9</span><span class="tabular-nums">38.934</span>
  <span class="tabular-nums">40.134</span></div>
"""


def test_btmh_gold_nghin_chi_to_luong():
    quotes = parse_btmh_gold(BTMH_HTML, now=123)
    assert len(quotes) == 1
    q = quotes[0]
    assert q.code == "BTMH_9999" and q.buy == 133_500_000 and q.sell == 137_500_000


def test_btmh_silver_luong_and_kg():
    items = parse_btmh_silver(BTMH_HTML)
    assert len(items) == 2
    assert items[0]["buy"] == 1_460_000 and items[0]["sell"] == 1_505_000
    assert items[0]["name"] == "Ngân Gia Bảo - Bạc thỏi 5 lượng, 10 lượng"
    # thỏi kg quy về lượng: 38.934 nghìn/kg -> 1.460.025 đ/lượng
    assert items[1]["buy"] == 1_460_025 and items[1]["sell"] == 1_505_025


WEBGIA_HTML = """
<table>
<tr><th>Sản phẩm</th><th>Mua vào</th><th>Bán ra</th><th>Thay đổi</th><th>Đổi lúc</th></tr>
<tr><td>Bạc 999 (miếng - Thanh - Thỏi) DOJI · đồng/lượng</td>
    <td>1.618.000</td><td>1.698.000</td><td>▲ 16.000</td><td>2 phút trước</td></tr>
<tr><td>Bạc thỏi Phú Quý 999 (1Kilo) Phú Quý · đồng/lượng</td>
    <td>1.461.000</td><td>1.506.000</td><td>▼ 5.000</td><td>9 phút trước</td></tr>
<tr><td>Bạc nguyên liệu Bảo Tín Mạnh Hải · đồng/lượng</td>
    <td>1.300.000</td><td>-</td><td>-</td><td>3 giờ trước</td></tr>
</table>
"""


def test_webgia_silver_parse():
    items = parse_webgia_silver(WEBGIA_HTML)
    assert len(items) == 3
    doji = items[0]
    assert doji["brand"] == "DOJI" and doji["name"] == "Bạc 999 (miếng - Thanh - Thỏi)"
    assert doji["buy"] == 1_618_000 and doji["sell"] == 1_698_000
    assert doji["change"] == 16_000
    assert items[1]["change"] == -5_000
    assert items[2]["sell"] is None and items[2]["change"] is None
