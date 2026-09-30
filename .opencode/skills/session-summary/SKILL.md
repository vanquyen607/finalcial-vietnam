---
name: session-summary
description: End-of-day trading session summary — P&L, market recap, top movers, news highlights, action items for tomorrow.
allowed-tools: mcp__vn-stock-trader__get_market_overview, mcp__vn-stock-trader__get_portfolio, mcp__vn-stock-trader__get_top_movers, mcp__vn-stock-trader__get_news
---

# Session Summary — Tổng kết phiên

## Workflow

1. **Market Recap** — Call `get_market_overview()` for index performance
2. **Top Movers** — Call `get_top_movers()` for biggest gainers/losers
3. **Portfolio P&L** — Call `get_portfolio()` for today's performance
4. **News Impact** — Call `get_news()` for today's key news

## Context-Aware Analysis

Use conversation history from the trading session:
- What alerts fired during the session?
- What analysis was done?
- What trades/decisions were considered?
- Summarize the session's activity

## Output Format (Tiếng Việt)

```
📊 Tổng kết phiên — {date}
━━━━━━━━━━━━━━━━━━━━━━━━

🏛️ Thị trường:
  VN-Index: {value} ({change}%) | Volume: {vol}
  Breadth: {up} tăng / {down} giảm / {flat} đứng
  Khối ngoại: {foreign_flow}

💼 Danh mục:
  P&L hôm nay: {pnl} ({pct}%)
  NAV: {nav}
  Best: {symbol} +{pct}% | Worst: {symbol} -{pct}%

📰 Tin quan trọng:
  1. {headline}
  2. ...

🔮 Ngày mai:
  - {action items}
  - {things to watch}
```
