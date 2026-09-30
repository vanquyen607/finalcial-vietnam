---
name: news-impact
description: Phân tích tác động tin tức lên cổ phiếu Việt Nam — sentiment, catalyst, rủi ro sự kiện. Dùng khi user hỏi về tin tức, news, sự kiện sắp tới, catalyst, hoặc sentiment của một mã cụ thể.
argument-hint: "<SYMBOL>"
allowed-tools: mcp__vn-stock-trader__get_news, WebSearch, WebFetch
---

# Skill: Phân tích Tác động Tin tức (News Impact Analysis)

## Mục tiêu
Đánh giá nhanh mức độ ảnh hưởng của tin tức/sự kiện lên giá cổ phiếu. Kết quả: **mức độ tác động + hướng + thời gian hiệu lực**.

## Quy trình thực hiện

### Bước 1 — Thu thập tin tức
```
mcp__vn-stock-trader__get_news(symbol, limit=10)   → tin liên quan mã cụ thể
mcp__vn-stock-trader__get_news(limit=30)            → tin thị trường tổng hợp + vĩ mô
WebSearch("site:cafef.vn OR vietstock.vn {symbol} tin tức")  → bổ sung từ web
WebFetch(url)                                        → đọc chi tiết bài viết quan trọng
```

> **Lưu ý:** MCP server không có `get_company_events` hay `get_market_news` riêng.
> Dùng `get_news` với/không có symbol để lấy tin thị trường và tin doanh nghiệp.

### Bước 2 — Phân loại tin tức

**Cấp độ tác động:**

| Cấp | Loại tin | Ví dụ | Thời gian hiệu lực |
|-----|---------|-------|-------------------|
| 🔴 Cao | Corporate action | KQKD vượt/hụt kỳ vọng >20%, M&A, huỷ niêm yết | 1–5 phiên |
| 🟠 Trung-cao | Fundamental change | Hợp đồng lớn, thay CEO, nâng/hạ room ngoại | 3–10 phiên |
| 🟡 Trung bình | Sector news | Chính sách ngành, regulatory, giá nguyên liệu | 1–3 phiên |
| 🟢 Thấp | Macro/General | Fed rates, USD/VND, GDP tổng | < 1 phiên |

### Bước 3 — Đánh giá sentiment (-5 đến +5)

| Điểm | Ý nghĩa |
|------|---------|
| +4 đến +5 | Rất tích cực — thường gap up |
| +2 đến +3 | Tích cực — kỳ vọng tăng |
| -1 đến +1 | Trung tính — chờ xác nhận |
| -2 đến -3 | Tiêu cực — áp lực bán |
| -4 đến -5 | Rất tiêu cực — nguy cơ giảm mạnh |

**Từ khoá phân tích:**
- Tích cực: "vượt kỳ vọng", "tăng trưởng", "ký kết hợp đồng", "nâng hạng"
- Tiêu cực: "hụt kỳ vọng", "vi phạm", "điều tra", "phong toả tài sản"
- Trung tính: "kế hoạch", "dự kiến", "có thể"

### Bước 4 — Thị trường đã phản ánh chưa?

**Price action check:**
- Giá tăng trước tin → market đã biết → phản ứng yếu hơn
- Giá chưa động → surprise → phản ứng mạnh
- Tin kém nhưng giá không giảm → lực cầu tốt

**Volume check:**
- Volume tăng đột biến ngày tin → xác nhận mạnh
- Volume bình thường → thị trường thờ ơ

### Bước 5 — Dự báo phản ứng giá

**Market awareness factor:**
- Tin bất ngờ (0 signal trước): ×1.5
- Tin đã được đồn đoán: ×0.7
- Tin trong mùa KQKD (market expects): ×0.8

## Format đầu ra

```
📰 PHÂN TÍCH TIN TỨC: [SYMBOL]
═══════════════════════════════════

📋 TIN TỨC CHÍNH (7 ngày)
1. [Tiêu đề] — [Nguồn] — [Ngày]
   → Tác động: 🔴/🟠/🟡/🟢 | Sentiment: +X/-X
2. ...

📊 ĐÁNH GIÁ TỔNG HỢP
• Sentiment score: X/5 (Tích cực/Trung tính/Tiêu cực)
• Cấp độ tác động: Cao/Trung/Thấp
• Market đã phản ánh: Có/Chưa/Một phần

⚡ SỰ KIỆN SẮP TỚI
• [Ngày]: [Sự kiện] → Kỳ vọng: [+/-]

📈 DỰ BÁO NGẮN HẠN
• Xu hướng: Tăng/Giảm/Sideways (1–3 phiên)
• Vùng quan sát: [giá kỳ vọng nếu tin tích cực/tiêu cực]

⚠️ RỦI RO SỰ KIỆN
• [List các sự kiện sắp tới có thể gây biến động]

📌 KẾT LUẬN NHANH
  [2–3 câu tóm tắt actionable]
```

## Lưu ý thị trường Việt Nam

- **Nguồn tin đáng tin cậy:** CafeF, VietStock, HOSE/HNX website, SSC (Uỷ ban CKNN), NDH
- **Thông tin nội bộ (insider):** Phổ biến hơn market developed — giá thường tăng trước tin
- **ĐHCĐ thường niên:** Tháng 3–4. Nghị quyết ĐHCĐ ảnh hưởng lớn đến kế hoạch cổ tức, phát hành
- **Giao dịch cổ đông nội bộ:** Bắt buộc công bố trong 3 ngày — signal quan trọng
- **Cổ tức tiền mặt:** Ngày GDKHQ giảm đúng mức cổ tức — không phải "giảm thật"
- **Phát hành thêm (rights issue):** Thường pha loãng EPS ngắn hạn — giá điều chỉnh
- **Margin call:** Khi index giảm mạnh, stocks bị margin call giảm vô lý → cơ hội
