import { Link } from "react-router-dom";
import { changePct, fmtCompact, fmtPrice } from "../lib/format";
import type { Quote } from "../lib/types";
import ChangeChip from "./ChangeChip";
import Sparkline from "./Sparkline";

export default function PriceCard({
  quote,
  series,
  alias,
}: {
  quote: Quote;
  series?: number[];
  alias?: string;
}) {
  const pct = changePct(quote.buy, quote.change_buy);
  const ref = alias || quote.code;
  const hasSpread = quote.sell > 0;

  return (
    <Link to={`/detail/${ref}`} className="card price-card">
      <div className="price-card__top">
        <span className="price-card__brand">{quote.code}</span>
        <span className="price-card__name">{quote.name}</span>
      </div>

      <div className="price-card__row">
        <div>
          <div className="price-label">Mua vào</div>
          <div className="price-card__bid">{fmtPrice(quote.buy, quote.unit)}</div>
        </div>
        <ChangeChip change={quote.change_buy} pct={pct} unit={quote.unit} />
      </div>

      <div className="price-card__grid">
        <div>
          <div className="price-label">Bán ra</div>
          <div className="price-card__ask">{hasSpread ? fmtPrice(quote.sell, quote.unit) : "—"}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="price-label">Chênh lệch</div>
          <div className="price-card__ask">
            {hasSpread ? fmtCompact(quote.sell - quote.buy, quote.unit) : "—"}
          </div>
        </div>
      </div>

      <Sparkline values={series ?? []} empty={!series || series.length < 2} />
    </Link>
  );
}
