"""Định danh vàng: alias <-> type_code của nguồn dữ liệu + metadata hiển thị.

Đơn vị:
-vang tâm: VND / 1 lượng (tael = 37,5g)
- XAUUSD: USD / ounce
"""
from __future__ import annotations

from typing import TypedDict


class GoldType(TypedDict):
    code: str          # type_code của nguồn dữ liệu
    name: str          # tên hiển thị
    brand: str         # thương hiệu
    unit: str          # "VND" | "USD"
    per: str           # "lượng" | "ounce"
    category: str      # "sjc" | "doji" | "pnj" | "world" | "other"
    featured: bool     # hiện ở trang chủ
    alias: str         # alias ổn định trong URL / API


# type_code thực tế trả về bởi vang.today/api/prices?action=current
GOLD_TYPES: list[GoldType] = [
    {"code": "SJL1L10", "name": "SJC 9999", "brand": "SJC", "unit": "VND", "per": "lượng",
     "category": "sjc", "featured": True, "alias": "sjc"},
    {"code": "SJ9999", "name": "SJC nhẫn trơn", "brand": "SJC", "unit": "VND", "per": "lượng",
     "category": "sjc", "featured": True, "alias": "sjc-ring"},
    {"code": "VNGSJC", "name": "Vàng SJC", "brand": "SJC", "unit": "VND", "per": "lượng",
     "category": "sjc", "featured": False, "alias": "vn-gold-sjc"},
    {"code": "DOHNL", "name": "DOJI Hà Nội", "brand": "DOJI", "unit": "VND", "per": "lượng",
     "category": "doji", "featured": True, "alias": "doji-hn"},
    {"code": "DOHCML", "name": "DOJI TP.HCM", "brand": "DOJI", "unit": "VND", "per": "lượng",
     "category": "doji", "featured": True, "alias": "doji-hcm"},
    {"code": "DOJINHTV", "name": "DOJI trang sức", "brand": "DOJI", "unit": "VND", "per": "lượng",
     "category": "doji", "featured": False, "alias": "doji-jewelry"},
    {"code": "PQHNVM", "name": "PNJ Hà Nội", "brand": "PNJ", "unit": "VND", "per": "lượng",
     "category": "pnj", "featured": True, "alias": "pnj-hn"},
    {"code": "PQHN24NTT", "name": "PNJ 24K", "brand": "PNJ", "unit": "VND", "per": "lượng",
     "category": "pnj", "featured": True, "alias": "pnj-24k"},
    {"code": "BTSJC", "name": "Bảo Tín Minh Châu SJC", "brand": "BTMC", "unit": "VND", "per": "lượng",
     "category": "other", "featured": False, "alias": "btmc-sjc"},
    {"code": "BT9999NTT", "name": "Bảo Tín Minh Châu 9999", "brand": "BTMC", "unit": "VND", "per": "lượng",
     "category": "other", "featured": False, "alias": "btmc-9999"},
    {"code": "VIETTINMSJC", "name": "VietinBank SJC", "brand": "VietinBank", "unit": "VND", "per": "lượng",
     "category": "other", "featured": False, "alias": "viettin-sjc"},
    {"code": "XAUUSD", "name": "Giá vàng thế giới", "brand": "Spot", "unit": "USD", "per": "ounce",
     "category": "world", "featured": True, "alias": "xauusd"},
]

BY_CODE: dict[str, GoldType] = {t["code"]: t for t in GOLD_TYPES}
BY_ALIAS: dict[str, GoldType] = {t["alias"]: t for t in GOLD_TYPES}


def featured_types() -> list[GoldType]:
    return [t for t in GOLD_TYPES if t["featured"]]


def resolve(ref: str) -> GoldType | None:
    """Nhận type_code hoặc alias, trả về GoldType."""
    if ref in BY_CODE:
        return BY_CODE[ref]
    return BY_ALIAS.get(ref.lower())
