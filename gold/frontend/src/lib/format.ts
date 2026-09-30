const VND = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });
const NUM2 = new Intl.NumberFormat("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Giá đầy đủ theo đơn vị: 140.500.000 (VND) hoặc 4.177,80 (USD). */
export function fmtPrice(value: number, unit: string): string {
  if (!Number.isFinite(value)) return "—";
  if (unit === "USD") return NUM2.format(value);
  return VND.format(Math.round(value));
}

/** Giá rút gọn để lướt: 140,5 tr / 4.177,8 $. */
export function fmtCompact(value: number, unit: string): string {
  if (!Number.isFinite(value)) return "—";
  if (unit === "USD") return NUM2.format(value);
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(value >= 100_000_000 ? 1 : 2)} tr`;
  return VND.format(value);
}

/** Thay đổi tuyệt đối + % so với đầu ngày. */
export function changePct(buy: number, change: number): number {
  const prev = buy - change;
  if (!prev) return 0;
  return (change / prev) * 100;
}

export function fmtSigned(value: number, unit: string): string {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  const abs = Math.abs(value);
  if (unit === "USD") return `${sign}${NUM2.format(abs)}`;
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(abs >= 10_000_000 ? 1 : 2)} tr`;
  return `${sign}${VND.format(Math.round(abs))}`;
}

export function fmtPct(pct: number): string {
  const sign = pct > 0 ? "+" : pct < 0 ? "−" : "";
  return `${sign}${Math.abs(pct).toFixed(2)}%`;
}

export function tone(v: number): "up" | "down" | "flat" {
  if (v > 0) return "up";
  if (v < 0) return "down";
  return "flat";
}

export function fmtClock(ts?: number | null): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleTimeString("vi-VN", { hour12: false });
}

/** "12 giây trước" / "3 phút trước" — dùng cho nhịp cập nhật (heartbeat). */
export function fmtAgo(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return "vừa xong";
  if (sec < 60) return `${Math.floor(sec)} giây trước`;
  if (sec < 3600) return `${Math.floor(sec / 60)} phút trước`;
  return `${Math.floor(sec / 3600)} giờ trước`;
}

export function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y.slice(2)}`;
}
