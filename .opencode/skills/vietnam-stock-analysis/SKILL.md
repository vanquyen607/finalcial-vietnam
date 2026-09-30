---
name: vietnam-stock-analysis
description: Professional Vietnamese stock market technical analysis expert. Use this skill when the user asks to analyze a stock symbol (e.g., "phân tích mã HPG", "đánh giá cổ phiếu VCB", "soi mã SSI", "analyze FPT stock"), needs to understand market trends, technical indicators (MA, RSI, MACD, volume), identify support/resistance levels, or find optimal buy/sell points for stocks listed on HOSE, HNX, or UPCOM. Also trigger when the user mentions checking a stock's trend, momentum, buy zone, or asks about overbought/oversold conditions. This skill automatically fetches 200 sessions of historical data and performs multi-timeframe analysis to provide detailed, action-oriented recommendations in Vietnamese. Make sure to use this skill whenever the user mentions a Vietnamese stock ticker followed by any form of analysis request, even casually like "xem mã TCB đi" or "HPG bây giờ sao?".
---

# Vietnam Stock Analysis

This skill transforms the AI into a specialized Technical Analyst for the Vietnamese stock market. It combines Python's data processing power with AI's reasoning capabilities to provide sharp, objective insights.

## Standard Workflow

Always follow this procedure to ensure accuracy:

1.  **Data Acquisition (Direct from Exchange):**
    Use the `./scripts/analyze_stock.py` script to fetch the last 200 trading sessions.
    Run this command from the skill's root directory:
    ```bash
    python ./scripts/analyze_stock.py [SYMBOL]
    ```
    *Note: Replace [SYMBOL] with the stock ticker (e.g., FPT, VNM).*

2.  **Read and Pre-process:**
    Read the generated JSON file in the `stock-data/` directory (e.g., `stock-data/fpt_data.json`).

3.  **Search External Market Context (Real-Time Web Search):**
    Before running technical analysis, use the `search_web` tool to gather today's external factors. Run **all seven** of the following searches:

    🇻🇳 **Thị trường trong nước:**
    - `tin tức [SYMBOL] hôm nay` — Latest news about the company
    - `cổ phiếu [SYMBOL] phân tích` — Market analysts' view on the stock
    - `VNIndex hôm nay` — Overall market sentiment (VNIndex)
    - `khối ngoại mua bán hôm nay` — Foreign investor buy/sell activity

    🌍 **Yếu tố thế giới:**
    - `chứng khoán Mỹ S&P500 Dow Jones hôm nay` — US equity market direction (leading indicator for Asian markets)
    - `tỷ giá USD DXY hôm nay` — USD strength, directly affects VND and foreign capital flows
    - `giá dầu thế giới hôm nay` — Crude oil price, broad macro risk signal

    Collect the key findings (headlines, sentiment, notable events) to enrich the analysis with real-world context. Prioritize content from the **current date**; if today's data is unavailable, use the most recent available. Note the source and date of each finding.

4.  **Technical Analysis (AI-driven):**
    Analyze key indicators from the raw data:
    - **Trends (Moving Averages):** MA5, MA20 (short-term), MA50, MA90 (medium-term), MA120, MA200 (long-term).
    - **Momentum:** MACD (Histogram, Signal), RSI (Overbought/Oversold).
    - **Volume:** Compare current volume with the 20-session average to confirm money flow.
    - **Support/Resistance:** Identify key price levels based on historical volatility.

5.  **Synthesize Findings:**
    Provide a concise but meaningful assessment for each criterion. Integrate the external context from Step 3 into the final assessment — note whether news sentiment reinforces or contradicts the technical signals.

