---
name: technical-analysis
description: Phân tích kỹ thuật một mã cổ phiếu Việt Nam — xu hướng, momentum, tín hiệu mua/bán. Dùng khi user hỏi về chart, RSI, MACD, support/resistance, hỗ trợ, kháng cự, hoặc tín hiệu mua/bán kỹ thuật.
argument-hint: "<SYMBOL>"
allowed-tools: mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_stock_history
---

# Skill: Phân tích Kỹ thuật (Technical Analysis)

## Mục tiêu
Phân tích xu hướng giá, momentum, và tín hiệu mua/bán dựa trên OHLCV. Kết quả phải **actionable**: có điểm vào, stoploss, target cụ thể.

## Quy trình thực hiện

### Bước 1 — Thu thập dữ liệu
```
mcp__vn-stock-trader__get_stock_price(symbol)                   → giá hiện tại, volume, tham chiếu, trần/sàn
mcp__vn-stock-trader__get_stock_history(symbol, period="1y")    → OHLCV 1 năm (đủ tính MA200)
```

### Bước 2 — Tính chỉ báo kỹ thuật

| Chỉ báo | Tham số | Ý nghĩa |
|---------|---------|---------|
| MA20 | SMA 20 phiên | Xu hướng ngắn hạn |
| MA50 | SMA 50 phiên | Xu hướng trung hạn |
| MA200 | SMA 200 phiên | Xu hướng dài hạn |
| RSI | 14 phiên | Quá mua (>70) / Quá bán (<30) |
| MACD | EMA12/EMA26, Signal EMA9 | Momentum, divergence |
| Bollinger Bands | SMA20, ±2σ | Biến động, breakout |
| Volume MA20 | TB 20 phiên | So sánh volume hiện tại |
| ATR | 14 phiên | Biến động thực — dùng tính stoploss |

### Bước 3 — Xác định xu hướng

**Trend analysis:**
- Giá > MA20 > MA50 > MA200 → **Uptrend mạnh**
- Giá < MA20 < MA50 < MA200 → **Downtrend mạnh**
- Các MA đan xen → Sideways / Chuyển xu hướng

**Support/Resistance** (6–12 tháng gần nhất):
- Swing high → kháng cự
- Swing low → hỗ trợ
- Vùng congestion → S/R mạnh

**Pattern:** Golden Cross (MA20 cắt MA50), Death Cross, Breakout, False Breakout.

### Bước 4 — Đánh giá tín hiệu tổng hợp

Chấm điểm 6 tín hiệu (+1 Tích cực / 0 Trung tính / -1 Tiêu cực):

| # | Tín hiệu | Tích cực | Tiêu cực |
|---|---------|---------|---------|
| 1 | Trend | Giá > MA20 > MA50 | Giá < MA20 < MA50 |
| 2 | RSI | 35–60 hoặc vừa thoát <30 | >75 hoặc divergence |
| 3 | MACD | MACD > Signal, hist tăng | MACD < Signal, hist giảm |
| 4 | Bollinger | Thoát lower band rồi phục hồi | Chạm upper quay đầu |
| 5 | Volume | Tăng khi giá tăng | Giá tăng volume teo |
| 6 | S/R | Gần hỗ trợ mạnh | Gần kháng cự chưa phá |

- Tổng ≥ +3: 🟢 **TÍN HIỆU MUA**
- Tổng −2 đến +2: 🟡 **CHỜ**
- Tổng ≤ −3: 🔴 **BÁN / TRÁNH**

### Bước 5 — Điểm giao dịch

**Stoploss:** Dưới support − 2% hoặc Entry − 1.5×ATR(14). Không >7% (HOSE).
**Target:** Kháng cự gần (T1), swing high trước (T2). R:R ≥ 1.5:1.

## Format đầu ra

```
📊 PHÂN TÍCH KỸ THUẬT: [SYMBOL]
═══════════════════════════════════

📈 XU HƯỚNG
• Trend: [Uptrend/Downtrend/Sideways]
• Giá vs MA: MA20=[X] | MA50=[X] | MA200=[X]

⚡ CHỈ BÁO
• RSI(14): X.X → [Quá mua/Bình thường/Quá bán]
• MACD: [Tích cực/Tiêu cực] | Histogram: [tăng/giảm]
• Bollinger: Giá ở [vị trí band]

🎯 TÍN HIỆU TỔNG HỢP: X/6 → 🟢/🟡/🔴
[chi tiết từng tín hiệu]

💹 ĐIỂM GIAO DỊCH
• Vào: XX,XXX đ
• Stoploss: XX,XXX đ (-X.X%)
• Target 1: XX,XXX đ (+X.X%) | Target 2: XX,XXX đ (+X.X%)
• R:R = X.X:1

📌 KẾT LUẬN: 🟢 MUA / 🟡 CHỜ / 🔴 TRÁNH
```

## Lưu ý thị trường Việt Nam

- **Biên độ:** HOSE ±7% | HNX ±10% | UPCOM ±15%
- **ATO (9:00–9:15):** Khớp mở cửa, giá/volume có thể bất thường
- **ATC (14:30–14:45):** Khớp đóng cửa, volume cuối phiên lớn
- **T+2:** Mua hôm nay bán được sau 2 phiên — không stoploss tức thì
- **Thanh khoản:** <200 triệu/ngày không trading | >1 tỷ/ngày an toàn
- **Khối ngoại:** Kiểm tra foreign room; bán ròng mạnh → TA kém tin cậy
