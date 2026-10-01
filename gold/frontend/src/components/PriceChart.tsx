import { useEffect, useMemo, useState } from "react";
import ChartView from "./ChartView";
import type { ChartPoint } from "./ChartView";
import { api } from "../lib/api";
import { changePct, fmtPct, fmtPrice, fmtSigned } from "../lib/format";
import { basePoints, mergeLive, useLiveSeries } from "../lib/useLiveSeries";
import type { HistoryPayload } from "../lib/types";
import { useMarket } from "../state/Market";

type Range = "24h" | "7d" | "30d";

const RANGES: { key: Range; label: string }[] = [
  { key: "24h", label: "24 giờ" },
  { key: "7d", label: "7 ngày" },
  { key: "30d", label: "30 ngày" },
];

interface Props {
  /** Mã kim loại (alias hoặc code) — điều khiển từ ngoài nếu truyền vào */
  symbol?: string;
  onSymbolChange?: (alias: string) => void;
  defaultRange?: Range;
  height?: number;
  /** Ẩn tiêu đề + bộ chọn mã (dùng trong bảng điều khiển nhỏ) */
  compact?: boolean;
}

export default function PriceChart({
  symbol,
  onSymbolChange,
  defaultRange = "24h",
  height = 300,
  compact = false,
}: Props) {
  const { symbols, quotes } = useMarket();
  const [local, setLocal] = useState(symbol ?? "sjc");
  const [range, setRange] = useState<Range>(defaultRange);
  const [hist, setHist] = useState<HistoryPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const active = symbol ?? local;
  const pick = (alias: string) => {
    setLocal(alias);
    onSymbolChange?.(alias);
  };

  useEffect(() => {
    if (!symbols.length) return;
    let alive = true;
    setHist(null);
    setError(null);
    (async () => {
      try {
        const data = await api.history(active, 30);
        if (alive) setHist(data);
      } catch (e) {
        if (alive) setError(String(e));
      }
    })();
    return () => {
      alive = false;
    };
  }, [active, symbols.length]);

  const meta = useMemo(
    () => symbols.find((s) => s.alias === active || s.code === active),
    [symbols, active],
  );
  const quote = meta ? quotes[meta.code] : undefined;
  const unit = quote?.unit ?? meta?.unit ?? "VND";

  const live = useLiveSeries(quote, range === "24h" ? "intraday" : "daily");

  const points: ChartPoint[] = useMemo(() => {
    if (!hist) return [];
    return mergeLive(basePoints(hist, range), live);
  }, [hist, range, live]);

  const secondary: ChartPoint[] | undefined = useMemo(() => {
    if (!hist || range === "24h" || !quote || quote.sell <= 0) return undefined;
    const days = range === "7d" ? 7 : 30;
    return hist.daily.slice(-days).map((d) => ({ time: d.date, value: d.sell }));
  }, [hist, range, quote]);

  const stats = useMemo(() => {
    if (points.length < 2) return null;
    const values = points.map((p) => p.value);
    const first = values[0];
    const last = values[values.length - 1];
    return {
      high: Math.max(...values),
      low: Math.min(...values),
      change: last - first,
      pct: changePct(last, last - first),
    };
  }, [points]);

  const pct = quote ? changePct(quote.buy, quote.change_buy) : 0;

  return (
    <div>
      <div className="range-tabs">
        {(compact ? symbols.filter((s) => s.featured) : symbols).map((s) => (
          <button
            key={s.code}
            data-active={active === s.alias || active === s.code}
            onClick={() => pick(s.alias)}
          >
            {s.name}
          </button>
        ))}
      </div>

      <div className="row row--between" style={{ marginBottom: 10, gap: 12, flexWrap: "wrap" }}>
        <div className="row">
          <span className="price-card__brand">{meta?.brand ?? "—"}</span>
          <span style={{ fontWeight: 600 }}>{meta?.name ?? "…"}</span>
          <span className="mono" style={{ fontWeight: 700, fontSize: 17 }}>
            {quote ? fmtPrice(quote.buy, unit) : "—"}
          </span>
          <span className={`chip chip--${pct > 0 ? "up" : pct < 0 ? "down" : "flat"}`}>
            {fmtPct(pct)}
          </span>
        </div>
        <div className="range-tabs" style={{ marginBottom: 0 }}>
          {RANGES.map((r) => (
            <button key={r.key} data-active={range === r.key} onClick={() => setRange(r.key)}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <div className="empty">{error}</div>
      ) : points.length < 2 ? (
        <div className="empty">Đang tải dữ liệu biểu đồ…</div>
      ) : (
        <div className="card" style={{ padding: 6 }}>
          <ChartView
            points={points}
            secondary={secondary}
            positive={pct >= 0}
            height={height}
            unit={unit}
            fitKey={`${active}:${range}:${hist ? "ready" : "wait"}`}
          />
        </div>
      )}

      {!compact && stats && (
        <div className="stat-grid" style={{ marginTop: 14 }}>
          <div className="stat">
            <div className="stat__k">Cao nhất kỳ</div>
            <div className="stat__v up">{fmtPrice(stats.high, unit)}</div>
          </div>
          <div className="stat">
            <div className="stat__k">Thấp nhất kỳ</div>
            <div className="stat__v down">{fmtPrice(stats.low, unit)}</div>
          </div>
          <div className="stat">
            <div className="stat__k">Thay đổi kỳ</div>
            <div className={`stat__v ${stats.pct >= 0 ? "up" : "down"}`}>
              {fmtSigned(stats.change, unit)}
            </div>
          </div>
          <div className="stat">
            <div className="stat__k">Phần trăm</div>
            <div className={`stat__v ${stats.pct >= 0 ? "up" : "down"}`}>{fmtPct(stats.pct)}</div>
          </div>
        </div>
      )}

      {!compact && (
        <p className="meta" style={{ marginTop: 12 }}>
          MÃ {meta?.code ?? "—"} · NGUỒN {hist?.source ?? "…"} · {hist?.daily.length ?? 0} NGÀY LƯU TRỮ
          · ĐƯỜNG ĐỨT KIM VÀNG = GIÁ BÁN RA
        </p>
      )}
    </div>
  );
}
