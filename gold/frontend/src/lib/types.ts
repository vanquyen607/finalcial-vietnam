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
  note: string;
  active: number;
  created_at: number;
  triggered_at: number | null;
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
