import { useEffect, useMemo, useState } from "react";
import ChartView from "./ChartView";
import type { ChartPoint } from "./ChartView";
import LivePrice from "./LivePrice";
import TechGauge from "./TechGauge";
import { api } from "../lib/api";
import { changePct, fmtPct } from "../lib/format";
import { basePoints, mergeLive, useLiveSeries } from "../lib/useLiveSeries";
import type { HistoryPayload } from "../lib/types";
import { useMarket } from "../state/Market";

/** Panel vàng thế giới: giá spot XAUUSD nhảy theo tick của app (trái)
 * + đồng hồ sức mua/bán TradingView (phải). */
export default function WorldLive() {
  const { quotes } = useMarket();
  const quote = quotes["XAUUSD"];
  const [hist, setHist] = useState<HistoryPayload | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .history("xauusd", 30)
      .then((d) => {
        if (alive) setHist(d);
      })
      .catch(() => {
        if (alive) setHist(null);
      });
    return () => {
      alive = false;
    };
  }, []);

  const live = useLiveSeries(quote, "intraday");
  const points: ChartPoint[] = useMemo(
    () => (hist ? mergeLive(basePoints(hist, "24h"), live) : []),
    [hist, live],
  );
  const pct = quote ? changePct(quote.buy, quote.change_buy) : 0;
  const rising = points.length >= 2
    ? points[points.length - 1].value >= points[0].value
    : pct >= 0;

  return (
    <div className="world-grid">
      <div>
        <div className="row row--between" style={{ marginBottom: 10, gap: 12, flexWrap: "wrap" }}>
          <div className="row">
            <span className="price-card__brand">Spot</span>
            <span style={{ fontWeight: 600 }}>XAU/USD</span>
            {quote ? (
              <LivePrice value={quote.buy} unit="USD" className="mono world-price" />
            ) : (
              <span className="mono world-price">—</span>
            )}
            <span className={`chip chip--${pct > 0 ? "up" : pct < 0 ? "down" : "flat"}`}>
              {fmtPct(pct)}
            </span>
            <span className="meta" style={{ whiteSpace: "nowrap" }}>
              <span className="dot dot--live" /> đang cập nhật
            </span>
          </div>
        </div>
        {points.length >= 2 ? (
          <div className="card" style={{ padding: 6 }}>
            <ChartView
              points={points}
              positive={rising}
              height={300}
              unit="USD"
              fitKey={`xauusd:24h:${hist ? "ready" : "wait"}`}
            />
          </div>
        ) : (
          <div className="empty">
            Đang gom dữ liệu biểu đồ thế giới…
            <br />
            <span className="meta">Đường giá sẽ hiện sau vài tick cập nhật.</span>
          </div>
        )}
        <p className="meta" style={{ marginTop: 10 }}>
          Giá spot quốc tế, cập nhật theo mỗi tick của app (~30 giây). Biểu đồ 24 giờ gần nhất.
        </p>
      </div>
      <TechGauge />
    </div>
  );
}
