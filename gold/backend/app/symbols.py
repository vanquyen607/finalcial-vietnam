"""Định danh vàng: alias <-> type_code của nguồn dữ liệu + metadata hiển thị.

Đơn vị:
- vàng tâm: VND / 1 lượng (tael = 37,5g)
- XAUUSD: USD / ounce
"""
from __future__ import annotations

from typing import TypedDict


class GoldType(TypedDict):
    code: str          # type_code của nguồn dữ liệu
    name: str          # tên hiển thị đầy đủ
    brand: str         # thương hiệu / nhà bán (khóa gộp nhóm)
    product: str       # tên sản phẩm bên trong thương hiệu ("SJC", "Nhẫn trơn", "Hà Nội"…)
    unit: str          # "VND" | "USD"
    per: str           # "lượng" | "ounce"
    category: str      # "sjc" | "doji" | "pnj" | "world" | "mh" | "pq" | "btmh" | "nt" | "btmc" | "other"
    featured: bool     # hiện ở trang chủ
    alias: str         # alias ổn định trong URL / API


class BrandInfo(TypedDict):
    brand: str         # khóa nhóm, khớp GoldType["brand"]
    label: str         # tên nhà bán hiển thị trên UI
    order: int         # thứ tự nhóm (nhỏ đứng trước); brand lạ = DEFAULT_ORDER


# Thứ tự nhóm trên bảng giá: thế giới trước, rồi các thương hiệu lớn.
BRANDS: list[BrandInfo] = [
    {"brand": "Spot", "label": "Vàng thế giới", "order": 0},
    {"brand": "SJC", "label": "SJC", "order": 1},
    {"brand": "DOJI", "label": "DOJI", "order": 2},
    {"brand": "PNJ", "label": "PNJ", "order": 3},
    {"brand": "BTMC", "label": "Bảo Tín Minh Châu", "order": 4},
    {"brand": "VietinBank", "label": "VietinBank", "order": 5},
    {"brand": "Mi Hồng", "label": "Mi Hồng", "order": 6},
    {"brand": "Phú Quý", "label": "Phú Quý", "order": 7},
    {"brand": "BTMH", "label": "Bảo Tín Mạnh Hải", "order": 8},
    {"brand": "Ngọc Thẩm", "label": "Ngọc Thẩm", "order": 9},
]

BRAND_BY_KEY: dict[str, BrandInfo] = {b["brand"]: b for b in BRANDS}
# brand không có trong bảng trên (thêm mới chưa kịp khai báo) -> xếp cuối.
DEFAULT_ORDER = 1000


def brand_order(brand: str) -> int:
    info = BRAND_BY_KEY.get(brand)
    return info["order"] if info else DEFAULT_ORDER


def brand_label(brand: str) -> str:
    info = BRAND_BY_KEY.get(brand)
    return info["label"] if info else brand


