import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import LivePrice from "../components/LivePrice";
import PremiumPanel from "../components/PremiumPanel";
import PriceCard from "../components/PriceCard";
import PriceChart from "../components/PriceChart";
import PriceTable from "../components/PriceTable";
import Sparkline from "../components/Sparkline";
import { changePct, fmtAgo, fmtPct, fmtPrice, fmtSigned, tone } from "../lib/format";
import { ageSeconds, useNow } from "../lib/useNow";
import { useMarket } from "../state/Market";

export default function Home() {
  const { quoteList, metaByCode, status, connected, loading, refresh } = useMarket();
  const [series, setSeries] = useState<Record<string, number[]>>({});
  const now = useNow(1000);
  const age = ageSeconds(status.last_success, now);

  useEffect(() => {
    let alive = true;

    const loadSparks = async () => {
      try {
        const res = await fetch("/api/sparklines?hours=24");
        if (!res.ok) return;
        const data = (await res.json()) as { series: Record<string, { ts: number; buy: number }[]> };
        const mapped: Record<string, number[]> = {};
        for (const [code, pts] of Object.entries(data.series || {})) {
          mapped[code] = pts.map((p) => p.buy);
        }
        if (alive) setSeries(mapped);
      } catch {
        /* sparkline là tính năng phụ — lỗi thì bỏ qua */
      }
    };

    void loadSparks();
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") void loadSparks();
    }, 60_000);

    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  const featured = useMemo(
    () => quoteList.filter((q) => metaByCode[q.code]?.featured),
    [quoteList, metaByCode],
  );

  const world = quoteList.find((q) => q.code === "XAUUSD");
  const upCount = quoteList.filter((q) => q.change_buy > 0).length;
  const downCount = quoteList.filter((q) => q.change_buy < 0).length;
  const flatCount = quoteList.length - upCount - downCount;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page__title">Bảng giá vàng hôm nay</h1>
          <p className="page__sub">
            {connected ? "Dữ liệu realtime qua WebSocket" : "Mất kết nối — đang thử lại…"}
            {" · "}
            <span className="mono">nguồn {status.source || "…"}</span>
            {age !== null ? ` · dữ liệu ${fmtAgo(age)}` : ""}
          </p>
        </div>
        <div className="page-head__actions">
          <span className="meta">
            <span className="up">▲ {upCount}</span> · <span className="down">▼ {downCount}</span> ·{" "}
            <span className="flat">─ {flatCount}</span>
          </span>
          <button className="btn btn--ghost" onClick={() => void refresh()}>
            Làm mới
          </button>
        </div>
      </div>

      {loading && !quoteList.length ? (
        <div className="empty">Đang tải bảng giá…</div>
      ) : (
        <>
          {/* KPI */}
          <div className="kpi-row">
            {featured.slice(0, 4).map((q) => {
              const pct = changePct(q.buy, q.change_buy);
              const t = tone(q.change_buy);
              return (
                <Link
                  key={q.code}
                  to={`/detail/${metaByCode[q.code]?.alias || q.code}`}
                  className="kpi"
                >
                  <div className="kpi__label">
                    <span className="price-card__brand">{q.code}</span>
                    <span className={`chip chip--${t}`}>
                      {t === "up" ? "▲" : t === "down" ? "▼" : "─"}{" "}
                      {fmtSigned(q.change_buy, q.unit)} · {fmtPct(pct)}
                    </span>
                  </div>
                  <div className="kpi__value">
                    <LivePrice value={q.buy} unit={q.unit} />
                  </div>
                  <div className="kpi__sub">
                    <span>BÁN {q.sell > 0 ? fmtPrice(q.sell, q.unit) : "—"}</span>
                    <span>{q.name}</span>
                  </div>
                  <Sparkline values={series[q.code] ?? []} empty={!series[q.code]?.length} height={38} />
                </Link>
              );
            })}
          </div>

          {/* Chênh lệch SJC – thế giới */}
          <PremiumPanel />

          {/* Bảng giá + biểu đồ realtime */}
          <div className="dash">
            <section className="panel">
              <div className="panel__head">
                <span className="panel__title">Bảng giá đầy đủ · {quoteList.length} loại</span>
                <span className="meta">
                  {connected ? (
                    <span className="up">
                      ● REALTIME · {age !== null ? fmtAgo(age).toUpperCase() : "…"}
                    </span>
                  ) : (
                    <span className="down">○ ĐANG KẾT NỐI LẠI</span>
                  )}
                </span>
              </div>
              <PriceTable quotes={quoteList} fetchedAt={status.last_success} />
            </section>

            <div>
              <section className="panel">
                <div className="panel__head">
                  <span className="panel__title">Biểu đồ realtime</span>
                  <Link to="/chart" className="meta">
                    MỞ ĐẦY ĐỦ →
                  </Link>
                </div>
                <div className="panel__body">
                  <PriceChart compact height={252} defaultRange="24h" />
                </div>
              </section>

              {world && (
                <section className="panel">
                  <div className="panel__head">
                    <span className="panel__title">Vàng thế giới · XAU/USD</span>
                    <span className={`chip chip--${world.change_buy >= 0 ? "up" : "down"}`}>
                      {fmtPrice(world.buy, world.unit)}
                    </span>
                  </div>
                  <div className="panel__body">
                    <p className="page__sub" style={{ lineHeight: 1.7 }}>
                      Đơn vị USD/ounce, làm gốc so sánh với giá trong nước.
                      <br />
                      Chênh nội địa phản ánh phí gia công, thuế và cung–cầu tại Việt Nam.
                    </p>
                  </div>
                </section>
              )}
            </div>
          </div>

          {/* Nổi bật */}
          <div className="section-label">Loại vàng nổi bật</div>
          <div className="grid-3">
            {featured.map((q) => (
              <PriceCard
                key={q.code}
                quote={q}
                series={series[q.code]}
                alias={metaByCode[q.code]?.alias}
              />
            ))}
          </div>

          <p className="meta" style={{ marginTop: 26 }}>
            GIÁ CHỈ MANG TÍNH THAM KHẢO · CHẠY {status.polls ?? 0} LẦN · {status.clients ?? 0} CLIENT
            ĐANG KẾT NỐI
          </p>
        </>
      )}
    </div>
  );
}
