---
name: watchlist-check
description: Check watchlist conditions from data/watchlist.json and alert when triggered. Designed for /loop 5m usage.
allowed-tools: mcp__vn-stock-trader__get_stock_price
---

# Watchlist Check — Kiểm tra điều kiện watchlist

Designed for recurring use: `/loop 5m /watchlist-check`

## Workflow

1. Read `data/watchlist.json` for alert conditions
2. For each watchlist item, call `get_stock_price(symbol)`
3. Evaluate conditions against current price
4. Report triggered alerts

## Supported Conditions (from watchlist.json)

```json
{
  "alerts": [
    {"symbol": "VNM", "condition": "price_below", "value": 80000},
    {"symbol": "HPG", "condition": "price_above", "value": 30000},
    {"symbol": "FPT", "condition": "pct_change_above", "value": 5},
    {"symbol": "MWG", "condition": "near_ceiling", "value": 1},
    {"symbol": "TCB", "condition": "near_floor", "value": 1}
  ]
}
```

## Output Format

If NO triggers:
```
✅ {time} — Watchlist: {N} mã, không có alert mới.
```

If triggers:
```
🔔 Watchlist Alert — {time}
━━━━━━━━━━━━━━━━━━━━━━━━

🎯 {symbol}: {condition_desc} — Giá hiện tại: {price}
   Điều kiện: {condition} {value} → TRIGGERED

Watchlist: {triggered}/{total} alerts active
```

## Context-Aware

- Track which alerts already fired (don't repeat)
- Note when condition clears: "VNM đã vượt lại 80,000 — alert cleared"
- Suggest removing stale alerts
