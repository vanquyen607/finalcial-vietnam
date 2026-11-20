import { Link } from "react-router-dom";
import { changePct, fmtPct, fmtPrice, fmtSigned, tone } from "../lib/format";
import { useExtras } from "../lib/useExtras";

/**
 * Dải tóm tắt nhanh: Bạc, Xăng dầu, Ngoại tệ — bấm vào từng thẻ để mở trang chi tiết riêng.
 */
export default function MarketStrip() {
  const { data } = useExtras();

  if (
    !data ||
    (!data.silver && !data.silver_domestic && !data.fx && !data.fuel && !data.indices && !data.crypto)
  )
    return null;
  const { silver, silver_domestic: silverVn, fx, fuel } = data;
  const vni = data.indices?.items.find((i) => i.code === "VNINDEX");
  const btc = data.crypto?.items.find((c) => c.code === "BTC");
  const domestic = silverVn?.items ?? [];
  const headlineSilver =
    domestic.find((i) => i.brand === "DOJI" && i.sell) ?? domestic.find((i) => i.sell);
  const headlineFuel = fuel?.items.find((i) => i.name.includes("95")) ?? fuel?.items[0];
  const usd = fx?.items.find((c) => c.code === "USD") ?? fx?.items[0];

  return (
    <section className="extras" aria-label="Bạc, xăng dầu và ngoại tệ">
      {(silver || domestic.length > 0) && (
        <Link to="/silver" className="panel extras__card extras__card--link">
          <div className="panel__head">
            <span className="panel__title">Bạc</span>
            <span className="meta">XEM TRANG BẠC →</span>
          </div>
          <div className="panel__body">
            {silver ? (
              <>
                <div className="extras__big">
                  <strong>{fmtPrice(silver.price_usd, "USD")}</strong>
                  <span className="meta">USD/oz</span>
                  <span className={`chip chip--${tone(silver.change_usd)}`}>
                    {fmtSigned(silver.change_usd, "USD")} ({fmtPct(changePct(silver.price_usd, silver.change_usd))})
                  </span>
                </div>
                <p className="meta extras__note">
                  {headlineSilver?.sell
                    ? `${headlineSilver.brand}: ${fmtPrice(headlineSilver.sell, "VND")} đ/lượng · ${domestic.length} sản phẩm`
                    : `${domestic.length} sản phẩm trong nước`}
                </p>
              </>
            ) : (
              <div className="extras__big">
                <strong>{headlineSilver?.sell ? fmtPrice(headlineSilver.sell, "VND") : "—"}</strong>
                <span className="meta">đ/lượng</span>
              </div>
            )}
          </div>
        </Link>
      )}

      {fuel && headlineFuel && (
        <Link to="/fuel" className="panel extras__card extras__card--link">
          <div className="panel__head">
            <span className="panel__title">Xăng dầu · {fuel.source}</span>
            <span className="meta">XEM BẢNG GIÁ →</span>
          </div>
          <div className="panel__body">
            <div className="extras__big">
              <strong>{fmtPrice(headlineFuel.zone1, "VND")}</strong>
              <span className="meta">đ/lít</span>
              {headlineFuel.change !== 0 && (
                <span className={`chip chip--${tone(headlineFuel.change)}`}>
                  {fmtSigned(headlineFuel.change, "VND")}
                </span>
              )}
            </div>
            <p className="meta extras__note">
              {headlineFuel.name} (Vùng 1) · {fuel.items.length} mặt hàng
            </p>
          </div>
        </Link>
      )}

      {vni && (
        <Link to="/market" className="panel extras__card extras__card--link">
          <div className="panel__head">
            <span className="panel__title">Thị trường · VN-Index</span>
            <span className="meta">XEM TỔNG HỢP →</span>
          </div>
          <div className="panel__body">
            <div className="extras__big">
              <strong>
                {vni.close.toLocaleString("vi-VN", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </strong>
              <span className="meta">điểm</span>
              <span className={`chip chip--${tone(vni.change)}`}>{fmtPct(vni.change_pct)}</span>
            </div>
            <p className="meta extras__note">
              {btc
                ? `BTC ${fmtPrice(btc.usd, "USD")} $ · Chứng khoán, crypto, dầu thô, DXY`
                : "Chứng khoán, crypto, dầu thô, DXY"}
            </p>
          </div>
        </Link>
      )}

      {fx && usd && (
        <Link to="/fx" className="panel extras__card extras__card--link">
          <div className="panel__head">
            <span className="panel__title">Ngoại tệ · {usd.code}</span>
            <span className="meta">XEM TỶ GIÁ →</span>
          </div>
          <div className="panel__body">
            <div className="extras__big">
              <strong>{usd.sell != null ? fmtPrice(usd.sell, "VND") : "—"}</strong>
              <span className="meta">VND bán ra</span>
            </div>
            <p className="meta extras__note">
              Mua vào {usd.buy != null ? fmtPrice(usd.buy, "VND") : "—"} · {fx.items.length} đồng ngoại tệ
            </p>
          </div>
        </Link>
      )}
    </section>
  );
}
