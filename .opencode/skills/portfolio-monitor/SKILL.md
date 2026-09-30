---
name: portfolio-monitor
description: Monitor portfolio positions for price changes, volume spikes, and ceiling/floor alerts. Designed for /loop 5m usage during trading sessions.
allowed-tools: mcp__vn-stock-trader__get_stock_price, mcp__vn-stock-trader__get_portfolio
---

# Portfolio Monitor — Giám sát danh mục

Designed for recurring use: `/loop 5m /portfolio-monitor`

## Workflow

1. Call `get_portfolio()` for current positions
2. For each position, call `get_stock_price(symbol)`
3. Compare with previous check (from conversation context)
4. Alert if thresholds breached

## Alert Thresholds

| Condition | Threshold | Icon |
|-----------|-----------|------|
| Price change since last check | > 3% | 🔴 |
| Price change since open | > 5% | 🔴🔴 |
| Volume spike vs average | > 3x | 📊 |
| Near ceiling (trần) | within 1% | ⬆️ |
| Near floor (sàn) | within 1% | ⬇️ |

## Output Format

If NO alerts:
```
✅ {time} — Danh mục ổn định. NAV: {nav} ({change}% vs mở cửa)
```

If alerts exist:
```
🚨 Portfolio Alert — {time}
━━━━━━━━━━━━━━━━━━━━━━━━

🔴 {symbol}: {price} ({change}%) — {reason}
📊 {symbol}: Volume gấp {x}x trung bình
⬆️ {symbol}: Sắp chạm trần ({price}/{ceiling})

NAV: {nav} | P&L session: {pnl}
```

## Context-Aware

Claude remembers previous checks:
- Track trend: "VNM tăng liên tục 3 lần check → momentum mạnh"
- Detect reversal: "HPG đang giảm sau 4 lần tăng"
- Accumulate volume: "Total volume HPG hôm nay đã gấp 5x average"
