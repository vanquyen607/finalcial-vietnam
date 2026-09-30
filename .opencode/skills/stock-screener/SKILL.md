---
name: stock-screener
description: Lọc cổ phiếu Việt Nam theo tiêu chí tài chính, kỹ thuật, hoặc kết hợp — tìm cơ hội đầu tư. Dùng khi user muốn lọc/tìm cổ phiếu, chạy screener, scan cơ hội, hoặc tìm mã theo điều kiện cụ thể.
argument-hint: "[strategy|criteria]"
allowed-tools: mcp__vn-stock-trader__screen_stocks, mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_financial_report
---

# Skill: Stock Screener (Lọc Cổ phiếu)

## Mục tiêu
Tìm cổ phiếu tiềm năng từ danh sách ~1,700+ mã trên HOSE/HNX/UPCOM theo tiêu chí định sẵn hoặc tuỳ chỉnh.

## Preset Screening Strategies

### 1. 📈 Growth + Quality (Tăng trưởng chất lượng)
```python
criteria = {
    "roe": "> 15",           # ROE > 15%
    "revenue_growth": "> 10", # Tăng trưởng DT YoY > 10%
    "eps_growth": "> 15",     # Tăng trưởng EPS YoY > 15%
    "debt_to_equity": "< 1",  # D/E < 1
    "market_cap": "> 1000",   # Vốn hoá > 1,000 tỷ
    "avg_volume_20d": "> 500000000"  # Thanh khoản > 500 triệu/ngày
}
```

### 2. 💰 Value Play (Định giá thấp)
```python
criteria = {
    "pe": "< 12",            # P/E < 12x
    "pb": "< 1.5",           # P/B < 1.5x
    "roe": "> 12",           # ROE > 12% (không phải rác)
    "dividend_yield": "> 3", # Cổ tức > 3%
    "market_cap": "> 500"    # Vốn hoá > 500 tỷ
}
```

### 3. ⚡ Momentum Breakout (Đà tăng breakout)
```python
criteria = {
    "price_vs_ma20": "> 0",   # Giá > MA20
    "price_vs_ma50": "> 0",   # Giá > MA50
    "rsi_14": "> 50 and < 65",# RSI thoải mái (không quá mua)
    "volume_ratio": "> 1.5",  # Volume/MA20 > 1.5x
    "price_change_20d": "> 5" # Tăng > 5% trong 20 phiên
}
```

### 4. 🏦 Dividend Income (Thu nhập cổ tức)
```python
criteria = {
    "dividend_yield": "> 5",  # Cổ tức > 5%
    "payout_consistency": "3+ years",
    "roe": "> 10",
    "debt_to_equity": "< 1.5",
    "market_cap": "> 1000"
}
```

### 5. 🔄 Recovery Play (Phục hồi)
```python
criteria = {
    "price_vs_52w_high": "< -30",  # Giảm > 30% từ đỉnh 52W
    "roe": "> 10",                  # Nền tảng vẫn tốt
    "rsi_14": "< 40",              # Oversold
    "volume_ratio": "> 1.2",       # Volume bắt đầu tăng
    "pe": "< 15"                   # Định giá hấp dẫn
}
```

## Quy trình thực hiện

### Bước 1 — Xác định strategy & sàn
```
mcp__vn-stock-trader__screen_stocks(criteria, exchange="HOSE|HNX|UPCOM")
→ Trả về danh sách symbols phù hợp (kèm key metrics)
```

### Bước 2 — Filter thanh khoản
**Bắt buộc loại bỏ:**
- Thanh khoản < 200 triệu VND/ngày (không trade được)
- Đang trong diện kiểm soát, cảnh báo, hạn chế
- Có pending litigation / tạm dừng giao dịch

### Bước 3 — Rank & sort

**Scoring system (0–100):**
- Định giá hấp dẫn: 25 điểm
- Tăng trưởng tài chính: 25 điểm
- Chất lượng kinh doanh (ROE, biên LN): 25 điểm
- Momentum kỹ thuật: 25 điểm

### Bước 4 — Phân tích Top 5–10 kết quả
```
mcp__vn-stock-trader__get_stock_price(symbol)      → giá, volume hiện tại
mcp__vn-stock-trader__get_financial_report(symbol) → key metrics
```

## Format đầu ra

```
🔍 KẾT QUẢ SCREENER: [Strategy Name]
═══════════════════════════════════════
Tiêu chí: [list criteria]
Sàn: HOSE/HNX/UPCOM | Tìm thấy: X mã

TOP KẾT QUẢ:
┌─────────┬──────────┬──────┬──────┬──────────┬────────────┬───────┐
│ Symbol  │ Ngành    │ P/E  │ ROE  │ Tăng DT  │ Thanh khoản│ Score │
├─────────┼──────────┼──────┼──────┼──────────┼────────────┼───────┤
│ XXX     │ BĐS      │ 10x  │ 18%  │ +22%     │ 2.5 tỷ     │ 82    │
│ YYY     │ Ngân hàng│ 8x   │ 15%  │ +18%     │ 5.1 tỷ     │ 78    │
└─────────┴──────────┴──────┴──────┴──────────┴────────────┴───────┘

💎 HIGHLIGHT TOP 3:
1. [SYMBOL]: [1–2 câu lý do nổi bật]
2. [SYMBOL]: [1–2 câu lý do nổi bật]
3. [SYMBOL]: [1–2 câu lý do nổi bật]

⚠️ LƯU Ý: Screener là bước lọc sơ bộ.
Cần deep-dive TA + FA trước khi quyết định.
Dùng /analyze [symbol] để phân tích chi tiết.
```

## Lưu ý thị trường Việt Nam

- **~1,700 mã** trên cả 3 sàn nhưng thanh khoản tập trung ở ~200–300 mã
- **VN30:** 30 mã blue chip, chiếm >60% market cap HOSE
- **Penny stocks:** Tránh mã < 5,000 đ/cp (rủi ro thao túng cao)
- **Foreign room:** Mã đầy room ngoại thường được định giá premium
- **Sector rotation VN:** Chu kỳ thường: Ngân hàng → BĐS → Chứng khoán → Công nghiệp
- **Cuối năm:** NH tăng trích lập dự phòng → EPS Q4 thấp giả tạo
