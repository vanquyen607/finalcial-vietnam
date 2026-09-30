import { useNavigate } from "react-router-dom";
import { changePct, fmtPct, fmtPrice } from "../lib/format";
import { useMarket } from "../state/Market";

/** Dải chạy chữ (marquee) kiểu sàn giao dịch — giá nhảy realtime từ WebSocket. */
export default function Ticker() {
  const { quoteList, metaByCode } = useMarket();
  const navigate = useNavigate();

  if (!quoteList.length) return null;

  const items = quoteList.map((q) => {
    const pct = changePct(q.buy, q.change_buy);
    const tone = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
    return (
      <span
        key={q.code}
        className="ticker__item"
        onClick={() => navigate(`/detail/${metaByCode[q.code]?.alias || q.code}`)}
      >
        <b>{q.code}</b>
        <span>{fmtPrice(q.buy, q.unit)}</span>
        <span className={tone}>{fmtPct(pct)}</span>
      </span>
    );
  });

  return (
    <div className="ticker">
      <div className="ticker__track">
        {items}
        {items}
      </div>
    </div>
  );
}
