import { useMemo } from "react";
import GoldTable from "../components/GoldTable";
import PriceChart from "../components/PriceChart";
import { changePct, fmtAgo, fmtPct, fmtPrice, fmtSigned, tone } from "../lib/format";
import { ageSeconds, useNow } from "../lib/useNow";
import { useMarket } from "../state/Market";

const STOCKS_URL =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8100/"
    : "https://finalcial-vietnam.onrender.com/";

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

  return (
    <div className="page">
      <div className="hero">
        <div>
          <h1 className="hero__title">
            Giá vàng hôm nay,
            <br />
            <span>so sánh {brandCount || "các"} thương hiệu.</span>
          </h1>
          <p className="hero__sub">
            Giá mua vàng vào và bán vàng ra của các cửa hàng tại Việt Nam.
            <br />
            Mỗi thương hiệu hiển thị nhiều sản phẩm: vàng miếng, nhẫn trơn, vàng 24K và trang sức.
          </p>
        </div>
        <div className="hero__actions">
          <span className="meta">
            {connected ? "● REALTIME" : "○ ĐANG KẾT NỐI LẠI"}
            {age !== null ? ` · ${fmtAgo(age).toUpperCase()}` : ""}
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
          <div className="hero-stats">
            <div className="hero-stat hero-stat--primary">
              <span className="hero-stat__label">SJC bán ra</span>
              <strong>{sjc ? fmtPrice(sjc.sell, sjc.unit) : "—"}</strong>
              {sjc && (
                <span className={`chip chip--${sjcTone}`}>
                  {fmtSigned(sjc.change_buy, sjc.unit)} · {fmtPct(sjcPct)}
                </span>
              )}
            </div>
            <div className="hero-stat">
              <span className="hero-stat__label">Vàng thế giới</span>
              <strong>{world ? fmtPrice(world.buy, world.unit) : "—"}</strong>
              <span className="hero-stat__hint">USD/ounce</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat__label">Đang theo dõi</span>
              <strong>{quoteList.length} loại</strong>
              <span className="hero-stat__hint">{brandCount} thương hiệu</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat__label">Biến động</span>
              <strong>
                <span className="up">▲ {upCount}</span> <span className="down">▼ {downCount}</span>
              </strong>
              <span className="hero-stat__hint">─ {flatCount} đi ngang</span>
            </div>
          </div>

          <section className="panel panel--chart">
            <div className="panel__head">
              <span className="panel__title">Biểu đồ giá</span>
              <span className="meta">
                {status.source ? `NGUỒN ${status.source.toUpperCase()}` : "ĐANG TẢI"}
                {age !== null ? ` · ${fmtAgo(age).toUpperCase()}` : ""}
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
                {quoteList.length} LOẠI · {brandCount} THƯƠNG HIỆU
              </span>
            </div>
            <GoldTable
              quotes={quoteList}
              metaByCode={metaByCode}
              brands={brands}
              fetchedAt={status.last_success}
            />
          </section>

          <p className="meta footer-note">
            Giá chỉ mang tính tham khảo · Chạy {status.polls ?? 0} lần · {status.clients ?? 0} client
            đang kết nối ·{" "}
            <a className="footer-link" href={STOCKS_URL} title="App phân tích cổ phiếu VN">
              Phân tích cổ phiếu →
            </a>
          </p>
        </>
      )}
    </div>
  );
}
