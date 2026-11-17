import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { TechnicalsPayload } from "../lib/types";

/** Đồng hồ sức mua/bán vàng thế giới — điểm Recommend gốc của TradingView
 * (tổng hợp RSI, MACD, MA…), vẽ native theo theme của app. */

const TFS: { key: string; label: string }[] = [
  { key: "60", label: "1 giờ" },
  { key: "240", label: "4 giờ" },
  { key: "1D", label: "Ngày" },
];

const SEG_COLORS = [
  "var(--down)",
  "color-mix(in srgb, var(--down) 55%, var(--paper))",
  "var(--ink-rule)",
  "color-mix(in srgb, var(--up) 55%, var(--paper))",
  "var(--up)",
];
const SEG_LABELS = ["Bán mạnh", "Bán", "Trung lập", "Mua", "Mua mạnh"];

export function ratingOf(v: number): { key: string; label: string } {
  if (v <= -0.5) return { key: "strong_sell", label: "Bán mạnh" };
  if (v < -0.1) return { key: "sell", label: "Bán" };
  if (v <= 0.1) return { key: "neutral", label: "Trung lập" };
  if (v < 0.5) return { key: "buy", label: "Mua" };
  return { key: "strong_buy", label: "Mua mạnh" };
}

function ratingColor(key: string): string {
  switch (key) {
    case "strong_sell":
      return "var(--down)";
    case "sell":
      return "color-mix(in srgb, var(--down) 70%, var(--ink))";
    case "buy":
      return "color-mix(in srgb, var(--up) 75%, var(--ink))";
    case "strong_buy":
      return "var(--up)";
    default:
      return "var(--ink-2)";
  }
}

/** Cung tròn từ góc a0→a1 (độ, 180 = trái, 0 = phải) trên nửa vòng tròn. */
function arcPath(cx: number, cy: number, r: number, a0: number, a1: number): string {
  const p = (a: number) => {
    const rad = (a * Math.PI) / 180;
    return [cx + r * Math.cos(rad), cy - r * Math.sin(rad)];
  };
  const [x0, y0] = p(a0);
  const [x1, y1] = p(a1);
  return `M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${r} ${r} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`;
}

function Meter({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null;
  const r = ratingOf(value);
  const left = ((value + 1) / 2) * 100;
  return (
    <div className="gauge-meter">
      <span className="gauge-meter__name">{label}</span>
      <span className="gauge-meter__track">
        <span
          className="gauge-meter__mark"
          style={{ left: `${left}%`, background: ratingColor(r.key) }}
        />
      </span>
      <span className="gauge-meter__val" style={{ color: ratingColor(r.key) }}>
        {r.label}
      </span>
    </div>
  );
}

export function useTechnicals(): TechnicalsPayload | null {
  const [data, setData] = useState<TechnicalsPayload | null>(null);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const d = await api.technicals();
        if (alive) setData(d);
      } catch {
        /* giữ bản cũ; lần tải sau thử lại */
      }
    };
    load();
    const t = window.setInterval(load, 60_000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, []);
  return data;
}

export default function TechGauge({ compact = false }: { compact?: boolean }) {
  const data = useTechnicals();
  const [tf, setTf] = useState("1D");

  if (!data) return <div className="empty">Đang tải chỉ số kỹ thuật…</div>;
  const frame = data.frames[tf] ?? data.frames["1D"];
  if (!frame) return <div className="empty">Chưa có dữ liệu kỹ thuật.</div>;

  // value −1…+1 -> góc kim 180°…0°
  const angle = 180 - ((frame.all + 1) / 2) * 180;
  const rad = (angle * Math.PI) / 180;
  const cx = 100;
  const cy = 96;
  const needleLen = 58;
  const nx = cx + needleLen * Math.cos(rad);
  const ny = cy - needleLen * Math.sin(rad);
  const color = ratingColor(frame.rating);

  return (
    <div className="gauge">
      {!compact && (
        <div className="range-tabs" style={{ justifyContent: "center", marginBottom: 6 }}>
          {TFS.map((t) => (
            <button key={t.key} data-active={tf === t.key} onClick={() => setTf(t.key)}>
              {t.label}
            </button>
          ))}
        </div>
      )}
      <svg className="gauge__svg" viewBox="-20 -20 240 140" role="img" aria-label={frame.label}>
        {SEG_COLORS.map((c, i) => (
          <path
            key={i}
            d={arcPath(cx, cy, 78, 180 - i * 36, 180 - (i + 1) * 36 + 2)}
            fill="none"
            stroke={c}
            strokeWidth={13}
            strokeLinecap="round"
            opacity={frame.rating === ["strong_sell", "sell", "neutral", "buy", "strong_buy"][i] ? 1 : 0.38}
          />
        ))}
        <line x1={cx} y1={cy} x2={nx.toFixed(1)} y2={ny.toFixed(1)} stroke="var(--ink)" strokeWidth={3} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={5.5} fill="var(--ink)" />
        {SEG_LABELS.map((s, i) => {
          const a = ((180 - (i * 36 + 18)) * Math.PI) / 180;
          const tx = cx + 97 * Math.cos(a);
          const ty = cy - 97 * Math.sin(a);
          return (
            <text key={s} x={tx.toFixed(1)} y={(ty + 3).toFixed(1)} textAnchor="middle" className="gauge__seg-label">
              {s}
            </text>
          );
        })}
      </svg>
      <div className="gauge__label" style={{ color }}>
        {frame.label}
        <span className="gauge__value">{frame.all > 0 ? "+" : ""}{frame.all.toFixed(2)}</span>
      </div>
      {!compact && (
        <div className="gauge__sub">
          <Meter label="Chỉ báo dao động" value={frame.other} />
          <Meter label="Đường trung bình" value={frame.ma} />
        </div>
      )}
      <p className="meta" style={{ marginTop: 8 }}>
        Khung {TFS.find((t) => t.key === tf)?.label ?? tf} · TradingView
        {data.stale ? " · dữ liệu cũ" : ""}
      </p>
    </div>
  );
}
