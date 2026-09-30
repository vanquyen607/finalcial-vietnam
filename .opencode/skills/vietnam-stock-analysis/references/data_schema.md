# Stock Data Schema

The data received from `./scripts/analyze_stock.py` is formatted as a JSON array of objects, representing historical daily candles.

## Data Structure (JSON)

Each "session" (candle) contains the following fields:

| Field | Description | Data Type |
| :--- | :--- | :--- |
| `Date` | Date of the trading session (ISO format) | `String (Date)` |
| `Open` | Opening price | `Float` |
| `High` | Highest price during the session | `Float` |
| `Low` | Lowest price during the session | `Float` |
| `Close` | Closing price | `Float` |
| `Volume` | Total trading volume | `Integer` |

## Data Sample (Example JSON)

```json
[
  {
    "Date": "2024-03-15T00:00:00.000",
    "Open": 105.5,
    "High": 107.2,
    "Low": 105.1,
    "Close": 106.8,
    "Volume": 1500000
  },
  {
    "Date": "2024-03-18T00:00:00.000",
    "Open": 106.8,
    "High": 108.5,
    "Low": 106.2,
    "Close": 108.3,
    "Volume": 1850000
  }
]
```

## Calculation Logic (for AI)

This is "Raw Data". The AI must independently calculate the following technical indicators based on the provided daily candles:

- **Moving Averages (MA5, MA20, MA50, etc.)**: Calculated by averaging the `Close` price over the last N sessions.
- **RSI (14)**: Based on the closing price changes (`Close`).
- **MACD (12, 26, 9)**: Based on the difference between Exponential Moving Averages.
- **Volume**: Compare the last session's volume with its moving average (MA20 Volume).
