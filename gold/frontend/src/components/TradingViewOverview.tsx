import { useEffect, useRef } from "react";

interface Props {
  symbol: string;
  watchlist?: string[];
  height?: number;
}

/** Nhúng widget Advanced Chart chính chủ của TradingView (dark, tiếng Việt, RSI+MACD). */
export default function TradingViewOverview({ symbol, watchlist = [], height = 520 }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const key = [symbol, ...watchlist].join("|");

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    host.innerHTML = "";

    const wrap = document.createElement("div");
    wrap.className = "tradingview-widget-container";
    wrap.style.height = "100%";
    wrap.style.width = "100%";

    const inner = document.createElement("div");
    inner.className = "tradingview-widget-container__widget";
    inner.style.height = "100%";
    inner.style.width = "100%";
    wrap.appendChild(inner);

    const script = document.createElement("script");
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.async = true;
    script.type = "text/javascript";
    script.innerHTML = JSON.stringify({
      allow_symbol_change: true,
      calendar: false,
      details: false,
      hide_side_toolbar: false,
      hide_top_toolbar: false,
      hide_legend: false,
      hide_volume: false,
      interval: "60",
      locale: "vi",
      save_image: true,
      style: "1",
      symbol,
      theme: "dark",
      timezone: "Asia/Ho_Chi_Minh",
      backgroundColor: "rgba(0, 0, 0, 1)",
      gridColor: "rgba(46, 46, 46, 0.6)",
      watchlist,
      withdateranges: true,
      compareSymbols: [],
      studies: ["STD;RSI", "STD;MACD"],
      autosize: true,
    });
    wrap.appendChild(script);
    host.appendChild(wrap);

    return () => {
      host.innerHTML = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return (
    <div>
      <div className="card" style={{ padding: 6 }}>
        <div ref={hostRef} style={{ height, width: "100%" }} />
      </div>
      <p className="meta" style={{ marginTop: 12 }}>
        BIỂU ĐỒ TRADINGVIEW NÂNG CAO · RSI + MACD · DANH SÁCH THEO DÕI: PAX GOLD, TVC GOLD ·
        ĐỔI KHUNG GIỜ TRÊN THANH CÔNG CỤ
      </p>
    </div>
  );
}
