import { useEffect, useState } from "react";

/** Đồng hồ re-render mỗi `intervalMs` — để hiển thị "x giây trước" chạy sống. */
export function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);
  return now;
}

/** Số giây đã trôi qua kể từ `ts` (epoch giây). */
export function ageSeconds(ts: number | null | undefined, now: number): number | null {
  if (!ts) return null;
  return Math.max(0, Math.floor(now / 1000) - ts);
}
