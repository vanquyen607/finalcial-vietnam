# Vietnam Stock Analysis Skill

A specialized AI Agent skill (like Claude, GPT) for technical analysis of the Vietnamese stock market. This skill automatically fetches historical data and performs multi-indicator analysis to provide investment recommendations in Vietnamese.

## 🚀 Setup and Usage

### 1. Requirements
- Python 3.8+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Skill Structure
- `SKILL.md`: Main instructions for the AI Agent (in English).
- `scripts/analyze_stock.py`: Python script for fetching stock exchange data.
- `references/data_schema.md`: Technical documentation for data structure.
- `tests/evals.json`: Sample evaluation test cases.

### 3. Manual Run (For Developers)
To test the data fetching script independently:
```bash
# Run from the skill's root directory
python scripts/analyze_stock.py [STOCK_SYMBOL]

# Example:
python scripts/analyze_stock.py FPT
```
Data will be saved at: `stock-data/[symbol]_data.json`.

## 🤖 Interaction with AI Agent
Once integrated into your Agent (like Claude Desktop or any system supporting `.skill` format), command it using natural language (Vietnamese or English):
- "Analyze FPT stock for me"
- "Đánh giá trạng thái kỹ thuật của SSI"
- "Does VNM currently have a buy point?"

**The Agent will always respond with a structured technical report in Vietnamese.**

## 📊 Analysis Indicators
The analysis is based on:
- Moving Averages (MA5, MA20, MA50, MA90, MA120, MA200).
- Relative Strength Index (RSI).
- Moving Average Convergence Divergence (MACD).
- Volume Analysis.
- Support and Resistance identification.

---
*Disclaimer: All analysis is for reference only. Stock investment involves substantial risk.*
