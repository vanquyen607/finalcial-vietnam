export interface GoldType {
  code: string;
  name: string;
  brand: string;
  /** tên sản phẩm bên trong nhà bán ("SJC", "Nhẫn trơn", "Hà Nội"…) */
  product: string;
  unit: "VND" | "USD";
  per: string;
  category: string;
  featured: boolean;
  alias: string;
}

/** Nhóm nhà bán do backend sắp thứ tự (/api/symbols -> brands). */
export interface BrandInfo {
  brand: string;
  label: string;
  order: number;
  count: number;
}

export interface Quote {
  ts: number;
  code: string;
  name: string;
  buy: number;
  sell: number;
  change_buy: number;
  change_sell: number;
  unit: "VND" | "USD";
  per: string;
  source: string;
}

export interface Status {
  state: "starting" | "live" | "error";
  source?: string;
  last_success?: number | null;
  last_error?: string | null;
  polls?: number;
  clients?: number;
}

export interface Alert {
  id: number;
  code: string;
  name?: string;
  direction: "up" | "down";
  threshold: number;
  target_price?: number | null;
  note: string;
  active: number;
  created_at: number;
  triggered_at: number | null;
}

export interface NewsItem {
  link: string;
  title: string;
  source: string;
  published: number;
  image: string;
}

export interface DailyPoint {
  date: string;
  buy: number;
  sell: number;
  day_change_buy: number;
  day_change_sell: number;
  updates: number;
}

export interface HistoryPayload {
  code: string;
  meta: GoldType;
  days: number;
  daily: DailyPoint[];
  intraday: { ts: number; buy: number; sell: number }[];
  source: string | null;
}

/* ---------- /api/extras: bạc, tỷ giá, xăng dầu ---------- */
export interface SilverInfo {
  ts: number;
  stale: boolean;
  price_usd: number;
  change_usd: number;
  source: string;
  vnd_per_luong?: number;
}

export interface FxItem {
  code: string;
  name: string;
  buy: number | null;
  transfer: number | null;
  sell: number | null;
}

export interface FuelItem {
  name: string;
  change: number;
  zone1: number;
  zone2: number | null;
}

export interface SilverDomesticItem {
  brand: string;
  name: string;
  buy: number | null;
  sell: number | null;
  change: number | null;
  source: string;
}

export interface ExtrasPayload {
  ts: number;
  silver: SilverInfo | null;
  silver_domestic: { ts: number; stale: boolean; source: string; items: SilverDomesticItem[] } | null;
  fx: { ts: number; stale: boolean; source: string; items: FxItem[] } | null;
  fuel: { ts: number; stale: boolean; source: string; items: FuelItem[] } | null;
}

/** Một khung thời gian của đồng hồ sức mua/bán (TradingView Recommend). */
export interface TfRating {
  all: number;
  ma: number | null;
  other: number | null;
  rating: string;
  label: string;
}

export interface TechnicalsPayload {
  ts: number;
  stale: boolean;
  symbol: string;
  close: number | null;
  change: number | null;
  frames: Record<string, TfRating>;
}
