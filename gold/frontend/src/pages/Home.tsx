import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import GoldTable from "../components/GoldTable";
import PriceChart from "../components/PriceChart";
import { api } from "../lib/api";
import { changePct, fmtAgo, fmtPct, fmtPrice, fmtSigned, tone } from "../lib/format";
import type { Alert, NewsItem } from "../lib/types";
import { ageSeconds, useNow } from "../lib/useNow";
import { useMarket } from "../state/Market";

const STOCKS_URL =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8100/"
    : "https://finalcial-vietnam.onrender.com/";

/** Giá trị cảnh báo đã định dạng: "≥ 140.000.000" hoặc "↑ 1%". */
function alertValue(a: Alert): string {
  if (a.target_price != null) {
    const sign = a.direction === "up" ? "≥" : "≤";
    return `${sign} ${fmtPrice(a.target_price, "VND")}`;
  }
  return `${a.direction === "up" ? "↑" : "↓"} ${a.threshold}%`;
}

export default function Home() {
  const { quoteList, metaByCode, brands, status, connected, loading, refresh } = useMarket();
  const now = useNow(1000);
  const age = ageSeconds(status.last_success, now);

  const sjc = useMemo(() => quoteList.find((q) => q.code === "SJL1L10"), [quoteList]);
  const world = useMemo(() => quoteList.find((q) => q.code === "XAUUSD"), [quoteList]);

  const upCount = quoteList.filter((q) => q.change_buy > 0).length;
  const downCount = quoteList.filter((q) => q.change_buy < 0).length;
  const flatCount = quoteList.length - upCount - downCount;
  const brandCount = brands.length || new Set(quoteList.map((q) => metaByCode[q.code]?.brand)).size;

  const sjcPct = sjc ? changePct(sjc.buy, sjc.change_buy) : 0;
  const sjcTone = sjc ? tone(sjc.change_buy) : "flat";
  const spread = sjc ? sjc.sell - sjc.buy : null;

  /* ---------- filter (tìm kiếm + thương hiệu) ---------- */
  const [query, setQuery] = useState("");
  const [brandFilter, setBrandFilter] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return quoteList.filter((item) => {
      if (brandFilter && (metaByCode[item.code]?.brand ?? "") !== brandFilter) return false;
      if (!q) return true;
      const meta = metaByCode[item.code];
      return (
        item.code.toLowerCase().includes(q) ||
        (meta?.product ?? item.name).toLowerCase().includes(q) ||
        (meta?.brand ?? "").toLowerCase().includes(q) ||
        (meta?.name ?? "").toLowerCase().includes(q)
      );
    });
  }, [quoteList, metaByCode, query, brandFilter]);

  /* ---------- side column: tin nổi bật + cảnh báo ---------- */
  const [news, setNews] = useState<NewsItem[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    let alive = true;
    api
      .news(5)
      .then((d) => {
        if (alive) setNews(d.items);
      })
      .catch(() => {
        /* API news lỗi -> để trống, không crash trang */
      });
    api
      .alerts()
      .then((d) => {
        if (alive) setAlerts(d.items.filter((a) => a.active).slice(0, 6));
      })
      .catch(() => {
        /* bỏ qua */
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="page">
      <div className="hero">
        <div>
          <h1 className="hero__title">
            Giá vàng hôm nay, so sánh {brandCount || "các"} thương hiệu.
          </h1>
          <p className="hero__sub">
            Giá mua vào và bán ra của các cửa hàng tại Việt Nam. Mỗi thương hiệu hiển thị nhiều
            sản phẩm: vàng miếng, nhẫn trơn, vàng 24K và trang sức.
          </p>
        </div>
        <div className="hero__actions">
          <span className="meta">{connected ? "Realtime" : "Đang kết nối lại"}</span>
          {age !== null && <span className="meta">{fmtAgo(age)}</span>}
          <button className="btn btn--ghost" onClick={() => void refresh()}>
            Làm mới
          </button>
        </div>
      </div>

      {loading && !quoteList.length ? (
        <div className="empty">Đang tải bảng giá…</div>
      ) : (
        <>
          <div className="hero-stats">
            <div className="hero-stat hero-stat--primary">
              <span className="hero-stat__label">SJC bán ra</span>
              <strong>{sjc ? fmtPrice(sjc.sell, sjc.unit) : "—"}</strong>
              {sjc && (
                <span className={`chip chip--${sjcTone}`}>
                  {fmtSigned(sjc.change_buy, sjc.unit)} ({fmtPct(sjcPct)})
                </span>
              )}
            </div>
            <div className="hero-stat">
              <span className="hero-stat__label">Vàng thế giới</span>
              <strong>{world ? fmtPrice(world.buy, world.unit) : "—"}</strong>
              <span className="hero-stat__hint">USD/ounce</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat__label">Chênh lệch mua / bán</span>
              <strong>{spread !== null ? fmtPrice(spread, "VND") : "—"}</strong>
              <span className="hero-stat__hint">SJC 1 lượng</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat__label">Biến động</span>
              <strong>
                <span className="up">▲ {upCount}</span> <span className="down">▼ {downCount}</span>
              </strong>
              <span className="hero-stat__hint">─ {flatCount} đi ngang</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat__label">Đang theo dõi</span>
              <strong>{quoteList.length} loại</strong>
              <span className="hero-stat__hint">{brandCount} thương hiệu</span>
            </div>
          </div>

          <div className="dash-grid">
            <div className="dash-main">
              <section className="panel panel--chart">
                <div className="panel__head">
                  <span className="panel__title">Biểu đồ giá</span>
                  <span className="meta">
                    {status.source ? `Nguồn ${status.source}` : "Đang tải"}
                  </span>
                </div>
                <div className="panel__body">
                  <PriceChart compact height={320} defaultRange="7d" />
                </div>
              </section>

              <section className="panel">
                <div className="panel__head">
                  <span className="panel__title">Bảng giá vàng</span>
                  <span className="meta">
                    {filtered.length === quoteList.length
                      ? `${quoteList.length} loại, ${brandCount} thương hiệu`
                      : `${filtered.length}/${quoteList.length} loại`}
                  </span>
                </div>
                <div className="filter-bar">
                  <input
                    type="search"
                    placeholder="Tìm sản phẩm, mã, thương hiệu…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    aria-label="Tìm trong bảng giá"
                  />
                  <select
                    value={brandFilter}
                    onChange={(e) => setBrandFilter(e.target.value)}
                    aria-label="Lọc theo thương hiệu"
                  >
                    <option value="">Tất cả thương hiệu</option>
                    {brands.map((b) => (
                      <option key={b.brand} value={b.brand}>
                        {b.label} ({b.count})
                      </option>
                    ))}
                  </select>
                  {(query || brandFilter) && (
                    <button
                      className="btn btn--ghost"
                      onClick={() => {
                        setQuery("");
                        setBrandFilter("");
                      }}
                    >
                      Xóa lọc
                    </button>
                  )}
                </div>
                <GoldTable
                  quotes={filtered}
                  metaByCode={metaByCode}
                  brands={brands}
                  fetchedAt={status.last_success}
                />
                {filtered.length === 0 && (
                  <div className="empty" style={{ padding: 18 }}>
                    Không có sản phẩm khớp “{query || brandFilter}”.
                  </div>
                )}
              </section>
            </div>

            <aside className="dash-side">
              <section className="panel">
                <div className="panel__head">
                  <span className="panel__title">Tin nổi bật</span>
                  <span className="meta">{news.length} tin</span>
                </div>
                <div className="panel__body">
                  {news.length === 0 ? (
                    <div className="empty">Đang tải tin…</div>
                  ) : (
                    news.map((n) => {
                      const nAge = ageSeconds(n.published, now);
                      return (
                        <a
                          key={n.link}
                          className="news-line"
                          href={n.link}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <span className="news-line__title">{n.title}</span>
                          <span className="news-line__meta">
                            {n.source}
                            {nAge !== null ? ` · ${fmtAgo(nAge)}` : ""}
                          </span>
                        </a>
                      );
                    })
                  )}
                  <div className="side-foot">
                    <span className="meta">Cập nhật tự động</span>
                    <Link to="/news">Xem tất cả →</Link>
                  </div>
                </div>
              </section>

              <section className="panel">
                <div className="panel__head">
                  <span className="panel__title">Cảnh báo giá</span>
                  <span className="meta">{alerts.length} đang bật</span>
                </div>
                <div className="panel__body">
                  {alerts.length === 0 ? (
                    <div className="empty">Chưa có cảnh báo đang bật.</div>
                  ) : (
                    alerts.map((a) => (
                      <div key={a.id} className="alert-line">
                        <span className="alert-line__name">
                          {a.name || a.code}
                          {a.note ? ` · ${a.note}` : ""}
                        </span>
                        <b className={a.direction === "up" ? "up" : "down"}>{alertValue(a)}</b>
                      </div>
                    ))
                  )}
                  <div className="side-foot">
                    <span className="meta">Đặt ngưỡng giá</span>
                    <Link to="/alerts">Quản lý →</Link>
                  </div>
                </div>
              </section>
            </aside>
          </div>

          <p className="meta footer-note">
            Giá chỉ mang tính tham khảo. Chạy {status.polls ?? 0} lần, {status.clients ?? 0} client
            đang kết nối.{" "}
            <a className="footer-link" href={STOCKS_URL} title="App phân tích cổ phiếu VN">
              Phân tích cổ phiếu →
            </a>
          </p>
        </>
      )}
    </div>
  );
}
