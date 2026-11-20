import { Fragment, useMemo, useState } from "react";
import MarketTabs from "../components/MarketTabs";
import { HeroStatsSkeleton, TablePanelSkeleton } from "../components/Skeletons";
import { changePct, fmtAgo, fmtPct, fmtPrice, fmtSigned, tone } from "../lib/format";
import { useExtras } from "../lib/useExtras";
import { ageSeconds, useNow } from "../lib/useNow";
import type { SilverDomesticItem } from "../lib/types";

const FX_NUM = new Intl.NumberFormat("vi-VN", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

function fmtFx(v: number | null): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return FX_NUM.format(v);
}

export function SilverPage() {
  const { data, loading, error, refresh } = useExtras();
  const [query, setQuery] = useState("");
  const [brandFilter, setBrandFilter] = useState("");
  const now = useNow(5000);

  const silver = data?.silver ?? null;
  const domestic = useMemo(() => data?.silver_domestic?.items ?? [], [data]);
  const brands = useMemo(() => Array.from(new Set(domestic.map((i) => i.brand))), [domestic]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return domestic.filter((item) => {
      if (brandFilter && item.brand !== brandFilter) return false;
      if (!q) return true;
      return item.name.toLowerCase().includes(q) || item.brand.toLowerCase().includes(q);
    });
  }, [domestic, query, brandFilter]);

  const grouped = useMemo(() => {
    const map = new Map<string, SilverDomesticItem[]>();
    for (const item of filtered) {
      const list = map.get(item.brand) ?? [];
      list.push(item);
      map.set(item.brand, list);
    }
    return Array.from(map.entries());
  }, [filtered]);

  const headline = domestic.find((i) => i.brand === "DOJI" && i.sell) ?? domestic.find((i) => i.sell);
  const premium =
    headline?.sell && silver?.vnd_per_luong
      ? (headline.sell / silver.vnd_per_luong - 1) * 100
      : null;
  const age = ageSeconds(data?.silver_domestic?.ts ?? silver?.ts ?? null, now);
  const worldPct = silver ? changePct(silver.price_usd, silver.change_usd) : 0;

  return (
    <div className="page">
      <MarketTabs />

      <div className="hero">
        <div>
          <h1 className="hero__title">Giá bạc hôm nay</h1>
          <p className="hero__sub">
            Bạc thế giới (XAG/USD) và bảng giá bạc miếng, bạc thỏi trong nước theo từng thương hiệu.
          </p>
        </div>
        <div className="hero__actions">
          {age !== null && <span className="meta">Cập nhật {fmtAgo(age)}</span>}
          <button className="btn btn--ghost" onClick={() => void refresh()}>
            Làm mới
          </button>
        </div>
      </div>

      {loading && !data ? (
        <>
          <HeroStatsSkeleton />
          <TablePanelSkeleton rows={6} />
        </>
      ) : error && !data ? (
        <div className="empty">{error}</div>
      ) : (
        <>
          <div className="hero-stats">
            <div className="hero-stat hero-stat--primary">
              <div className="hero-stat__head">
                <span className="hero-stat__label">Bạc thế giới (XAG/USD)</span>
                <strong>{silver ? `${fmtPrice(silver.price_usd, "USD")} $` : "—"}</strong>
              </div>
              {silver && (
                <span className={`chip chip--${tone(silver.change_usd)}`}>
                  {fmtSigned(silver.change_usd, "USD")} ({fmtPct(worldPct)})
                </span>
              )}
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">Thế giới quy đổi</span>
              <strong>
                {silver?.vnd_per_luong != null ? fmtPrice(silver.vnd_per_luong, "VND") : "—"}
              </strong>
              <span className="hero-stat__hint">đ/lượng</span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">
                {headline ? `${headline.brand} bán ra` : "Bạc trong nước"}
              </span>
              <strong>{headline?.sell ? fmtPrice(headline.sell, "VND") : "—"}</strong>
              <span className="hero-stat__hint">
                {premium != null
                  ? `Cao hơn TG ${premium.toFixed(1).replace(".", ",")}%`
                  : "đ/lượng"}
              </span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">Thương hiệu</span>
              <strong>{brands.length} hãng</strong>
              <span className="hero-stat__hint">{domestic.length} sản phẩm</span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">Nguồn dữ liệu</span>
              <strong>{silver?.source || "—"}</strong>
              <span className="hero-stat__hint">{data?.silver_domestic?.source || "Trong nước"}</span>
            </div>
          </div>

          <section className="panel panel--table">
            <div className="panel__head">
              <span className="panel__title">Bảng giá bạc trong nước</span>
              <span className="meta">
                {filtered.length}/{domestic.length} sản phẩm
              </span>
            </div>
            <div className="filter-bar">
              <input
                type="search"
                placeholder="Tìm sản phẩm bạc, thương hiệu…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Tìm giá bạc"
              />
              <select
                value={brandFilter}
                onChange={(e) => setBrandFilter(e.target.value)}
                aria-label="Lọc thương hiệu bạc"
              >
                <option value="">Tất cả thương hiệu</option>
                {brands.map((b) => (
                  <option key={b} value={b}>
                    {b}
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
            <div className="gold-table-wrap">
              <table className="gold-table">
                <thead>
                  <tr>
                    <th>Sản phẩm</th>
                    <th className="num">Mua vào</th>
                    <th className="num">Bán ra</th>
                    <th className="num gt-spread">Chênh lệch</th>
                    <th className="num gt-change">Thay đổi</th>
                  </tr>
                </thead>
                <tbody>
                  {grouped.map(([brand, items]) => (
                    <Fragment key={brand}>
                      <tr className="gold-table__group">
                        <td colSpan={5}>
                          <span className="gold-table__brand">{brand}</span>
                          <span className="gold-table__count">{items.length} sản phẩm</span>
                        </td>
                      </tr>
                      {items.map((s) => {
                        const spread = s.buy && s.sell ? s.sell - s.buy : null;
                        const chg = s.change ?? 0;
                        const t = tone(chg);
                        return (
                          <tr key={`${s.brand}-${s.name}`}>
                            <td className="gt-col-name">
                              <span className="gt-name">{s.name}</span>
                            </td>
                            <td className="num bid">
                              {s.buy != null ? fmtPrice(s.buy, "VND") : "—"}
                              {chg !== 0 && (
                                <span className={`gt-inline-chg ${t}`}>
                                  {fmtSigned(chg, "VND")}
                                </span>
                              )}
                            </td>
                            <td className="num ask">
                              {s.sell != null ? fmtPrice(s.sell, "VND") : "—"}
                            </td>
                            <td className="num muted gt-spread">
                              {spread != null ? fmtPrice(spread, "VND") : "—"}
                            </td>
                            <td className={`num ${t} gt-change`}>
                              {chg !== 0 ? fmtSigned(chg, "VND") : "—"}
                            </td>
                          </tr>
                        );
                      })}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
            {filtered.length === 0 && (
              <div className="empty" style={{ padding: 18 }}>
                Không có sản phẩm bạc phù hợp.
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export function FuelPage() {
  const { data, loading, error, refresh } = useExtras();
  const now = useNow(5000);

  const fuel = data?.fuel ?? null;
  const items = useMemo(() => fuel?.items ?? [], [fuel]);
  const age = ageSeconds(fuel?.ts ?? null, now);

  const ron95 = items.find((i) => i.name.includes("95")) ?? items[0];
  const e5 = items.find((i) => i.name.includes("E5"));
  const diesel = items.find((i) => i.name.includes("DO"));

  return (
    <div className="page">
      <MarketTabs />

      <div className="hero">
        <div>
          <h1 className="hero__title">Giá xăng dầu hôm nay</h1>
          <p className="hero__sub">
            Bảng giá bán lẻ xăng dầu {fuel?.source ?? "Petrolimex"} theo Vùng 1 và Vùng 2 (đồng/lít).
          </p>
        </div>
        <div className="hero__actions">
          {age !== null && <span className="meta">Cập nhật {fmtAgo(age)}</span>}
          <button className="btn btn--ghost" onClick={() => void refresh()}>
            Làm mới
          </button>
        </div>
      </div>

      {loading && !data ? (
        <>
          <HeroStatsSkeleton />
          <TablePanelSkeleton rows={6} />
        </>
      ) : error && !data ? (
        <div className="empty">{error}</div>
      ) : !fuel ? (
        <div className="empty">Chưa có dữ liệu xăng dầu.</div>
      ) : (
        <>
          <div className="hero-stats">
            <div className="hero-stat hero-stat--primary">
              <div className="hero-stat__head">
                <span className="hero-stat__label">{ron95?.name ?? "Xăng RON 95"}</span>
                <strong>{ron95 ? `${fmtPrice(ron95.zone1, "VND")} đ` : "—"}</strong>
              </div>
              {ron95 && (
                <span className={`chip chip--${tone(ron95.change)}`}>
                  {ron95.change !== 0 ? `${fmtSigned(ron95.change, "VND")} đ/lít` : "Không đổi"}
                </span>
              )}
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">{e5?.name ?? "Xăng E5 RON 92"}</span>
              <strong>{e5 ? fmtPrice(e5.zone1, "VND") : "—"}</strong>
              <span className="hero-stat__hint">Vùng 1 · đ/lít</span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">{diesel?.name ?? "Dầu DO"}</span>
              <strong>{diesel ? fmtPrice(diesel.zone1, "VND") : "—"}</strong>
              <span className="hero-stat__hint">Vùng 1 · đ/lít</span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">Mặt hàng</span>
              <strong>{items.length} loại</strong>
              <span className="hero-stat__hint">Vùng 1 & Vùng 2</span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">Nguồn niêm yết</span>
              <strong>{fuel.source}</strong>
              <span className="hero-stat__hint">Bán lẻ trong nước</span>
            </div>
          </div>

          <section className="panel panel--table">
            <div className="panel__head">
              <span className="panel__title">Bảng giá xăng dầu · {fuel.source}</span>
              <span className="meta">ĐƠN VỊ: ĐỒNG / LÍT</span>
            </div>
            <div className="gold-table-wrap">
              <table className="gold-table">
                <thead>
                  <tr>
                    <th>Mặt hàng</th>
                    <th className="num">Vùng 1</th>
                    <th className="num">Vùng 2</th>
                    <th className="num gt-spread">Chênh Vùng 2–1</th>
                    <th className="num gt-change">Thay đổi</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((f) => {
                    const diff = f.zone2 != null ? f.zone2 - f.zone1 : null;
                    const t = tone(f.change);
                    return (
                      <tr key={f.name}>
                        <td className="gt-col-name">
                          <span className="gt-name">{f.name}</span>
                        </td>
                        <td className="num bid">
                          {fmtPrice(f.zone1, "VND")}
                          {f.change !== 0 && (
                            <span className={`gt-inline-chg ${t}`}>
                              {fmtSigned(f.change, "VND")}
                            </span>
                          )}
                        </td>
                        <td className="num ask">
                          {f.zone2 != null ? fmtPrice(f.zone2, "VND") : "—"}
                        </td>
                        <td className="num muted gt-spread">
                          {diff != null ? `+${fmtPrice(diff, "VND")}` : "—"}
                        </td>
                        <td className={`num ${t} gt-change`}>
                          {f.change !== 0 ? fmtSigned(f.change, "VND") : "0"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export function FxPage() {
  const { data, loading, error, refresh } = useExtras();
  const [query, setQuery] = useState("");
  const now = useNow(5000);

  const fx = data?.fx ?? null;
  const items = useMemo(() => fx?.items ?? [], [fx]);
  const age = ageSeconds(fx?.ts ?? null, now);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (c) => c.code.toLowerCase().includes(q) || c.name.toLowerCase().includes(q),
    );
  }, [items, query]);

  const usd = items.find((c) => c.code === "USD");
  const eur = items.find((c) => c.code === "EUR");
  const gbp = items.find((c) => c.code === "GBP");
  const jpy = items.find((c) => c.code === "JPY");

  return (
    <div className="page">
      <MarketTabs />

      <div className="hero">
        <div>
          <h1 className="hero__title">Tỷ giá ngoại tệ</h1>
          <p className="hero__sub">
            Tỷ giá mua tiền mặt, mua chuyển khoản và bán ra quy đổi VND ({fx?.source ?? "Ngân hàng"}).
          </p>
        </div>
        <div className="hero__actions">
          {age !== null && <span className="meta">Cập nhật {fmtAgo(age)}</span>}
          <button className="btn btn--ghost" onClick={() => void refresh()}>
            Làm mới
          </button>
        </div>
      </div>

      {loading && !data ? (
        <>
          <HeroStatsSkeleton />
          <TablePanelSkeleton rows={8} />
        </>
      ) : error && !data ? (
        <div className="empty">{error}</div>
      ) : !fx ? (
        <div className="empty">Chưa có dữ liệu ngoại tệ.</div>
      ) : (
        <>
          <div className="hero-stats">
            <div className="hero-stat hero-stat--primary">
              <div className="hero-stat__head">
                <span className="hero-stat__label">USD bán ra</span>
                <strong>{usd?.sell != null ? `${fmtFx(usd.sell)} đ` : "—"}</strong>
              </div>
              <span className="chip chip--flat">
                Mua CK {usd?.transfer != null ? fmtFx(usd.transfer) : "—"}
              </span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">EUR bán ra</span>
              <strong>{fmtFx(eur?.sell ?? null)}</strong>
              <span className="hero-stat__hint">Mua {fmtFx(eur?.buy ?? null)}</span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">GBP bán ra</span>
              <strong>{fmtFx(gbp?.sell ?? null)}</strong>
              <span className="hero-stat__hint">Mua {fmtFx(gbp?.buy ?? null)}</span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">JPY bán ra</span>
              <strong>{fmtFx(jpy?.sell ?? null)}</strong>
              <span className="hero-stat__hint">Mua {fmtFx(jpy?.buy ?? null)}</span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">Đang niêm yết</span>
              <strong>{items.length} đồng</strong>
              <span className="hero-stat__hint">Nguồn {fx.source}</span>
            </div>
          </div>

          <section className="panel panel--table">
            <div className="panel__head">
              <span className="panel__title">Bảng tỷ giá ngoại tệ</span>
              <span className="meta">
                {filtered.length}/{items.length} ngoại tệ · ĐƠN VỊ: VND
              </span>
            </div>
            <div className="filter-bar">
              <input
                type="search"
                placeholder="Tìm mã hoặc tên ngoại tệ (USD, EUR, JPY…)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Tìm ngoại tệ"
              />
              {query && (
                <button className="btn btn--ghost" onClick={() => setQuery("")}>
                  Xóa lọc
                </button>
              )}
            </div>
            <div className="gold-table-wrap">
              <table className="gold-table">
                <thead>
                  <tr>
                    <th className="gt-col-brand">Mã</th>
                    <th>Ngoại tệ</th>
                    <th className="num">Mua tiền mặt</th>
                    <th className="num gt-spread">Mua chuyển khoản</th>
                    <th className="num">Bán ra</th>
                    <th className="num gt-change">Chênh lệch</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((c) => {
                    const spread = c.buy != null && c.sell != null ? c.sell - c.buy : null;
                    return (
                      <tr key={c.code}>
                        <td className="gt-brand gt-col-brand">
                          <b>{c.code}</b>
                        </td>
                        <td className="gt-col-name">
                          <span className="gt-name">{c.code}</span>
                          <span className="gt-code">{c.name}</span>
                        </td>
                        <td className="num bid">
                          {fmtFx(c.buy)}
                          {c.transfer != null && (
                            <span className="gt-inline-chg muted">CK {fmtFx(c.transfer)}</span>
                          )}
                        </td>
                        <td className="num ask gt-spread">{fmtFx(c.transfer)}</td>
                        <td className="num ask">{fmtFx(c.sell)}</td>
                        <td className="num muted gt-change">
                          {spread != null ? fmtFx(spread) : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {filtered.length === 0 && (
              <div className="empty" style={{ padding: 18 }}>
                Không có ngoại tệ khớp “{query}”.
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

const IDX_NUM = new Intl.NumberFormat("vi-VN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function fmtSignedNum(v: number): string {
  const s = IDX_NUM.format(Math.abs(v));
  if (v > 0) return `+${s}`;
  if (v < 0) return `-${s}`;
  return "0";
}

function fmtVol(v: number | null): string {
  if (v == null || !Number.isFinite(v)) return "—";
  if (v >= 1e6) return `${(v / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} triệu`;
  return v.toLocaleString("vi-VN");
}

export function MarketPage() {
  const { data, loading, error, refresh } = useExtras();
  const now = useNow(5000);

  const indices = data?.indices ?? null;
  const crypto = data?.crypto ?? null;
  const oil = data?.oil ?? null;
  const globalIdx = data?.global ?? null;
  const rates = data?.rates ?? null;

  const newestTs = Math.max(
    indices?.ts ?? 0,
    crypto?.ts ?? 0,
    oil?.ts ?? 0,
    globalIdx?.ts ?? 0,
    rates?.ts ?? 0,
  );
  const age = ageSeconds(newestTs > 0 ? newestTs : null, now);
  const hasAny = Boolean(indices || crypto || oil || globalIdx || rates);
  const vni = indices?.items.find((i) => i.code === "VNINDEX");
  const btc = crypto?.items.find((c) => c.code === "BTC");
  const brent = oil?.items.find((o) => o.code === "BRENT");
  const dxy = globalIdx?.items.find((g) => g.code === "DXY");

  const rateMax = useMemo(() => {
    const max: Record<string, number> = {};
    for (const item of rates?.items ?? []) {
      for (const term of rates?.terms ?? []) {
        const v = item.rates[term];
        if (v != null && (max[term] == null || v > max[term])) max[term] = v;
      }
    }
    return max;
  }, [rates]);
  const best12 = useMemo(() => {
    let best: { name: string; value: number } | null = null;
    for (const item of rates?.items ?? []) {
      const v = item.rates["12"];
      if (v != null && (!best || v > best.value)) best = { name: item.name, value: v };
    }
    return best;
  }, [rates]);

  return (
    <div className="page">
      <MarketTabs />

      <div className="hero">
        <div>
          <h1 className="hero__title">Thị trường tổng hợp</h1>
          <p className="hero__sub">
            Chỉ số chứng khoán Việt Nam, tiền số, dầu thô thế giới và các chỉ số toàn cầu tác động tới giá vàng.
          </p>
        </div>
        <div className="hero__actions">
          {age !== null && <span className="meta">Cập nhật {fmtAgo(age)}</span>}
          <button className="btn btn--ghost" onClick={() => void refresh()}>
            Làm mới
          </button>
        </div>
      </div>

      {loading && !data ? (
        <>
          <HeroStatsSkeleton />
          <TablePanelSkeleton rows={6} />
        </>
      ) : error && !data ? (
        <div className="empty">{error}</div>
      ) : !hasAny ? (
        <div className="empty">Chưa có dữ liệu thị trường.</div>
      ) : (
        <>
          <div className="hero-stats">
            <div className="hero-stat hero-stat--primary">
              <div className="hero-stat__head">
                <span className="hero-stat__label">VN-Index</span>
                <strong>{vni ? IDX_NUM.format(vni.close) : "—"}</strong>
              </div>
              {vni && (
                <span className={`chip chip--${tone(vni.change)}`}>
                  {fmtSignedNum(vni.change)} ({fmtPct(vni.change_pct)})
                </span>
              )}
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">Bitcoin</span>
              <strong>{btc ? `${fmtPrice(btc.usd, "USD")} $` : "—"}</strong>
              {btc && (
                <span className={`chip chip--${tone(btc.change_24h)}`}>{fmtPct(btc.change_24h)} / 24h</span>
              )}
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">Dầu Brent</span>
              <strong>{brent ? `${fmtPrice(brent.price, "USD")} $` : "—"}</strong>
              <span className="hero-stat__hint">USD / thùng</span>
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">Chỉ số USD (DXY)</span>
              <strong>{dxy ? IDX_NUM.format(dxy.value) : "—"}</strong>
              {dxy && (
                <span className={`chip chip--${tone(dxy.change_abs)}`}>
                  {fmtSignedNum(dxy.change_abs)} ({fmtPct(dxy.change_pct)})
                </span>
              )}
            </div>

            <div className="hero-stat">
              <span className="hero-stat__label">Tiết kiệm 12 tháng cao nhất</span>
              <strong>{best12 ? `${IDX_NUM.format(best12.value)}%` : "—"}</strong>
              <span className="hero-stat__hint">{best12 ? `${best12.name} · %/năm tại quầy` : "Lãi suất ngân hàng"}</span>
            </div>
          </div>

          {indices && (
            <section className="panel panel--table">
              <div className="panel__head">
                <span className="panel__title">Chứng khoán Việt Nam · {indices.source}</span>
                <span className="meta">PHIÊN GẦN NHẤT</span>
              </div>
              <div className="gold-table-wrap">
                <table className="gold-table">
                  <thead>
                    <tr>
                      <th>Chỉ số</th>
                      <th className="num">Điểm</th>
                      <th className="num">Thay đổi</th>
                      <th className="num gt-change">%</th>
                      <th className="num gt-spread">Khối lượng</th>
                    </tr>
                  </thead>
                  <tbody>
                    {indices.items.map((ix) => {
                      const t = tone(ix.change);
                      return (
                        <tr key={ix.code}>
                          <td className="gt-col-name">
                            <span className="gt-name">{ix.name}</span>
                          </td>
                          <td className="num bid">{IDX_NUM.format(ix.close)}</td>
                          <td className={`num ${t}`}>{fmtSignedNum(ix.change)}</td>
                          <td className={`num ${t} gt-change`}>{fmtPct(ix.change_pct)}</td>
                          <td className="num muted gt-spread">{fmtVol(ix.volume)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {crypto && (
            <section className="panel panel--table">
              <div className="panel__head">
                <span className="panel__title">Tiền số · {crypto.source}</span>
                <span className="meta">BIẾN ĐỘNG 24H</span>
              </div>
              <div className="gold-table-wrap">
                <table className="gold-table">
                  <thead>
                    <tr>
                      <th>Đồng</th>
                      <th className="num">Giá USD</th>
                      <th className="num">Giá VND</th>
                      <th className="num gt-change">24h</th>
                    </tr>
                  </thead>
                  <tbody>
                    {crypto.items.map((c) => {
                      const t = tone(c.change_24h);
                      return (
                        <tr key={c.code}>
                          <td className="gt-col-name">
                            <span className="gt-name">
                              {c.name} · {c.code}
                            </span>
                          </td>
                          <td className="num bid">{fmtPrice(c.usd, "USD")} $</td>
                          <td className="num ask">{c.vnd != null ? fmtPrice(c.vnd, "VND") : "—"}</td>
                          <td className={`num ${t} gt-change`}>{fmtPct(c.change_24h)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {oil && (
            <section className="panel panel--table">
              <div className="panel__head">
                <span className="panel__title">Dầu thô thế giới · {oil.source}</span>
                <span className="meta">USD / THÙNG</span>
              </div>
              <div className="gold-table-wrap">
                <table className="gold-table">
                  <thead>
                    <tr>
                      <th>Loại dầu</th>
                      <th className="num">Giá</th>
                      <th className="num">Thay đổi</th>
                      <th className="num gt-change">%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {oil.items.map((o) => {
                      const t = tone(o.change_abs);
                      return (
                        <tr key={o.code}>
                          <td className="gt-col-name">
                            <span className="gt-name">{o.name}</span>
                          </td>
                          <td className="num bid">{fmtPrice(o.price, "USD")} $</td>
                          <td className={`num ${t}`}>{fmtSigned(o.change_abs, "USD")}</td>
                          <td className={`num ${t} gt-change`}>{fmtPct(o.change_pct)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {globalIdx && (
            <section className="panel panel--table">
              <div className="panel__head">
                <span className="panel__title">Chỉ số toàn cầu · {globalIdx.source}</span>
                <span className="meta">TÁC ĐỘNG TỚI VÀNG</span>
              </div>
              <div className="gold-table-wrap">
                <table className="gold-table">
                  <thead>
                    <tr>
                      <th>Chỉ số</th>
                      <th className="num">Giá trị</th>
                      <th className="num">Thay đổi</th>
                      <th className="num gt-change">%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {globalIdx.items.map((g) => {
                      const t = tone(g.change_abs);
                      return (
                        <tr key={g.code}>
                          <td className="gt-col-name">
                            <span className="gt-name">{g.name}</span>
                          </td>
                          <td className="num bid">
                            {IDX_NUM.format(g.value)}
                            {g.unit}
                          </td>
                          <td className={`num ${t}`}>{fmtSignedNum(g.change_abs)}</td>
                          <td className={`num ${t} gt-change`}>{fmtPct(g.change_pct)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {rates && (
            <section className="panel panel--table">
              <div className="panel__head">
                <span className="panel__title">Lãi suất tiết kiệm · {rates.source}</span>
                <span className="meta">%/NĂM · Ô ĐẬM = CAO NHẤT KỲ HẠN</span>
              </div>
              <div className="gold-table-wrap">
                <table className="gold-table">
                  <thead>
                    <tr>
                      <th>Ngân hàng</th>
                      {rates.terms.map((term) => (
                        <th key={term} className="num">
                          {term === "KKH" ? "KKH" : `${term}T`}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rates.items.map((item) => (
                      <tr key={item.code}>
                        <td className="gt-col-name">
                          <span className="gt-name">{item.name}</span>
                        </td>
                        {rates.terms.map((term) => {
                          const v = item.rates[term];
                          const isBest = v != null && rateMax[term] != null && v === rateMax[term];
                          return (
                            <td key={term} className={`num${isBest ? " rate-best" : ""}`}>
                              {v != null ? IDX_NUM.format(v) : "—"}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
