---
name: fundamental-analysis
description: Phân tích cơ bản một mã cổ phiếu Việt Nam — định giá, tài chính, triển vọng ngành. Dùng khi user hỏi về P/E, P/B, ROE, EPS, định giá, BCTC, báo cáo tài chính, hoặc phân tích cơ bản (FA).
argument-hint: "<SYMBOL>"
allowed-tools: mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_financial_report, mcp__vn-stock-trader__get_sector_peers
---

# Skill: Phân tích Cơ bản (Fundamental Analysis)

## Mục tiêu
Đánh giá giá trị nội tại của doanh nghiệp dựa trên tài chính, định giá, và triển vọng. Kết quả: **MUA / GIỮ / BÁN** với luận điểm rõ ràng.

## Quy trình thực hiện

### Bước 1 — Thu thập dữ liệu tài chính
```
mcp__vn-stock-trader__get_stock_price(symbol)       → tên, ngành, vốn hoá, sàn, giá hiện tại
mcp__vn-stock-trader__get_financial_report(symbol)  → BCTC 4 quý, P/E, P/B, ROE, ROA, EPS
mcp__vn-stock-trader__get_sector_peers(symbol)      → P/E ngành, so sánh peers
```

### Bước 2 — Phân tích định giá (Valuation)

| Chỉ số | Mức hấp dẫn | Trung bình VN | Đắt |
|--------|-------------|---------------|-----|
| P/E | < 12x | 12–18x | > 20x |
| P/B | < 1.5x | 1.5–3x | > 4x |
| EV/EBITDA | < 8x | 8–12x | > 15x |
| Dividend Yield | > 5% | 2–4% | < 1% |

**So sánh với ngành:** P/E cổ phiếu / P/E ngành → discount hay premium?

### Bước 3 — Phân tích sức khoẻ tài chính

**Sinh lời:**
- ROE > 15% → tốt | < 10% → kém
- ROA > 8% → hiệu quả tài sản tốt
- Biên lợi nhuận ròng: tăng YoY → tích cực

**Tăng trưởng (4 quý gần nhất so với cùng kỳ):**
- Doanh thu tăng > 10% YoY → tích cực
- LNST tăng > 15% YoY → tích cực
- EPS tăng ổn định → câu chuyện tăng trưởng mạnh

**Nợ & Thanh khoản:**
- D/E < 1.0 → an toàn | > 2.0 → rủi ro (trừ ngân hàng, BĐS)
- Current ratio > 1.5 → thanh khoản tốt
- Nợ xấu (ngân hàng) → NPL < 2% → an toàn

### Bước 4 — Phân tích triển vọng

**Catalyst tiềm năng:**
- Kết quả kinh doanh sắp công bố (KQKD Q/H/Y)
- Dự án mới, hợp đồng lớn
- Chính sách hỗ trợ ngành của Chính phủ
- M&A, cổ đông lớn mua thêm
- Thăng hạng thị trường (FTSE, MSCI)

**Rủi ro cần note:**
- Cổ đông lớn bán ròng liên tục
- Pending audit issues, thay CEO đột ngột
- Ngành đang dưới áp lực regulatory

### Bước 5 — Định giá mục tiêu

**Phương pháp P/E forward:**
```
Target Price = EPS(TTM) × (1 + growth_rate) × Target P/E
```
Dùng P/E target = trung bình P/E ngành × 0.9 (margin of safety).

**Upside/Downside:**
- Upside > 20% → MUA
- Upside 0–20% → GIỮ
- Upside < 0% → BÁN / TRÁNH

## Format đầu ra

```
📊 PHÂN TÍCH CƠ BẢN: [SYMBOL]
═══════════════════════════════════

🏢 TỔNG QUAN
• Ngành: [sector] | Vốn hoá: X,XXX tỷ
• Sàn: HOSE/HNX/UPCOM

💰 ĐỊNH GIÁ
• P/E: Xx (ngành: Xx) → [rẻ/hợp lý/đắt]
• P/B: X.x | ROE: X.x% | EPS TTM: X,XXX đ

📈 TĂNG TRƯỞNG
• Doanh thu YoY: +X% | LNST YoY: +X%
• Xu hướng: [tăng trưởng/ổn định/suy giảm]

🏗️ SỨC KHOẺ TÀI CHÍNH
• D/E: X.x → [an toàn/rủi ro]
• Biên LN ròng: X.x%

🎯 ĐỊNH GIÁ MỤC TIÊU
• Target 12 tháng: XX,XXX đ
• Upside: +X.X%

⚡ CATALYST & RỦI RO
• Catalyst: [list]
• Rủi ro: [list]

📌 KẾT LUẬN: 🟢 MUA / 🟡 GIỮ / 🔴 BÁN
  Lý do: [1–2 câu súc tích]
```

## Lưu ý thị trường Việt Nam

- **BCTC:** Có thể chậm 45 ngày sau quý. Ưu tiên BCTC kiểm toán (chính xác hơn sơ bộ)
- **Ngân hàng:** Dùng P/B và NIM thay P/E; NPL quan trọng hơn D/E thông thường
- **BĐS:** D/E cao là bình thường; chú ý presale revenue và tiến độ bàn giao
- **Bluechips VN30:** Thường được định giá premium 15–20% so với mid/small cap
- **Mùa KQKD:** Q4 công bố tháng 1–2, Q1 tháng 4, Q2 tháng 7, Q3 tháng 10
- **Cổ tức:** Nhiều DN VN trả cổ tức bằng cổ phiếu → pha loãng EPS
- **Foreign room:** Nếu room đầy và ROE cao, định giá thường có premium
