import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import LivePrice from "../components/LivePrice";
import PriceChart from "../components/PriceChart";
import ChangeChip from "../components/ChangeChip";
import { api } from "../lib/api";
import { changePct, fmtClock, fmtDate, fmtPct, fmtPrice, fmtSigned } from "../lib/format";
import type { HistoryPayload } from "../lib/types";
import { useMarket } from "../state/Market";

export default function Detail() {
  const { ref = "" } = useParams();
  const navigate = useNavigate();
  const { metaByCode, quotes, symbols } = useMarket();
  const [hist, setHist] = useState<HistoryPayload | null>(null);

  const meta = useMemo(
    () => Object.values(metaByCode).find((m) => m.alias === ref || m.code === ref),
    [metaByCode, ref],
  );

  useEffect(() => {
    if (!symbols.length) return;
    let alive = true;
    setHist(null);
    (async () => {
      try {
        setHist(await api.history(ref, 30));
      } catch {
        if (alive) setHist(null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [ref, symbols.length]);

  const code = meta?.code;
  const quote = code ? quotes[code] : undefined;
  const unit = quote?.unit ?? "VND";
  const pct = quote ? changePct(quote.buy, quote.change_buy) : 0;

  const stats = useMemo(() => {
    if (!hist) return null;
    const daily = hist.daily;
    const buys = daily.map((d) => d.buy).filter(Boolean);
    if (!buys.length) return null;
    return {
      high: Math.max(...buys),
      low: Math.min(...buys),
      first: daily[0]?.date,
      last: daily[daily.length - 1]?.date,
      span: daily.length,
    };
  }, [hist]);

  if (!meta && symbols.length) {
    return (
      <div className="page">
        <div className="empty">
          Không tìm thấy loại vàng <b>{ref}</b>
          <div style={{ marginTop: 12 }}>
            <Link className="btn btn--ghost" to="/">
              Về bảng giá
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <Link to="/" className="meta">
            ← BẢNG GIÁ
          </Link>
          <h1 className="page__title" style={{ marginTop: 6 }}>
            {quote?.name ?? meta?.name ?? "…"}
          </h1>
          <p className="page__sub">
            {meta?.brand} · {meta?.code ?? ref} · {meta?.per || "lượng"} ·{" "}
            <span className="mono">{quote?.source?.toUpperCase() ?? "…"}</span>
          </p>
        </div>
        <div className="page-head__actions">
          <Link to={`/chart?m=${meta?.alias ?? ref}`} className="btn btn--ghost">
            Biểu đồ đầy đủ
          </Link>
          <Link to="/alerts" className="btn btn--primary">
            + Tạo cảnh báo
          </Link>
        </div>
      </div>

      {/* Hero giá */}
      <div className="card detail-hero">
        <div className="row row--between wrap" style={{ alignItems: "flex-start" }}>
          <div>
            <div className="price-label">Giá mua vào</div>
            <div className="detail-hero__price">
              <LivePrice value={quote?.buy ?? 0} unit={unit} />
            </div>
            <div className="detail-hero__sub">
              {quote && <ChangeChip change={quote.change_buy} pct={pct} unit={unit} />}
              <span className="meta">
                {quote?.ts ? `CẬP NHẬT ${fmtClock(quote.ts)}` : "CHỜ DỮ LIỆU"}
              </span>
            </div>
          </div>

          <div className="row" style={{ gap: 34 }}>
            <div>
              <div className="price-label">Mua vào</div>
              <div className="mono" style={{ fontWeight: 700, fontSize: 18, marginTop: 4 }}>
                {quote ? fmtPrice(quote.buy, unit) : "—"}
              </div>
            </div>
            <div>
              <div className="price-label">Bán ra</div>
              <div
                className="mono"
                style={{ fontWeight: 700, fontSize: 18, marginTop: 4, color: "var(--on-surface-variant)" }}
              >
                {quote && quote.sell > 0 ? fmtPrice(quote.sell, unit) : "—"}
              </div>
            </div>
            <div>
              <div className="price-label">Chênh lệch</div>
              <div className="mono" style={{ fontWeight: 700, fontSize: 18, marginTop: 4 }}>
                {quote && quote.sell > 0 ? fmtSigned(quote.sell - quote.buy, unit) : "—"}
              </div>
            </div>
            <div>
              <div className="price-label">So đầu ngày</div>
              <div className="mono" style={{ fontWeight: 700, fontSize: 18, marginTop: 4 }}>
                {quote ? fmtSigned(quote.change_buy, unit) : "—"}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Biểu đồ + thống kê */}
      <div className="dash">
        <section className="panel">
          <div className="panel__head">
            <span className="panel__title">Biểu đồ · {meta?.brand ?? ref}</span>
            <span className="meta">REALTIME</span>
          </div>
          <div className="panel__body">
            <PriceChart
              symbol={meta?.alias ?? ref}
              onSymbolChange={(alias) => navigate(`/detail/${alias}`)}
              defaultRange="24h"
              height={300}
              compact
            />
          </div>
        </section>

        <div>
          {stats && (
            <section className="panel">
              <div className="panel__head">
                <span className="panel__title">Thống kê {stats.span} ngày</span>
              </div>
              <div className="panel__body">
                <div className="stat-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
                  <div className="stat">
                    <div className="stat__k">Cao nhất</div>
                    <div className="stat__v up">{fmtPrice(stats.high, unit)}</div>
                  </div>
                  <div className="stat">
                    <div className="stat__k">Thấp nhất</div>
                    <div className="stat__v down">{fmtPrice(stats.low, unit)}</div>
                  </div>
                  <div className="stat">
                    <div className="stat__k">Biên độ</div>
                    <div className="stat__v">{fmtSigned(stats.high - stats.low, unit)}</div>
                  </div>
                  <div className="stat">
                    <div className="stat__k">Hôm nay</div>
                    <div className={`stat__v ${pct > 0 ? "up" : pct < 0 ? "down" : ""}`}>
                      {fmtPct(pct)}
                    </div>
                  </div>
                </div>
                <p className="meta" style={{ marginTop: 14 }}>
                  KHOẢNG {stats.first ? fmtDate(stats.first) : ""} → {stats.last ? fmtDate(stats.last) : ""}
                </p>
              </div>
            </section>
          )}

          <section className="panel">
            <div className="panel__head">
              <span className="panel__title">Loại vàng khác</span>
            </div>
            <div className="panel__body">
              {symbols
                .filter((s) => s.code !== code)
                .slice(0, 6)
                .map((s) => {
                  const q = quotes[s.code];
                  return (
                    <div key={s.code} className="list-row">
                      <div>
                        <div className="list-row__name">{s.name}</div>
                        <div className="list-row__meta">{s.code}</div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div className="list-row__price">
                          {q ? <LivePrice value={q.buy} unit={q.unit} /> : "—"}
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
