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

export interface IndexItem {
  code: string;
  name: string;
  close: number;
  change: number;
  change_pct: number;
  volume: number | null;
  ts: number;
}

export interface CryptoItem {
  code: string;
  name: string;
  usd: number;
  vnd: number | null;
  change_24h: number;
}

export interface OilItem {
  code: string;
  name: string;
  price: number;
  change_abs: number;
  change_pct: number;
}

export interface GlobalItem {
  code: string;
  name: string;
  value: number;
  change_abs: number;
  change_pct: number;
  unit: string;
}

export interface RatesItem {
  code: string;
  name: string;
  rates: Record<string, number | null>;
}

export interface ExtrasPayload {
  ts: number;
  silver: SilverInfo | null;
  silver_domestic: { ts: number; stale: boolean; source: string; items: SilverDomesticItem[] } | null;
  fx: { ts: number; stale: boolean; source: string; items: FxItem[] } | null;
  fuel: { ts: number; stale: boolean; source: string; items: FuelItem[] } | null;
  indices: { ts: number; stale: boolean; source: string; items: IndexItem[] } | null;
  crypto: { ts: number; stale: boolean; source: string; items: CryptoItem[] } | null;
  oil: { ts: number; stale: boolean; source: string; items: OilItem[] } | null;
  global: { ts: number; stale: boolean; source: string; items: GlobalItem[] } | null;
  rates: { ts: number; stale: boolean; source: string; terms: string[]; items: RatesItem[] } | null;
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
