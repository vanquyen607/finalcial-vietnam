"""Nguồn phụ ngoài vàng: bạc thế giới, tỷ giá Vietcombank, giá xăng dầu.

Ba nguồn đều công khai, không cần API key:
- Bạc spot: TradingView scanner (cùng hạ tầng với vàng spot ở spot.py),
  dự phòng gold-api.com.
- Tỷ giá: XML chính thức của Vietcombank (mua / chuyển khoản / bán).
  Vietcombank ghi rõ "mỗi 5 phút chỉ gọi 1 lần" -> service cache 30 phút.
- Xăng dầu: bảng giá bán lẻ Petrolimex trên giaxanghomnay.com
  (HTML tĩnh, parse bằng BeautifulSoup như privateshops.py).
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup

from .btmh import parse_btmh_silver, vn_num

log = logging.getLogger("aurum.extras")

HEADERS = {"User-Agent": "Mozilla/5.0 (AurumTerminal/1.0)", "Accept": "application/json, text/xml, text/html"}

SILVER_SCANNER = "https://scanner.tradingview.com/symbol"
SILVER_SYMBOLS = ["TVC:SILVER", "OANDA:XAGUSD", "FX:XAGUSD"]
SILVER_FALLBACK = "https://api.gold-api.com/price/XAG"

VCB_FX_URL = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
# Thứ tự hiển thị ưu tiên trên UI; mã nào Vietcombank không có thì bỏ qua.
FX_ORDER = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "SGD", "CNY", "HKD", "KRW", "THB"]

FUEL_URL = "https://giaxanghomnay.com/"
# Chỉ lấy các mặt hàng chính cho gọn UI.
FUEL_KEYS = ["E5 RON 92", "RON 95 Mức 3", "RON 95 Mức 5", "DO 0,05S", "DO 0,001S", "Dầu hỏa"]


# ---------- bạc thế giới ----------
async def fetch_silver(client: httpx.AsyncClient) -> dict | None:
    """Giá bạc spot: {price_usd, change_usd, source} hoặc None nếu mọi nguồn chết."""
    for symbol in SILVER_SYMBOLS:
        try:
            resp = await client.get(
                SILVER_SCANNER,
                params={"symbol": symbol, "fields": "close,change_abs"},
                headers=HEADERS, timeout=8.0,
            )
            resp.raise_for_status()
            data = resp.json()
            price = float(data.get("close") or 0)
            if price > 0:
                return {"price_usd": price, "change_usd": float(data.get("change_abs") or 0),
                        "source": "TradingView"}
        except Exception as exc:  # noqa: BLE001 - nguồn phụ lỗi là bình thường
            log.debug("silver %s lỗi: %s", symbol, exc)

    try:
        resp = await client.get(SILVER_FALLBACK, headers=HEADERS, timeout=8.0)
        resp.raise_for_status()
        price = float(resp.json().get("price") or 0)
        if price > 0:
            return {"price_usd": price, "change_usd": 0.0, "source": "gold-api"}
    except Exception as exc:  # noqa: BLE001
        log.debug("silver gold-api lỗi: %s", exc)
    return None


# ---------- tỷ giá Vietcombank ----------
def _vnd(text: str | None) -> float | None:
    """'16,917.04' -> 16917.04; '-' / rỗng -> None."""
    if not text or text.strip() in ("", "-"):
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def parse_vcb_fx(xml_text: str) -> list[dict]:
    """Parse XML tỷ giá Vietcombank, trả danh sách theo thứ tự FX_ORDER."""
    root = ET.fromstring(xml_text)
    by_code = {}
    for node in root.iter("Exrate"):
        code = (node.get("CurrencyCode") or "").strip()
        if not code:
            continue
        by_code[code] = {
            "code": code,
            "name": (node.get("CurrencyName") or "").strip(),
            "buy": _vnd(node.get("Buy")),
            "transfer": _vnd(node.get("Transfer")),
            "sell": _vnd(node.get("Sell")),
        }
    return [by_code[c] for c in FX_ORDER if c in by_code]


async def fetch_fx(client: httpx.AsyncClient) -> list[dict] | None:
    try:
        resp = await client.get(VCB_FX_URL, headers=HEADERS, timeout=10.0)
        resp.raise_for_status()
        items = parse_vcb_fx(resp.text)
        return items or None
    except Exception as exc:  # noqa: BLE001
        log.debug("vcb fx lỗi: %s", exc)
        return None


# ---------- giá xăng dầu ----------
def _num(text: str) -> float | None:
    """'19,390' / '-1,500' -> số đồng; '0' -> 0.0; rác -> None."""
    m = re.search(r"-?[\d][\d.,]*", text or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "").replace(".", ""))
    except ValueError:
        return None


def parse_fuel(html: str) -> list[dict]:
    """Bảng Petrolimex trên giaxanghomnay: cột [mặt hàng, thay đổi, ..., giá vùng 1, giá vùng 2]."""
    soup = BeautifulSoup(html, "lxml")
    for table in soup.find_all("table"):
        head = table.get_text(" ", strip=True)
        if "Giá vùng 1" not in head:
            continue
        items = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) < 4 or not any(k in cells[0] for k in FUEL_KEYS):
                continue
            zone1, zone2 = _num(cells[-2]), _num(cells[-1])
            if zone1 is None:
                continue
            items.append({"name": cells[0], "change": _num(cells[1]) or 0.0,
                          "zone1": zone1, "zone2": zone2})
        if items:
            return items
    return []


async def fetch_fuel(client: httpx.AsyncClient) -> list[dict] | None:
    try:
        resp = await client.get(FUEL_URL, headers=HEADERS, timeout=12.0)
        resp.raise_for_status()
        items = parse_fuel(resp.text)
        return items or None
    except Exception as exc:  # noqa: BLE001
        log.debug("fuel lỗi: %s", exc)
        return None


# ---------- bạc trong nước ----------
WEBGIA_SILVER_URL = "https://webgia.tv/gia-bac"
BTMH_BOARD_URL = "https://baotinmanhhai.vn/bang-gia-vang"
SILVER_BRANDS = ["DOJI", "Bảo Tín Minh Châu", "Phú Quý", "Bảo Tín Mạnh Hải", "Kim Ngân Phúc"]
SILVER_PER_BRAND = 2  # mỗi hãng lấy tối đa 2 sản phẩm tiêu biểu cho gọn bảng


def _silver_change(text: str) -> float | None:
    """'▲ 16.000' -> 16000; '▼ 3.000' -> -3000; '±0' -> 0; '-' -> None."""
    text = (text or "").strip()
    if not text or text == "-":
        return None
    if text.startswith("±"):
        return 0.0
    value = vn_num(re.sub(r"[^\d.,-]", "", text))
    if value is None:
        return None
    return -value if text.startswith("▼") else value


def parse_webgia_silver(html: str) -> list[dict]:
    """Bảng giá bạc webgia: {'brand','name','buy','sell','change'} theo đồng/lượng."""
    soup = BeautifulSoup(html, "lxml")
    items: list[dict] = []
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) < 4 or cells[0] == "Sản phẩm":
                continue
            label = cells[0].split("·")[0].strip()  # 'Tên SP BRAND'
            brand = next((b for b in SILVER_BRANDS if label.endswith(b)), "")
            if not brand:
                continue
            buy, sell = vn_num(cells[1]), vn_num(cells[2])
            if buy is None and sell is None:
                continue
            name = label[: -len(brand)].strip()
            letters = [c for c in name if c.isalpha()]
            if letters and sum(c.isupper() for c in letters) / len(letters) > 0.8:
                name = name.title()  # dòng viết hoa gần như toàn bộ -> chuẩn hoá
            items.append({"brand": brand, "name": name,
                          "buy": buy, "sell": sell,
                          "change": _silver_change(cells[3]), "source": "webgia"})
    return items


async def fetch_silver_domestic(client: httpx.AsyncClient) -> list[dict] | None:
    """Bảng bạc trong nước: webgia (tổng hợp) + BTMH lấy trực tiếp từ hãng.

    Dòng BTMH của webgia bị loại để nhường bản chính chủ; mỗi hãng tối đa
    SILVER_PER_BRAND sản phẩm. Một nguồn chết thì nguồn còn lại vẫn trả.
    """
    items: list[dict] = []
    try:
        resp = await client.get(WEBGIA_SILVER_URL, headers=HEADERS, timeout=12.0)
        resp.raise_for_status()
        seen: dict[str, int] = {}
        for row in parse_webgia_silver(resp.text):
            if row["brand"] == "Bảo Tín Mạnh Hải":
                continue
            if seen.get(row["brand"], 0) >= SILVER_PER_BRAND:
                continue
            seen[row["brand"]] = seen.get(row["brand"], 0) + 1
            items.append(row)
    except Exception as exc:  # noqa: BLE001
        log.debug("webgia bạc lỗi: %s", exc)
    try:
        resp = await client.get(BTMH_BOARD_URL, headers=HEADERS, timeout=12.0)
        resp.raise_for_status()
        for row in parse_btmh_silver(resp.text):
            items.append({**row, "brand": "Bảo Tín Mạnh Hải", "source": "btmh"})
    except Exception as exc:  # noqa: BLE001
        log.debug("btmh bạc lỗi: %s", exc)
    return items or None
