# -*- coding: utf-8 -*-
"""Cham diem cam xuc tin tuc CafeF — keyword-based.

Tin tuc title + sub deu duoc cham. Khong dung model ML (qua nang, can API key).
Ket qua: sentiment (-1..+1), tags: catalyst / risk / earnings / dividend / merger.
Cache theo symbol 24h (chung TTL voi news.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- keyword lists (lowercase) ---
# Tang gia tri (positive)
_POS = [
    "tăng trưởng", "tăng cao", "tăng ", "lợi nhuận tăng", "doanh thu tăng",
    "lợi nhuận kỷ lục", "doanh thu kỷ lục", "doanh thu cao nhất",
    "phân phối cổ tức", "cổ tức", "cổ phiếu thưởng", "thưởng cổ phiếu",
    "mua lại cổ phiếu", "tự mua", "bảo lãnh", "hợp đồng lớn", "ký hợp đồng",
    "thắng thầu", "trúng thầu", "phê duyệt", "chấp thuận", "cấp phép",
    "niêm yết mới", "thăng hạng", "thanh khoản cao", "dòng tiền dương",
    "biên lợi nhuận cải thiện", "tăng vốn", "phát hành riêng lẻ",
    "đối tác chiến lược", "thỏa thuận hợp tác", "thương vụ", "thuê bao tăng",
    "sản lượng tăng", "khách hàng mới", "thị phần tăng", "dẫn đầu",
    "vượt kế hoạch", "vượt mục tiêu", "quý tốt nhất", "năm tốt nhất",
    "lập đỉnh", "cổ phiếu tăng", "giá mục tiêu", "khuyến nghị mua",
    "tái cấu trúc thành công", "thanh toán cổ tức", "lãi cơ bản trên cổ phiếu",
    "mua thêm", "thanh lý", "thuê bao", "hợp đồng xuất khẩu", "xuất khẩu tăng",
    "biên lợi nhuận", "tăng vọt", "tăng mạnh", "tăng đột biến", "bứt phá",
    "tăng tốc", "phục hồi", "khởi sắc", "tích cực", "tích cực hóa",
    "kỷ lục", "đỉnh", "cao nhất", "lợi nhuận sau thuế tăng",
]
# Gia tri (negative)
_NEG = [
    "lỗ", "sụt giảm", "giảm mạnh", "giảm sâu", "giảm ", "thua lỗ", "âm lợi nhuận",
    "doanh thu giảm", "lợi nhuận giảm", "suy giảm", "khó khăn", "khủng hoảng",
    "pháp lý", "kiểm toán", "trích lập", "bị phạt", "xử phạt", "vi phạm",
    "khởi kiện", "tố cáo", "thưa kiện", "bồi thường", "tranh chấp",
    "nợ xấu", "nợ khó đòi", "tỷ lệ nợ", "đòn bẩy cao", "mất thanh khoản",
    "cắt giảm", "đóng cửa", "ngừng hoạt động", "thanh lý tài sản",
    "phát hành cổ phiếu giảm", "pha loãng", "bán tháo", "bán cắt lỗ",
    "giảm chỉ số", "rút khỏi", "hủy bỏ", "hoãn", "trì hoãn",
    "cảnh báo", "cảnh báo rủi ro", "thẩm định", "đánh giá thấp",
    "hạ xếp hạng", "báo động", "kém", "yếu kém", "suy thoái",
    "thất bại", "không đạt", "bỏ lỡ", "lãi suất tăng", "áp lực",
    "âm tiền", "lỗ ròng", "sụt", "mất ", "suy", "kém hiệu quả",
    "phản ánh tiêu cực", "báo động", "rủi ro cao", "kiện",
]
# Catalyst — su kien co the tao dot bien gia
_CAT = [
    "báo cáo tài chính", "bctc", "kết quả kinh doanh", "kqkd",
    "đại hội đồng cổ đông", "đhđcđ", "agm", "thông qua",
    "chia cổ tức", "cổ tức", "phát hành", "tăng vốn",
    "niêm yết", "chuyển sàn", "upcom", "delisting",
    "thâu tóm", "mua lại", "sáp nhập", "merger", "thương vụ",
    "hợp đồng lớn", "dự án lớn", "thầu lớn", "đầu tư",
    "chính sách", "nghị định", "thông tư", "quyết định",
    "cổ phiếu quỹ", "mua lại cổ phiếu", "tự mua",
    "lộ trình", "kế hoạch", "mục tiêu", "trọng tâm",
]
# Risk — canh bao rui ro
_RISK = [
    "rủi ro", "cảnh báo", "kiểm toán viên", "điều kiện", "phụ thuộc",
    "đòn bẩy", "nợ vay", "áp lực tài chính", "thanh khoản",
    "biến động", "tranh chấp", "kiện tụng", "vi phạm",
    "phạt", "trích lập", "hao mòn", "mất giá", "tỷ giá",
    "thị trường suy", "cạnh tranh", "thay đổi quản lý", "nghỉ hưu",
    "bê bối", "tai tiếng", "phản ánh", "khiếu nại",
]

_POS_RE = re.compile("|".join(re.escape(k) for k in _POS), re.IGNORECASE)
_NEG_RE = re.compile("|".join(re.escape(k) for k in _NEG), re.IGNORECASE)
_CAT_RE = re.compile("|".join(re.escape(k) for k in _CAT), re.IGNORECASE)
_RISK_RE = re.compile("|".join(re.escape(k) for k in _RISK), re.IGNORECASE)

# bo qua tin quan he (khong phai su kien doanh nghiep)
_SKIP = [
    "người nổi tiếng", "sao", "showbiz", "bóng đá", "thể thao",
    "thời tiết", "du lịch", "ăn uống", "phim", "âm nhạc",
]


@dataclass
class SentimentResult:
    score: float = 0.0          # -1..+1
    tags: list[str] = field(default_factory=list)
    matched_pos: list[str] = field(default_factory=list)
    matched_neg: list[str] = field(default_factory=list)
    matched_cat: list[str] = field(default_factory=list)
    matched_risk: list[str] = field(default_factory=list)


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def analyze_text(text: str) -> SentimentResult:
    """Cham cam xuc 1 chuoi title+sub."""
    r = SentimentResult()
    if not text:
        return r
    low = text.lower()

    # skip tin quan he
    for s in _SKIP:
        if s in low:
            r.tags.append("skip")
            return r

    pos_hits = _POS_RE.findall(low)
    neg_hits = _NEG_RE.findall(low)
    cat_hits = _CAT_RE.findall(low)
    risk_hits = _RISK_RE.findall(low)

    r.matched_pos = list(dict.fromkeys(pos_hits))[:5]
    r.matched_neg = list(dict.fromkeys(neg_hits))[:5]
    r.matched_cat = list(dict.fromkeys(cat_hits))[:3]
    r.matched_risk = list(dict.fromkeys(risk_hits))[:3]

    # score = (pos - neg) / (pos + neg + 1)
    raw = (len(pos_hits) - len(neg_hits)) / (len(pos_hits) + len(neg_hits) + 1)
    r.score = round(_clamp(raw), 2)

    # tags
    if r.matched_cat:
        r.tags.append("catalyst")
    if r.matched_risk:
        r.tags.append("risk")
    if r.score > 0.15:
        r.tags.append("positive")
    elif r.score < -0.15:
        r.tags.append("negative")
    else:
        r.tags.append("neutral")
    return r


def analyze_news_item(item: dict) -> dict:
    """Cham cam xuc 1 tin CafeF (title + sub)."""
    text = f"{item.get('title', '')} {item.get('sub', '')}".strip()
    res = analyze_text(text)
    return {
        **item,
        "sentiment": res.score,
        "sent_tags": res.tags,
        "sent_cat": res.matched_cat[:2],
    }


def tag_news_list(items: list[dict]) -> list[dict]:
    """Danh sach tin CafeF -> gan sentiment tags."""
    return [analyze_news_item(it) for it in items]
