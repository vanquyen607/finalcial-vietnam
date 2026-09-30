---
name: morning-brief
description: Pre-market morning brief — market overview, portfolio status, overnight news. Use before trading session starts.
allowed-tools: mcp__vn-stock-trader__get_market_overview, mcp__vn-stock-trader__get_portfolio, mcp__vn-stock-trader__get_news, mcp__vn-stock-trader__get_stock_price
---

# Morning Brief — Tóm tắt trước phiên

## Workflow

1. **Market Overview** — Call `get_market_overview()` for VN-Index, HNX, UPCOM
2. **Portfolio Check** — Call `get_portfolio()` for positions and P&L
3. **News Digest** — Call `get_news()` for market news, then `get_news(symbol)` for each portfolio stock
4. **Watchlist** — Read `data/watchlist.json`, call `get_stock_price(symbol)` for each

## Context-Aware Analysis

If not the first run in this session:
- Compare with previous brief results
- Highlight changes: new highs/lows, trend reversals, volume anomalies

## Output Format (Tiếng Việt)

```
☀️ Morning Brief — {date}
━━━━━━━━━━━━━━━━━━━━━━━━

📊 Thị trường:
  VN-Index: {value} ({change}%)
  HNX / UPCOM: ...
  Tin quốc tế đêm qua: {summary}

💼 Danh mục ({N} mã):
  NAV: {value} | P&L hôm qua: {pnl}
  Top tăng: {symbol} +{pct}%
  Top giảm: {symbol} -{pct}%
  T+2 hôm nay: {amount}

📰 Tin nổi bật:
  1. {headline} → ảnh hưởng {symbols}
  2. ...

⚠️ Cần chú ý: {alerts if any}

💡 Nhận định: {2-3 câu tổng hợp}
```

## Lưu ý
- Chỉ chạy ngày giao dịch (T2-T6, trừ ngày lễ)
- Nên chạy trước 9:00
