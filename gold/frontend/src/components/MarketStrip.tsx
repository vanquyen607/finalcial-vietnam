import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { changePct, fmtPct, fmtPrice, fmtSigned, tone } from "../lib/format";
import type { ExtrasPayload } from "../lib/types";

/**
 * Dải thị trường phụ: bạc thế giới, giá xăng dầu, tỷ giá ngoại tệ.
 * Dữ liệu từ /api/extras (backend cache theo nguồn); lỗi thì ẩn cả dải,
 * không ảnh hưởng bảng giá vàng chính.
 */
export default function MarketStrip() {
  const [data, setData] = useState<ExtrasPayload | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api
        .extras()
        .then((d) => {
          if (alive) setData(d);
        })
        .catch(() => {
          /* nguồn phụ lỗi -> ẩn dải, trang chính vẫn chạy */
        });
    void load();
    const id = window.setInterval(load, 120_000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  if (!data || (!data.silver && !data.silver_domestic && !data.fx && !data.fuel)) return null;
  const { silver, silver_domestic: silverVn, fx, fuel } = data;
  const domestic = silverVn?.items ?? [];
  const headline = domestic.find((i) => i.brand === "DOJI" && i.sell) ?? domestic.find((i) => i.sell);
  const premium =
    headline?.sell && silver?.vnd_per_luong
      ? (headline.sell / silver.vnd_per_luong - 1) * 100
      : null;

  return (
    <section className="extras" aria-label="Bạc, xăng dầu và ngoại tệ">
      {(silver || domestic.length > 0) && (
        <div className="panel extras__card">
          <div className="panel__head">
            <span className="panel__title">Bạc</span>
            {silver && <span className="meta">{silver.source}</span>}
          </div>
          <div className="panel__body">
            {silver && (
              <>
                <div className="extras__big">
                  <strong>{fmtPrice(silver.price_usd, "USD")}</strong>
                  <span className="meta">USD/oz</span>
                  <span className={`chip chip--${tone(silver.change_usd)}`}>
                    {fmtSigned(silver.change_usd, "USD")} ({fmtPct(changePct(silver.price_usd, silver.change_usd))})
                  </span>
                </div>
                {silver.vnd_per_luong != null && (
                  <p className="meta extras__note">
                    Thế giới quy đổi ≈ {fmtPrice(silver.vnd_per_luong, "VND")} đ/lượng
                    {premium != null && headline && (
                      <> · {headline.brand} bán ra cao hơn {premium.toFixed(1).replace(".", ",")}%</>
                    )}
                  </p>
                )}
              </>
            )}
            {domestic.length > 0 && (
              <div className="extras__rows extras__rows--silver">
                {domestic.map((s) => (
                  <div key={`${s.brand}-${s.name}`} className="extras__row">
                    <span>
                      {s.name} <span className="meta">· {s.brand}</span>
                    </span>
                    <span className="extras__val">
                      {s.change != null && s.change !== 0 && (
                        <i className={tone(s.change)}>
                          {s.change > 0 ? "▲" : "▼"} {fmtPrice(Math.abs(s.change), "VND")}
                        </i>
                      )}
                      {s.buy != null && <span className="meta">mua {fmtPrice(s.buy, "VND")}</span>}
                      {s.sell != null && <b>{fmtPrice(s.sell, "VND")}</b>}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {fuel && (
        <div className="panel extras__card">
          <div className="panel__head">
            <span className="panel__title">Xăng dầu · Vùng 1</span>
            <span className="meta">{fuel.source} · đ/lít</span>
          </div>
          <div className="panel__body extras__rows">
            {fuel.items.map((f) => (
              <div key={f.name} className="extras__row">
                <span>{f.name}</span>
                <span className="extras__val">
                  {f.change !== 0 && (
                    <i className={tone(f.change)}>
                      {f.change > 0 ? "▲" : "▼"} {fmtPrice(Math.abs(f.change), "VND")}
                    </i>
                  )}
                  <b>{fmtPrice(f.zone1, "VND")}</b>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {fx && (
        <div className="panel extras__card">
          <div className="panel__head">
            <span className="panel__title">Ngoại tệ</span>
            <span className="meta">{fx.source} · mua / bán</span>
          </div>
          <div className="panel__body extras__rows">
            {fx.items.slice(0, 8).map((c) => (
              <div key={c.code} className="extras__row">
                <span>
                  <b>{c.code}</b>
                </span>
                <span className="extras__val">
                  <span>{c.buy != null ? fmtPrice(c.buy, "VND") : "—"}</span>
                  <b>{c.sell != null ? fmtPrice(c.sell, "VND") : "—"}</b>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
