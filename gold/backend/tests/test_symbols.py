from __future__ import annotations

from app.symbols import (
    BRANDS,
    BY_ALIAS,
    BY_CODE,
    DEFAULT_ORDER,
    GOLD_TYPES,
    brand_groups,
    brand_label,
    brand_order,
)


def test_every_type_has_brand_product_and_alias():
    for t in GOLD_TYPES:
        assert t["brand"], t["code"]
        assert t["product"], t["code"]
        assert t["name"], t["code"]
        assert t["alias"], t["code"]
    assert len(BY_CODE) == len(GOLD_TYPES)
    assert len(BY_ALIAS) == len(GOLD_TYPES)


def test_brand_order_world_first_and_unknown_last():
    assert brand_order("Spot") == 0
    assert brand_order("SJC") < brand_order("DOJI") < brand_order("PNJ")
    assert brand_order("Mi Hồng") < brand_order("Ngọc Thẩm")
    assert brand_order("brand-chua-khai-bao") == DEFAULT_ORDER
    assert brand_label("brand-chua-khai-bao") == "brand-chua-khai-bao"
    assert brand_label("BTMH") == "Bảo Tín Mạnh Hải"


def test_brand_groups_are_ordered_and_covers_all_types():
    groups = brand_groups()
    orders = [g["order"] for g in groups]
    assert orders == sorted(orders), "nhóm phải xếp theo BRANDS.order tăng dần"
    # mọi mã vàng đều rơi vào đúng một nhóm
    assert sum(g["count"] for g in groups) == len(GOLD_TYPES)
    labels = [g["label"] for g in groups]
    assert labels[0] == "Vàng thế giới"
    assert "SJC" in labels and "Ngọc Thẩm" in labels
    # tổng số nhóm = số brand duy nhất trong GOLD_TYPES
    assert len(groups) == len({t["brand"] for t in GOLD_TYPES})
    assert len({t["brand"] for t in GOLD_TYPES}) == len(BRANDS)


def test_brand_groups_featured_smaller():
    featured = brand_groups(featured=True)
    assert sum(g["count"] for g in featured) < sum(g["count"] for g in brand_groups())
    assert featured[0]["label"] == "Vàng thế giới"
