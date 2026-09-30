import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import PriceChart from "../components/PriceChart";
import TradingViewOverview from "../components/TradingViewOverview";
import { tvTabsFor } from "../lib/tradingview";
import { useMarket } from "../state/Market";

type Mode = "aurum" | "tv";

export default function ChartPage() {
  const [params, setParams] = useSearchParams();
  const { symbols } = useMarket();
  const active = params.get("m") ?? "sjc";

  const code = symbols.find((s) => s.alias === active || s.code === active)?.code;
  const tvTabs = tvTabsFor(code);

  // Mặc định mở tab TradingView nếu mã có dữ liệu trên đó (chỉ XAUUSD);
  // tự reset mỗi khi đổi mã.
  const [mode, setMode] = useState<Mode | null>(null);
  useEffect(() => setMode(null), [code]);
  const effective: Mode = mode ?? (tvTabs ? "tv" : "aurum");

  const pick = (alias: string) => setParams({ m: alias });

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page__title">Biểu đồ giá vàng</h1>
          <p className="page__sub">
            {tvTabs
              ? "Tab TradingView: biểu đồ chuyên sâu của TradingView · Tab Aurum: giá mua/bán realtime của app"
              : "Đường màu sáng là giá mua vào (realtime), đường đứt nét vàng là giá bán ra · kéo/zoom bằng chuột"}
          </p>
        </div>
        {tvTabs && (
          <div className="range-tabs" style={{ marginBottom: 0 }}>
            <button data-active={effective === "aurum"} onClick={() => setMode("aurum")}>
              Aurum
            </button>
            <button data-active={effective === "tv"} onClick={() => setMode("tv")}>
              TradingView
            </button>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel__head">
          <span className="panel__title">Phân tích kỹ thuật giá vàng</span>
          <span className="meta">
            {effective === "tv" ? "DỮ LIỆU TRADINGVIEW" : "DỮ LIỆU 30 NGÀY · CẬP NHẬT THEO TICK"}
          </span>
        </div>
        <div className="panel__body">
          {effective === "tv" && tvTabs ? (
            <div>
              <div className="range-tabs">
                {symbols.map((s) => (
                  <button
                    key={s.code}
                    data-active={active === s.alias || active === s.code}
                    onClick={() => pick(s.alias)}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
              <TradingViewOverview
                symbol={tvTabs[0].tv}
                watchlist={tvTabs.slice(1).map((t) => t.tv)}
                height={520}
              />
            </div>
          ) : (
            <PriceChart
              symbol={active}
              onSymbolChange={pick}
              defaultRange="30d"
              height={420}
            />
          )}
        </div>
      </div>
    </div>
  );
}