# type_code thực tế trả về bởi vang.today/api/prices?action=current
GOLD_TYPES: list[GoldType] = [
    {"code": "SJL1L10", "name": "SJC 9999", "brand": "SJC", "product": "Miếng 9999",
     "unit": "VND", "per": "lượng",
     "category": "sjc", "featured": True, "alias": "sjc"},
    {"code": "SJ9999", "name": "SJC nhẫn trơn", "brand": "SJC", "product": "Nhẫn trơn",
     "unit": "VND", "per": "lượng",
     "category": "sjc", "featured": True, "alias": "sjc-ring"},
    {"code": "VNGSJC", "name": "Vàng SJC", "brand": "SJC", "product": "Vàng SJC",
     "unit": "VND", "per": "lượng",
     "category": "sjc", "featured": False, "alias": "vn-gold-sjc"},
    {"code": "DOHNL", "name": "DOJI Hà Nội", "brand": "DOJI", "product": "Hà Nội",
     "unit": "VND", "per": "lượng",
     "category": "doji", "featured": True, "alias": "doji-hn"},
    {"code": "DOHCML", "name": "DOJI TP.HCM", "brand": "DOJI", "product": "TP.HCM",
     "unit": "VND", "per": "lượng",
     "category": "doji", "featured": True, "alias": "doji-hcm"},
    {"code": "DOJINHTV", "name": "DOJI trang sức", "brand": "DOJI", "product": "Trang sức",
     "unit": "VND", "per": "lượng",
     "category": "doji", "featured": False, "alias": "doji-jewelry"},
    {"code": "PQHNVM", "name": "PNJ Hà Nội", "brand": "PNJ", "product": "Hà Nội",
     "unit": "VND", "per": "lượng",
     "category": "pnj", "featured": True, "alias": "pnj-hn"},
    {"code": "PQHN24NTT", "name": "PNJ 24K", "brand": "PNJ", "product": "24K",
     "unit": "VND", "per": "lượng",
     "category": "pnj", "featured": True, "alias": "pnj-24k"},
    {"code": "BTSJC", "name": "Bảo Tín Minh Châu SJC", "brand": "BTMC", "product": "SJC",
     "unit": "VND", "per": "lượng",
     "category": "btmc", "featured": False, "alias": "btmc-sjc"},
    {"code": "BT9999NTT", "name": "Bảo Tín Minh Châu 9999", "brand": "BTMC", "product": "9999",
     "unit": "VND", "per": "lượng",
     "category": "btmc", "featured": False, "alias": "btmc-9999"},
    {"code": "VIETTINMSJC", "name": "VietinBank SJC", "brand": "VietinBank", "product": "SJC",
     "unit": "VND", "per": "lượng",
     "category": "other", "featured": False, "alias": "viettin-sjc"},
    {"code": "XAUUSD", "name": "Giá vàng thế giới", "brand": "Spot", "product": "Spot",
     "unit": "USD", "per": "ounce",
     "category": "world", "featured": True, "alias": "xauusd"},
    # Nguồn phụ: Simplize (tổng hợp) — giá niêm yết theo ngày của từng cửa hàng.
    {"code": "MH_SJC", "name": "Mi Hồng SJC", "brand": "Mi Hồng", "product": "SJC",
     "unit": "VND", "per": "lượng",
     "category": "mh", "featured": False, "alias": "mh-sjc"},
    {"code": "MH_9999", "name": "Mi Hồng 999", "brand": "Mi Hồng", "product": "999",
     "unit": "VND", "per": "lượng",
     "category": "mh", "featured": False, "alias": "mh-9999"},
    {"code": "BTMH_9999", "name": "Bảo Tín Mạnh Hải 9999", "brand": "BTMH", "product": "9999",
     "unit": "VND", "per": "lượng",
     "category": "btmh", "featured": False, "alias": "btmh-9999"},
    {"code": "PQ_SJC", "name": "Phú Quý SJC", "brand": "Phú Quý", "product": "SJC",
     "unit": "VND", "per": "lượng",
     "category": "pq", "featured": False, "alias": "pq-sjc"},
    {"code": "PQ_9999", "name": "Phú Quý 9999", "brand": "Phú Quý", "product": "9999",
     "unit": "VND", "per": "lượng",
     "category": "pq", "featured": False, "alias": "pq-9999"},
    # Nguồn chính chủ: Ngọc Thẩm (ngoctham.com/ajax/proxy_banggia.php).
    {"code": "NT_9999", "name": "Ngọc Thẩm 9999", "brand": "Ngọc Thẩm", "product": "9999",
     "unit": "VND", "per": "lượng",
     "category": "nt", "featured": False, "alias": "nt-9999"},
    {"code": "NT_SJC", "name": "Ngọc Thẩm SJC", "brand": "Ngọc Thẩm", "product": "SJC",
     "unit": "VND", "per": "lượng",
     "category": "nt", "featured": False, "alias": "nt-sjc"},
]

BY_CODE: dict[str, GoldType] = {t["code"]: t for t in GOLD_TYPES}
BY_ALIAS: dict[str, GoldType] = {t["alias"]: t for t in GOLD_TYPES}


def featured_types() -> list[GoldType]:
    return [t for t in GOLD_TYPES if t["featured"]]


def brand_groups(featured: bool = False) -> list[dict]:
    """Gộp vàng theo nhà bán, sắp theo BRANDS.order.

    Trả về [{brand, label, order, count, items}] — count/items tính theo GOLD_TYPES
    (metadata), không theo quote đang có giá.
    """
    types = featured_types() if featured else GOLD_TYPES
    buckets: dict[str, list[GoldType]] = {}
    for t in types:
        buckets.setdefault(t["brand"], []).append(t)

    groups: list[dict] = []
    for brand, items in buckets.items():
        info = BRAND_BY_KEY.get(brand)
        groups.append({
            "brand": brand,
            "label": info["label"] if info else brand,
            "order": info["order"] if info else DEFAULT_ORDER,
            "count": len(items),
            "items": items,
        })
    groups.sort(key=lambda g: (g["order"], g["label"]))
    return groups


def resolve(ref: str) -> GoldType | None:
    """Nhận type_code hoặc alias, trả về GoldType."""
    if ref in BY_CODE:
        return BY_CODE[ref]
    return BY_ALIAS.get(ref.lower())
