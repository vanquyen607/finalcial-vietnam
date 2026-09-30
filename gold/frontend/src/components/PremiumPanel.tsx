import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fmtAgo, fmtPct, fmtPrice, fmtSigned } from "../lib/format";
import { ageSeconds, useNow } from "../lib/useNow";

interface PremiumData {
  ts: number;
  sjc: { name: string; sell: number; source: string };
  xau: { buy: number; source: string };
  fx: { usd_vnd: number; source: string; ts: number };
  world_vnd_luong: number;
  gap_abs: number;
  gap_pct: number;
}

/** Chênh lệch giá SJC trong nước so với thế giới quy đổi VND/lượng. */
export default function PremiumPanel() {
  const [data, setData] = useState<PremiumData | null>(null);
  const now = useNow(1000);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const res = await fetch("/api/premium");
        if (!res.ok) return;
        const json = (await res.json()) as PremiumData;
        if (alive) setData(json);
      } catch {
        /* tính năng phụ — lỗi thì ẩn panel */
      }
    };
    void load();
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, 60_000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  if (!data) return null;
  const fxAge = ageSeconds(data.fx.ts, now);

  return (
    <section className="panel">
      <div className="panel__head">
        <span className="panel__title">Chênh lệch SJC – thế giới</span>
        <span className="meta">
          USD/VND {Math.round(data.fx.usd_vnd).toLocaleString("vi-VN")}
          {fxAge !== null ? ` · TỶ GIÁ ${fmtAgo(fxAge).toUpperCase()}` : ""}
        </span>
      </div>
      <div className="panel__body">
        <div className="stat-grid">
          <div className="stat">
            <div className="stat__k">SJC cao hơn thế giới</div>
            <div className={`stat__v ${data.gap_abs >= 0 ? "up" : "down"}`}>
              {fmtSigned(data.gap_abs, "VND")} · {fmtPct(data.gap_pct)}
            </div>
          </div>
          <div className="stat">
            <div className="stat__k">{data.sjc.name} bán ra</div>
            <div className="stat__v">{fmtPrice(data.sjc.sell, "VND")}</div>
          </div>
          <div className="stat">
            <div className="stat__k">Thế giới quy đổi /lượng</div>
            <div className="stat__v">{fmtPrice(data.world_vnd_luong, "VND")}</div>
          </div>
        </div>
        <p className="meta" style={{ marginTop: 12 }}>
          TG QUY ĐỔI = XAU/USD × USD/VND × 1,20565 (1 LƯỢNG = 1,20565 OUNCE) ·{" "}
          <Link to="/chart?m=xauusd" className="meta">
            XEM BIỂU ĐỒ THẾ GIỚI →
          </Link>
        </p>
      </div>
    </section>
  );
}