6.  **Present & Save Report:**
    - **Present:** Display the full report directly to the user in the conversation.
    - **Save:** Also save the report as a Markdown file in the `reports/` directory (create it if it doesn't exist) with the naming convention:
      ```
      reports/[SYMBOL]_[YYYY-MM-DD].md
      ```
      Example: `reports/SSI_2026-03-18.md`
    - Inform the user where the report was saved.

## Report Structure (Output Requirements)

**CRITICAL:** The report **MUST** be in **Vietnamese**, visually rich, and follow this structure. Use **Markdown tables** and emoji to make data scannable. Do NOT use ASCII art boxes (they render poorly). See `references/example_report.md` for a complete example.

**Header** — Start with a metadata table: Mã CP, Sàn, Ngày phân tích, Giá đóng cửa, 52W High/Low.

**Section 1: Tổng Quan Xu Hướng 📈** — Markdown table with columns: Khung thời gian / Xu hướng / Tín hiệu (🔴/🟡/🟢) / Ghi chú. Include an Overall row with verdict (BEARISH/NEUTRAL/BULLISH).

**Section 2: Chỉ Số Kỹ Thuật 🔍** — Present each sub-indicator as tables:
- **Moving Averages:** Table with columns: Đường MA / Giá trị / So với giá / Trạng thái (✅/❌). End with a summary line (e.g., "3/6 MA hỗ trợ").
- **RSI and MACD:** Table (Chỉ số / Giá trị / Tín hiệu / Đánh giá). Add an RSI position table showing which zone the current RSI falls in. Add a MACD Histogram table for the last 10 sessions using 🟩/🟥 emoji squares as visual bars.
- **Volume:** Table comparing last 3-5 sessions vs MA20, with emoji ratings 🔴/🟡/🟢.

**Section 3: Vùng Hỗ Trợ và Kháng Cự 🗺️** — A price ladder table with columns: Mức giá / Loại (🔵/🔴/🟠/🟢/⭐) / Mô tả / Khoảng cách (%). Mark current price with ★. Sort from highest to lowest.

**Section 4: 🌐 Bối Cảnh Thị Trường & Tin Tức** — This section presents real-time external findings gathered in Step 3. Structure it as:
- **Tổng quan thị trường trong nước:** A table summarizing VNIndex status + khối ngoại activity (Yếu tố / Trạng thái 🔴/🟡/🟢 / Chi tiết / Nguồn).
- **🌍 Yếu Tố Thế Giới:** A table covering global macro signals: US market (S&P500/Dow), USD/DXY rate, and oil price. Columns: Yếu tố thế giới / Trạng thái / Giá trị / Tác động đến TTCK VN 🔴/🟡/🟢 / Nguồn. After the table, add a short analysis of how these global factors specifically affect [SYMBOL]'s sector (e.g., tech, banking, commodities).
- **Tin tức nổi bật về [SYMBOL]:** A table of key headlines (Tin tức / Ngày / Mức ảnh hưởng 🔴/🟡/🟢 / Nguồn).
- **Tổng hợp tác động:** A summary table with two rows — Domestic context and Global context — each rated TAILWIND 🟢, NEUTRAL 🟡, or HEADWIND 🔴. End with an overall external signal verdict and confidence note.

**Section 5: Nhận Định và Khuyến Nghị 💡** — Include:
- A scorecard table rating: Xu hướng, Momentum, Dòng tiền, Yếu tố ngoài, Rủi ro (each /10) using ⬛/⬜ block characters as progress bars. *("Yếu tố ngoài" is scored based on news/market context from Section 4.)*
- If BUY: a trigger checklist table (✅/⬜ conditions) and a trade plan table (Vùng mua / Chốt lời / Cắt lỗ / R:R Ratio). Add a reasoning table.
- If SELL/HOLD: clearly state reasons and conditions to reassess.


**Footer:**

### ⚠️ Lưu ý
> Đây chỉ là phân tích kỹ thuật mang tính chất tham khảo, **KHÔNG** phải lời khuyên đầu tư tài chính.

---
**Dữ liệu nguồn:** `~[path to JSON file]~`


## Trigger Examples

**User:** "Phân tích giúp mình mã FPT nhé"
**Claude:** [Activates skill, runs script, reads JSON, and presents report in Vietnamese as formatted above]

## Environment Requirements

This skill requires the following Python libraries (must be installed manually):
- `vnstock`: For real-time data fetching.
- `pandas`: Dataframe processing.
- `pytz`: Vietnamese timezone management.

Install via:
`pip install -r requirements.txt`

## Error Handling

If the script fails or produces unexpected results, follow these steps:
- **Invalid symbol**: Inform the user that the stock symbol was not found. Ask them to double-check the ticker.
- **Network error**: Tell the user there was a connection issue fetching data from the exchange. Suggest retrying.
- **Insufficient data** (fewer than 50 sessions): Warn the user that the analysis may be unreliable due to limited historical data and proceed with caution.
- **Out-of-scope request** (e.g., fundamental analysis, news, earnings): Politely clarify that this skill only covers technical analysis (TA). Suggest external resources for fundamental analysis (FA).

## Important Notes
- Combines **technical analysis** with **real-time external context** (news, VNIndex, foreign investor activity) for a more complete picture.
- News search is performed on each run — results reflect the current date. Source titles and URLs are included in the report for transparency.
- Always remind the user that this is for reference only and not financial investment advice.
