---
name: portfolio-review
description: Đánh giá danh mục đầu tư Việt Nam — hiệu suất, rủi ro, phân bổ, và khuyến nghị tái cơ cấu. Dùng khi user muốn review/đánh giá danh mục, phân bổ tài sản, hoặc tái cơ cấu portfolio.
allowed-tools: mcp__vn-stock-trader__get_portfolio, mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_stock_history, mcp__vn-stock-trader__get_financial_report, mcp__vn-stock-trader__get_sector_peers
---

# Skill: Đánh giá Danh mục (Portfolio Review)

## Mục tiêu
Phân tích toàn diện danh mục đầu tư: hiệu suất vs benchmark, rủi ro tập trung, chất lượng từng vị thế, và action plan.

## Quy trình thực hiện

### Bước 1 — Thu thập dữ liệu danh mục

**Từ user:**
- Danh sách: Symbol | Số lượng CP | Giá mua TB | Ngày mua
- Tổng vốn ban đầu

**Tự động lấy:**
```
mcp__vn-stock-trader__get_portfolio()              → danh mục + P&L hiện tại
for each symbol in portfolio:
    mcp__vn-stock-trader__get_stock_price(symbol)       → giá hiện tại
    mcp__vn-stock-trader__get_stock_history(symbol)     → performance lịch sử
    mcp__vn-stock-trader__get_financial_report(symbol)  → P/E, ROE, EPS
    mcp__vn-stock-trader__get_sector_peers(symbol)      → ngành + peer comparison
```

### Bước 2 — Tính hiệu suất

**Metrics cơ bản:**
```python
current_value = sum(shares × current_price)
total_return = (current_value - cost_basis) / cost_basis × 100
unrealized_pnl = current_value - cost_basis

# Annualized return (nếu biết ngày mua)
days_held = (today - purchase_date).days
annualized_return = (1 + total_return/100)^(365/days_held) - 1
```

**So sánh benchmark:**
- VN-Index return cùng kỳ (lấy từ get_stock_history với symbol="VNINDEX")
- VN30 return cùng kỳ
- Alpha = Portfolio return − VN-Index return

### Bước 3 — Phân tích phân bổ (Allocation)

**Phân bổ theo ngành:**
- Tính % tổng NAV của từng ngành (lấy từ get_sector_peers)
- Flag nếu ngành nào > 30% (rủi ro tập trung)

**Phân bổ theo vốn hoá:**
- Large cap (>10,000 tỷ): bao nhiêu %?
- Mid cap (1,000–10,000 tỷ): bao nhiêu %?
- Small cap (<1,000 tỷ): bao nhiêu %?

**Phân bổ theo risk:**
- Defensive (utilities, food): %?
- Cyclical (banks, BĐS, steel): %?
- Growth (tech, retail): %?

### Bước 4 — Đánh giá từng vị thế

Cho mỗi cổ phiếu:

| Tiêu chí | Tốt | Cần xem lại |
|---------|-----|------------|
| Return vs VN-Index | Outperform | Underperform >10% |
| RSI hiện tại | 35–65 | >75 (quá mua) hoặc <25 |
| Fundamentals | ROE>12%, D/E<1 | ROE suy giảm, nợ tăng |
| Trend | Giá > MA50 | Giá < MA200 |
| Sizing | <20% NAV/vị thế | >25% NAV (quá tập trung) |

### Bước 5 — Đánh giá rủi ro tổng thể

**Risk metrics:**
- **Concentration risk:** Top 3 vị thế chiếm bao nhiêu % NAV?
- **Correlation risk:** Nhiều mã cùng ngành → giảm cùng lúc
- **Beta ước tính:** Cao hơn 1.3 → danh mục biến động mạnh hơn index
- **Margin exposure:** Có vay margin không? Tỷ lệ?

### Bước 6 — Tạo action plan

**Hold:** Fundamentals tốt, định giá hợp lý, trend tích cực
**Add:** Undervalued, pullback về support, catalyst sắp tới
**Reduce:** Đã đạt target, định giá đắt, momentum yếu
**Cut:** Stoploss bị phá, fundamental deterioration, thesis sai

## Format đầu ra

```
📋 ĐÁNH GIÁ DANH MỤC
═══════════════════════════════════════

💼 TỔNG QUAN
• Tổng NAV: X,XXX,XXX,XXX đ
• Lãi/Lỗ: +/- X,XXX,XXX đ (+/-X.X%)
• Alpha vs VN-Index: +/-X.X%
• Số vị thế: X mã

📊 TỪNG VỊ THẾ:
┌────────┬────────┬──────────┬────────┬──────────┬────────┐
│ Mã     │ % NAV  │ Giá mua  │ Hiện tại│ P&L      │ Hành động│
├────────┼────────┼──────────┼────────┼──────────┼────────┤
│ XXX    │ 25%    │ 45,000   │ 52,000 │ +15.6%   │ ✅ Hold│
│ YYY    │ 20%    │ 28,000   │ 24,500 │ -12.5%   │ ⚠️ Review│
│ ZZZ    │ 15%    │ 18,000   │ 22,000 │ +22.2%   │ 🎯 Add  │
└────────┴────────┴──────────┴────────┴──────────┴────────┘

🥧 PHÂN BỔ NGÀNH:
• Ngân hàng: 35% ⚠️ (quá tập trung)
• BĐS: 25%
• Thép: 20%
• Công nghệ: 20%

⚠️ RỦI RO CẦN CHÚ Ý:
1. [Risk 1 với khuyến nghị cụ thể]
2. [Risk 2 với khuyến nghị cụ thể]

📌 ACTION PLAN (ưu tiên)
1. 🔴 [Hành động urgency cao]
2. 🟡 [Hành động medium]
3. 🟢 [Hành động tối ưu hoá]
```

## Lưu ý thị trường Việt Nam

- **T+2 settlement:** Lên kế hoạch rebalancing trước 2 phiên
- **Biên độ HOSE ±7%:** Stoploss phải cân nhắc không thể thực hiện ngay
- **Margin:** Tỷ lệ cho vay thường 50% — tránh leverage quá cao
- **Tax:** Thuế TNCN 0.1% trên mỗi giao dịch bán → tính vào break-even
- **Phí giao dịch:** 0.15–0.35%/lệnh → ảnh hưởng nếu trade quá nhiều
- **Thanh khoản small-cap:** Khó thoát lệnh lớn mà không impact giá
- **Cuối năm:** NAV fund giảm trước tết → sell-off thường xuyên tháng 1
- **VND:** Tỷ giá USD/VND tương đối ổn định nhưng depreciation dài hạn ~3%/năm
