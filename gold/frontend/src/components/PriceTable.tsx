import { useNavigate } from "react-router-dom";
import { changePct, fmtClock, fmtPct, fmtSigned, tone } from "../lib/format";
import type { Quote } from "../lib/types";
import LivePrice from "./LivePrice";
import { useMarket } from "../state/Market";

/** Bảng giá đầy đủ — click 1 dòng để mở chi tiết. Giá nháy khi có tick. */
export default function PriceTable({
  quotes,
  fetchedAt,
}: {
  quotes: Quote[];
  /** thời điểm backend vừa lấy snapshot (cột "lấy lúc") */
  fetchedAt?: number | null;
}) {
  const { metaByCode } = useMarket();
  const navigate = useNavigate();

  return (
    <div className="tbl-wrap">
      <table className="tbl">
        <thead>
          <tr>
            <th>Loại vàng</th>
            <th>Mua vào</th>
            <th>Bán ra</th>
            <th>Chênh mua/bán</th>
            <th>Thay đổi</th>
            <th>Phần trăm</th>
            <th>Lấy lúc</th>
          </tr>
        </thead>
        <tbody>
          {quotes.map((q) => {
            const pct = changePct(q.buy, q.change_buy);
            const t = tone(q.change_buy);
            const hasSpread = q.sell > 0;
            return (
              <tr
                key={q.code}
                onClick={() => navigate(`/detail/${metaByCode[q.code]?.alias || q.code}`)}
              >
                <td>
                  <span className="name">{q.name}</span>
                  <span className="sub">
                    {q.code} · {q.per || "lượng"}
                  </span>
                </td>
                <td className="bid">
                  <LivePrice value={q.buy} unit={q.unit} />
                </td>
                <td className="ask">{hasSpread ? <LivePrice value={q.sell} unit={q.unit} /> : "—"}</td>
                <td className="ask">{hasSpread ? fmtSigned(q.sell - q.buy, q.unit) : "—"}</td>
                <td className={t === "flat" ? "muted" : t}>{fmtSigned(q.change_buy, q.unit)}</td>
                <td className={t === "flat" ? "muted" : t}>{fmtPct(pct)}</td>
                <td className="muted">{fmtClock(fetchedAt ?? q.ts)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
