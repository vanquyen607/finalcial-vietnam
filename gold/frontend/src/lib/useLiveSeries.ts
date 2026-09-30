import { useEffect, useRef, useState } from "react";
import type { Quote } from "./types";

export interface LiveTick {
  ts: number;
  buy: number;
}

/**
 * Gom các tick realtime từ WebSocket để nối vào biểu đồ.
 * - intraday (24h): cộng dồn điểm mới, thời gian tăng dần (giây).
 * - daily (7d/30d): giữ tick cuối để cập nhật cây nến hiện tại.
 */
export function useLiveSeries(quote: Quote | undefined, mode: "intraday" | "daily"): LiveTick[] {
  const [live, setLive] = useState<LiveTick[]>([]);
  const codeRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (quote?.code !== codeRef.current) {
      codeRef.current = quote?.code;
      setLive([]);
    }
  }, [quote?.code]);

  useEffect(() => {
    if (!quote || quote.buy <= 0) return;
    setLive((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.ts === quote.ts) return prev;
      if (last && quote.ts < last.ts) return prev;
      if (last && quote.ts - last.ts > 12 * 3600 * 1000) {
        // ngắt quãng quá lâu → bắt đầu chuỗi mới
        return [{ ts: quote.ts, buy: quote.buy }];
      }
      return [...prev, { ts: quote.ts, buy: quote.buy }];
    });
  }, [quote]);

  return mode === "intraday" ? live : live.slice(-1);
}

/** Gộp dữ liệu lịch sử + tick realtime, khử trùng lặp theo thời gian (giây). */
export function mergeLive<T extends { time: number | string; value: number }>(
  base: T[],
  live: LiveTick[],
): T[] {
  if (!live.length) return base;
  if (!base.length) {
    return live.map((p) => ({ time: Math.floor(p.ts / 1000), value: p.buy }) as unknown as T);
  }

  const isDaily = typeof base[base.length - 1].time === "string";
  if (isDaily) {
    const copy = base.slice();
    copy[copy.length - 1] = { ...copy[copy.length - 1], value: live[live.length - 1].buy };
    return copy;
  }

  const byTime = new Map<number, number>();
  for (const p of base) byTime.set(Number(p.time), p.value);
  for (const t of live) byTime.set(Math.floor(t.ts / 1000), t.buy);

  return [...byTime.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([time, value]) => ({ time, value }) as unknown as T);
}
