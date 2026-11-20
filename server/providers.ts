import * as cheerio from "cheerio";
import { XMLParser } from "fast-xml-parser";
import { db, type DailyRow } from "./store.ts";
import { BY_CODE, GOLD_TYPES } from "./symbols.ts";

export interface ProviderQuote {
  code: string;
  name: string;
  buy: number;
  sell: number;
  change_buy: number;
  change_sell: number;
  unit: "VND" | "USD";
  per: string;
  source: string;
  updated_at?: number;
}

export interface GoldProvider {
  readonly name: string;
  fetchCurrent(): Promise<ProviderQuote[]>;
  supportsHistory?(code: string): boolean;
  fetchHistory?(code: string, days: number): Promise<Omit<DailyRow, "code">[]>;
}

const UA = "Mozilla/5.0 (AurumTerminal/1.0)";
const BROWSER_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

function num(v: unknown): number | null {
  if (typeof v === "number") {
    return Number.isFinite(v) ? v : null;
  }
  if (typeof v === "string") {
    const cleaned = v.trim();
    if (!cleaned) return null;
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function vnNum(text: string | undefined | null): number | null {
  if (!text) return null;
  const cleaned = text.trim().replace(/\./g, "").replace(",", ".");
  if (!cleaned) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

async function fetchText(
  url: string,
  timeoutMs = 12000,
  headers: Record<string, string> = {},
): Promise<{ status: number; headers: Headers; text: string }> {
  const res = await fetch(url, {
    headers: { "User-Agent": UA, ...headers },
    redirect: "follow",
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await res.text();
  return { status: res.status, headers: res.headers, text };
}

async function fetchJson<T>(
  url: string,
  timeoutMs = 12000,
  headers: Record<string, string> = {},
): Promise<{ status: number; headers: Headers; data: T }> {
  const res = await fetch(url, {
    headers: { "User-Agent": UA, Accept: "application/json", ...headers },
    redirect: "follow",
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (res.status === 304) {
    return { status: 304, headers: res.headers, data: null as T };
  }
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${url}`);
  }
  const data = (await res.json()) as T;
  return { status: res.status, headers: res.headers, data };
}

function seededRandom(seedStr: string): () => number {
  let h = 2166136261;
  for (let i = 0; i < seedStr.length; i++) {
    h ^= seedStr.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return () => {
    h += 0x6d2b79f5;
    let t = Math.imul(h ^ (h >>> 15), 1 | h);
    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ============================================================================
// MockProvider
// ============================================================================
const MOCK_BASE: Record<string, number> = {
  SJL1L10: 140_500_000,
  SJ9999: 140_000_000,
  VNGSJC: 140_500_000,
  DOHNL: 140_500_000,
  DOHCML: 140_500_000,
  DOJINHTV: 139_800_000,
  PQHNVM: 140_200_000,
  PQHN24NTT: 140_200_000,
  BTSJC: 139_500_000,
  BT9999NTT: 139_500_000,
  VIETTINMSJC: 140_500_000,
  XAUUSD: 4177.8,
};

export class MockProvider implements GoldProvider {
  readonly name = "mock";
  private t = 0;
  private level: Record<string, number> = {};
  private prev: Record<string, number> = {};

  constructor() {
    for (const t of GOLD_TYPES) {
      this.level[t.code] = MOCK_BASE[t.code] ?? (t.unit === "VND" ? 140_000_000 : 4000);
    }
    this.prev = { ...this.level };
  }

  private step(): void {
    this.prev = { ...this.level };
    this.t += 1;
    for (const [code, price] of Object.entries(this.level)) {
      const rand = (Math.random() - 0.5) * 2;
      const drift = code === "XAUUSD" ? rand * 0.0012 : rand * 0.0004;
      const hash = code.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
      const wave = Math.sin(this.t / 12 + (hash % 7)) * 0.0006;
      this.level[code] = price * (1 + drift + wave);
    }
  }

  async fetchCurrent(): Promise<ProviderQuote[]> {
    this.step();
    const now = Math.floor(Date.now() / 1000);
    return GOLD_TYPES.map((meta) => {
      const code = meta.code;
      let buy = this.level[code];
      let sell = code === "XAUUSD" ? buy : buy * 1.021;
      let prev = this.prev[code];
      if (meta.unit === "VND") {
        buy = Math.round(buy / 10_000) * 10_000;
        sell = Math.round(sell / 10_000) * 10_000;
        prev = Math.round(prev / 10_000) * 10_000;
      } else {
        buy = Math.round(buy * 100) / 100;
        sell = Math.round(sell * 100) / 100;
        prev = Math.round(prev * 100) / 100;
      }
      return {
        code,
        name: meta.name,
        buy,
        sell,
        change_buy: Number((buy - prev).toFixed(4)),
        change_sell: Number((sell - prev).toFixed(4)),
        unit: meta.unit,
        per: meta.per,
        source: this.name,
        updated_at: now,
      };
    });
  }

  supportsHistory(_code: string): boolean {
    return true;
  }

  async fetchHistory(code: string, days: number): Promise<Omit<DailyRow, "code">[]> {
    const meta = BY_CODE[code];
    const base = MOCK_BASE[code] ?? (meta?.unit === "USD" ? 4000 : 140_000_000);
    const rnd = seededRandom(code);
    const today = new Date();
    const rows: Omit<DailyRow, "code">[] = [];
    let price = base * (1 - rnd() * 0.03);
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(today.getTime() - i * 86400_000);
      const prev = price;
      const delta = (rnd() - 0.48) * 0.008;
      price *= 1 + delta;
      const isVnd = base > 1e6;
      const buy = isVnd ? Math.round(price / 10_000) * 10_000 : Math.round(price * 100) / 100;
      const sell =
        code === "XAUUSD"
          ? 0
          : isVnd
            ? Math.round((price * 1.021) / 10_000) * 10_000
            : Math.round(price * 1.021 * 100) / 100;
      const change = isVnd
        ? Math.round((price - prev) / 10_000) * 10_000
        : Math.round((price - prev) * 100) / 100;
      rows.push({
        date: d.toISOString().slice(0, 10),
        buy,
        sell,
        day_change_buy: change,
        day_change_sell: 0,
        updates: Math.floor(rnd() * 5) + 1,
      });
    }
    return rows;
  }
}

// ============================================================================
// World Spot (TradingView Scanner + gold-api fallback)
// ============================================================================
const SPOT_SCANNER = "https://scanner.tradingview.com/symbol";
const SPOT_SYMBOLS = [
  "OANDA:XAUUSD",
  "TVC:GOLD",
  "FX:XAUUSD",
  "FOREXCOM:XAUUSD",
  "SAXO:XAUUSD",
  "BINANCE:PAXGUSDT",
  "CRYPTO:PAXGUSD",
];
const SPOT_FALLBACK = "https://api.gold-api.com/price/XAU";

export async function fetchWorldSpot(): Promise<[number, number] | null> {
  for (const symbol of SPOT_SYMBOLS) {
    try {
      const url = `${SPOT_SCANNER}?symbol=${encodeURIComponent(symbol)}&fields=close,change_abs`;
      const { data } = await fetchJson<{ close?: number; change_abs?: number }>(url, 7000);
      const price = Number(data?.close ?? 0);
      if (price > 0) {
        return [price, Number(data?.change_abs ?? 0)];
      }
    } catch {
      // try next symbol
    }
  }
  try {
    const { data } = await fetchJson<{ price?: number }>(SPOT_FALLBACK, 7000);
    const price = Number(data?.price ?? 0);
    if (price > 0) return [price, 0];
  } catch {
    // ignore
  }
  return null;
}

// ============================================================================
// VangTodayProvider
// ============================================================================
const VANGTODAY_BASE = "https://vang.today/api/prices";
const HISTORY_CODES = new Set([
  "BT9999NTT",
  "BTSJC",
  "DOHCML",
  "DOHNL",
  "DOJINHTV",
  "PQHN24NTT",
  "PQHNVM",
  "SJ9999",
  "SJL1L10",
  "VIETTINMSJC",
  "VNGSJC",
  "XAUUSD",
]);

interface VangTodayRow {
  type_code?: string;
  buy?: unknown;
  sell?: unknown;
  change_buy?: unknown;
  change_sell?: unknown;
}

export class VangTodayProvider implements GoldProvider {
  readonly name = "vangtoday";

  async fetchCurrent(): Promise<ProviderQuote[]> {
    const { data } = await fetchJson<{
      success?: boolean;
      current_time?: number;
      data?: VangTodayRow[];
    }>(`${VANGTODAY_BASE}?action=current`, 12000);

    if (!data?.success || !Array.isArray(data.data)) {
      throw new Error("vang.today trả success=false hoặc data rỗng");
    }

    const updatedAt = typeof data.current_time === "number" ? data.current_time : undefined;
    const quotes: ProviderQuote[] = [];
    for (const row of data.data) {
      if (!row || typeof row !== "object") continue;
      const code = row.type_code;
      const buy = num(row.buy);
      if (!code || typeof code !== "string" || buy === null) continue;
      const meta = BY_CODE[code];
      quotes.push({
        code,
        name: meta?.name ?? code,
        buy,
        sell: num(row.sell) ?? 0,
        change_buy: num(row.change_buy) ?? 0,
        change_sell: num(row.change_sell) ?? 0,
        unit: meta?.unit ?? "VND",
        per: meta?.per ?? "lượng",
        source: this.name,
        updated_at: updatedAt,
      });
    }

    if (!quotes.length) {
      throw new Error("vang.today trả data rỗng");
    }

    const spot = await fetchWorldSpot();
    if (spot) {
      const [price, change] = spot;
      const now = Math.floor(Date.now() / 1000);
      for (const q of quotes) {
        if (q.code === "XAUUSD" && price > 0) {
          q.buy = price;
          q.change_buy = change;
          q.source = "spot";
          q.updated_at = now;
          break;
        }
      }
    }
    return quotes;
  }

  supportsHistory(code: string): boolean {
    return HISTORY_CODES.has(code);
  }

  async fetchHistory(code: string, days: number): Promise<Omit<DailyRow, "code">[]> {
    const clamped = Math.max(1, Math.min(days, 30));
    const url = `${VANGTODAY_BASE}?days=${clamped}&type=${encodeURIComponent(code)}`;
    const { data } = await fetchJson<{
      success?: boolean;
      history?: Array<{ date?: string; prices?: Record<string, Record<string, unknown>> }>;
    }>(url, 12000);

    if (!data?.success || !Array.isArray(data.history)) {
      throw new Error("vang.today history success=false");
    }

    const out: Omit<DailyRow, "code">[] = [];
    for (const day of data.history) {
      if (!day || !day.date || !day.prices) continue;
      const entry = day.prices[code];
      if (!entry) continue;
      const buy = num(entry.buy);
      if (buy === null) continue;
      out.push({
        date: day.date,
        buy,
        sell: num(entry.sell) ?? 0,
        day_change_buy: num(entry.day_change_buy) ?? 0,
        day_change_sell: num(entry.day_change_sell) ?? 0,
        updates: Math.trunc(num(entry.updates) ?? 0),
      });
    }
    out.sort((a, b) => a.date.localeCompare(b.date));
    return out;
  }
}

// ============================================================================
// MiHongProvider
// ============================================================================
const MIHONG_ITEMS: Record<string, string> = {
  SJC: "MH_SJC",
  "999": "MH_9999",
  "985": "MH_985",
  "980": "MH_980",
  "750": "MH_750",
  "680": "MH_680",
  "610": "MH_610",
};

function parseMhTime(text: string): number | null {
  const m = text.trim().match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})$/);
  if (!m) return null;
  const [, dd, mm, yyyy, hh, min] = m;
  const utc = Date.UTC(Number(yyyy), Number(mm) - 1, Number(dd), Number(hh), Number(min));
  return Math.floor(utc / 1000) - 7 * 3600;
}

export class MiHongProvider implements GoldProvider {
  readonly name = "mihong";
  private cache: ProviderQuote[] = [];
  private cacheTs = 0;

  async fetchCurrent(): Promise<ProviderQuote[]> {
    const now = Math.floor(Date.now() / 1000);
    if (this.cache.length && now - this.cacheTs < 300) return this.cache;

    const { data } = await fetchJson<Array<Record<string, unknown>>>(
      "https://api.mihong.com/v1/gold-prices?market=domestic",
      12000,
      { "x-market": "mihong" },
    );

    const quotes: ProviderQuote[] = [];
    for (const row of data ?? []) {
      if (!row || typeof row !== "object") continue;
      const code = MIHONG_ITEMS[String(row.code ?? "")];
      if (!code || !BY_CODE[code]) continue;
      const buy = num(row.buyingPrice);
      const sell = num(row.sellingPrice);
      if (!buy && !sell) continue;
      const meta = BY_CODE[code];
      quotes.push({
        code,
        name: meta.name,
        buy: (buy ?? 0) * 10,
        sell: (sell ?? 0) * 10,
        change_buy: (num(row.buyChange) ?? 0) * 10,
        change_sell: (num(row.sellChange) ?? 0) * 10,
        unit: meta.unit,
        per: meta.per,
        source: this.name,
        updated_at: parseMhTime(String(row.dateTime ?? "")) ?? now,
      });
    }
    if (!quotes.length) {
      if (this.cache.length) return this.cache;
      throw new Error("mihong trả rỗng");
    }
    this.cache = quotes;
    this.cacheTs = now;
    return quotes;
  }
}

// ============================================================================
// NgocThamProvider
// ============================================================================
const NT_ITEMS: Record<string, string[]> = {
  NT_9999: ["Nhẫn 999.9", "Nhẫn Trơn 24K", "Vàng 24K"],
  NT_SJC: ["Vàng Miếng SJC (Loại 10 chỉ)", "Vàng Miếng SJC"],
};

function parseNtTime(text: string): number | null {
  const m = text.trim().match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})$/);
  if (!m) return null;
  const [, yyyy, mm, dd, hh, min, ss] = m;
  const utc = Date.UTC(Number(yyyy), Number(mm) - 1, Number(dd), Number(hh), Number(min), Number(ss));
  return Math.floor(utc / 1000) - 7 * 3600;
}

export class NgocThamProvider implements GoldProvider {
  readonly name = "ngoctham";
  private cache: ProviderQuote[] = [];
  private cacheTs = 0;
  private etag = "";

  async fetchCurrent(): Promise<ProviderQuote[]> {
    const now = Math.floor(Date.now() / 1000);
    if (this.cache.length && now - this.cacheTs < 900) return this.cache;

    const headers: Record<string, string> = {};
    if (this.etag) headers["If-None-Match"] = this.etag;

    const res = await fetchJson<{
      date?: string;
      chitiet?: Array<{ loaivang?: string; giamua?: unknown; giaban?: unknown }>;
    }>("https://ngoctham.com/ajax/proxy_banggia.php", 12000, headers);

    if (res.status === 304 && this.cache.length) {
      this.cacheTs = now;
      return this.cache;
    }

    this.etag = res.headers.get("etag") ?? this.etag;
    const payload = res.data;
    const ts = parseNtTime(payload?.date ?? "") ?? now;
    const byName = new Map<string, { giamua?: unknown; giaban?: unknown }>();
    for (const r of payload?.chitiet ?? []) {
      if (r?.loaivang) byName.set(r.loaivang, r);
    }

    const quotes: ProviderQuote[] = [];
    for (const [code, candidates] of Object.entries(NT_ITEMS)) {
      const row = candidates.map((n) => byName.get(n)).find(Boolean);
      if (!row) continue;
      const buy = num(row.giamua);
      const sell = num(row.giaban);
      if (!buy || !sell) continue;
      const meta = BY_CODE[code];
      quotes.push({
        code,
        name: meta.name,
        buy: buy * 10,
        sell: sell * 10,
        change_buy: 0,
        change_sell: 0,
        unit: meta.unit,
        per: meta.per,
        source: this.name,
        updated_at: ts,
      });
    }
    if (!quotes.length) {
      if (this.cache.length) return this.cache;
      throw new Error("ngoctham trả rỗng");
    }
    this.cache = quotes;
    this.cacheTs = now;
    return quotes;
  }
}

// ============================================================================
// BtmhProvider
// ============================================================================
const BTMH_GOLD_ITEMS: Record<string, string> = {
  "Kim Gia Bảo 24K": "BTMH_9999",
  "Vàng trang sức 24K 999": "BTMH_999",
};

function parseBtmhRows(html: string): Array<{ name: string; nums: number[] }> {
  const $ = cheerio.load(html);
  const out: Array<{ name: string; nums: number[] }> = [];
  $('div[role="row"]').each((_, rowEl) => {
    const nameEl = $(rowEl).find('[role="cell"]').first();
    if (!nameEl.length) return;
    const nums: number[] = [];
    $(rowEl)
      .find("span.tabular-nums")
      .each((__, s) => {
        const val = vnNum($(s).text());
        if (val !== null) nums.push(val);
      });
    if (nums.length >= 2) {
      out.push({ name: nameEl.text().replace(/\s+/g, " ").trim(), nums });
    }
  });
  return out;
}

export function parseBtmhSilver(html: string) {
  const items: Array<{
    brand: string;
    name: string;
    buy: number | null;
    sell: number | null;
    change: number | null;
  }> = [];
  for (const { name, nums } of parseBtmhRows(html)) {
    if (!name.includes("Bạc") && !name.includes("Ngân Gia Bảo")) continue;
    const factor = name.includes("(ĐVT: kg)") ? 37.5 : 1000;
    const buy = nums.length > 1 ? nums[1] * factor : null;
    const sell = nums.length > 2 ? nums[2] * factor : null;
    if (!buy && !sell) continue;
    items.push({
      brand: "BTMH",
      name: name.replace(/\s*\(ĐVT:[^)]*\)/g, ""),
      buy,
      sell,
      change: null,
    });
  }
  return items;
}

export class BtmhProvider implements GoldProvider {
  readonly name = "btmh";
  private cache: ProviderQuote[] = [];
  private cacheTs = 0;

  async fetchCurrent(): Promise<ProviderQuote[]> {
    const now = Math.floor(Date.now() / 1000);
    if (this.cache.length && now - this.cacheTs < 600) return this.cache;

    const { status, text } = await fetchText("https://baotinmanhhai.vn/bang-gia-vang", 12000, {
      Accept: "text/html",
    });
    if (status >= 400) throw new Error(`HTTP ${status} btmh`);

    const quotes: ProviderQuote[] = [];
    for (const { name, nums } of parseBtmhRows(text)) {
      const code = BTMH_GOLD_ITEMS[name];
      if (!code || nums.length < 3) continue;
      const meta = BY_CODE[code];
      quotes.push({
        code,
        name: meta.name,
        buy: nums[1] * 10_000,
        sell: nums[2] * 10_000,
        change_buy: 0,
        change_sell: 0,
        unit: meta.unit,
        per: meta.per,
        source: this.name,
        updated_at: now,
      });
    }
    if (!quotes.length) {
      if (this.cache.length) return this.cache;
      throw new Error("btmh trả rỗng");
    }
    this.cache = quotes;
    this.cacheTs = now;
    return quotes;
  }
}

// ============================================================================
// SimplizeProvider
// ============================================================================
const SIMPLIZE_PRODUCTS: Array<[string, string, string]> = [
  ["MH_SJC", "mi-hong", "vang-mieng-sjc-mi-hong"],
  ["MH_9999", "mi-hong", "vang-999-mi-hong"],
  ["MH_985", "mi-hong", "vang-985-mi-hong"],
  ["MH_980", "mi-hong", "vang-980-mi-hong"],
  ["MH_750", "mi-hong", "vang-750-mi-hong"],
  ["MH_680", "mi-hong", "vang-680-mi-hong"],
  ["MH_610", "mi-hong", "vang-610-mi-hong"],
  ["BTMH_9999", "bao-tin-manh-hai", "vang-nu-trang-9999-btmh"],
  ["BTMH_999", "bao-tin-manh-hai", "vang-nu-trang-999-btmh"],
  ["BTMH_RING", "bao-tin-manh-hai", "nhan-ep-vi-kim-gia-bao"],
  ["BTMH_DONG", "bao-tin-manh-hai", "dong-vang-kim-gia-bao-hoa-sen"],
  ["PQ_SJC", "phu-quy", "vang-mieng-sjc-phu-quy"],
  ["PQ_9999", "phu-quy", "nhan-tron-phu-quy-9999"],
  ["PQ_999", "phu-quy", "phu-quy-1-luong-999"],
  ["PQ_9999_BAR", "phu-quy", "phu-quy-1-luong-9999"],
  ["PQ_TS9999", "phu-quy", "vang-trang-suc-9999-phu-quy"],
  ["PQ_TS999", "phu-quy", "vang-trang-suc-999-phu-quy"],
  ["PQ_TS99", "phu-quy", "vang-trang-suc-99-phu-quy"],
  ["PQ_TS98", "phu-quy", "vang-trang-suc-98-phu-quy"],
  ["SJC_1CHI", "sjc", "vang-sjc-1-chi"],
  ["SJC_5CHI", "sjc", "vang-sjc-5-chi"],
  ["SJC_NHAN_05", "sjc", "vang-nhan-sjc-9999-05-chi"],
  ["SJC_NHAN_1", "sjc", "vang-nhan-sjc-9999-1-chi"],
  ["DOJI_SJC_DN", "doji", "vang-mieng-sjc-doji-da-nang"],
  ["DOJI_RING", "doji", "nhan-tron-9999-hung-thinh-vuong"],
  ["DOJI_24K", "doji", "vang-24k-doji"],
  ["DOJI_PL_HN", "doji", "vang-mieng-phuc-long-doji-ha-noi"],
  ["DOJI_PL_HCM", "doji", "vang-mieng-phuc-long-doji-hcm"],
  ["DOJI_PL_DN", "doji", "vang-mieng-phuc-long-doji-da-nang"],
  ["PNJ_KIMBAO", "pnj", "vang-kim-bao-9999"],
  ["PNJ_PHUCLOC", "pnj", "vang-phuc-loc-tai-9999"],
  ["PNJ_PHOENIX", "pnj", "vang-mieng-pnj-phuong-hoang"],
  ["BTMC_RTL", "bao-tin-minh-chau", "vang-mieng-rong-thang-long-btmc"],
  ["BTMC_TS9999", "bao-tin-minh-chau", "trang-suc-vang-rong-thang-long-9999"],
  ["BTMC_TS999", "bao-tin-minh-chau", "trang-suc-vang-rong-thang-long-999"],
  ["NT_TA", "ngoc-tham", "vang-ta-ngoc-tham"],
  ["NT_18K", "ngoc-tham", "vang-18k-ngoc-tham"],
  ["NT_TS750", "ngoc-tham", "vang-trang-au750-ngoc-tham"],
];

export class SimplizeProvider implements GoldProvider {
  readonly name = "simplize";
  private cache: ProviderQuote[] = [];
  private cacheTs = 0;
  private bid = "";
  private bidTs = 0;

  private async getBuildId(): Promise<string> {
    const now = Math.floor(Date.now() / 1000);
    if (this.bid && now - this.bidTs < 86400) return this.bid;
    const { status, text } = await fetchText(
      "https://simplize.vn/gia-vang/mi-hong/vang-999-mi-hong",
      12000,
    );
    if (status >= 400) throw new Error(`HTTP ${status} simplize`);
    const m = text.match(/"buildId":"([A-Za-z0-9_-]+)"/);
    if (!m) throw new Error("không tìm thấy buildId Simplize");
    this.bid = m[1];
    this.bidTs = now;
    return this.bid;
  }

  async fetchCurrent(): Promise<ProviderQuote[]> {
    const now = Math.floor(Date.now() / 1000);
    if (this.cache.length && now - this.cacheTs < 900) return this.cache;

    const bid = await this.getBuildId();
    const quotes: ProviderQuote[] = [];
    const batchSize = 8;

    for (let i = 0; i < SIMPLIZE_PRODUCTS.length; i += batchSize) {
      const batch = SIMPLIZE_PRODUCTS.slice(i, i + batchSize);
      const settled = await Promise.allSettled(
        batch.map(async ([code, brand, slug]) => {
          const url = `https://simplize.vn/_next/data/${bid}/gia-vang/${brand}/${slug}.json`;
          const { data } = await fetchJson<{
            pageProps?: { listData?: Array<Record<string, unknown>> };
          }>(url, 8000);
          const item = data?.pageProps?.listData?.[0];
          if (!item) return null;
          const buy = num(item.priceBuy);
          const sell = num(item.priceSell);
          if (!buy || !sell) return null;
          const meta = BY_CODE[code];
          const ts = num(item.modifiedTime);
          return {
            code,
            name: meta.name,
            buy,
            sell,
            change_buy: num(item.priceBuyChg) ?? 0,
            change_sell: num(item.priceSellChg) ?? 0,
            unit: meta.unit,
            per: meta.per,
            source: this.name,
            updated_at: ts ? Math.floor(ts / 1000) : now,
          } satisfies ProviderQuote;
        }),
      );
      for (const r of settled) {
        if (r.status === "fulfilled" && r.value) quotes.push(r.value);
      }
    }

    if (!quotes.length) {
      if (this.cache.length) return this.cache;
      throw new Error("simplize trả rỗng toàn bộ sản phẩm");
    }
    this.cache = quotes;
    this.cacheTs = now;
    return quotes;
  }
}

// ============================================================================
// PrivateShopsProvider
// ============================================================================
const MIN_PRICE = 20_000_000;
const MAX_PRICE = 500_000_000;

function parseShopPrice(text: string, mult: number): number | null {
  const digits = (text || "").replace(/[^\d]/g, "");
  if (!digits) return null;
  const val = Number(digits) * mult;
  return val >= MIN_PRICE && val <= MAX_PRICE ? val : null;
}

function tableRows(html: string): string[][] {
  const $ = cheerio.load(html);
  const table = $("table").first();
  if (!table.length) return [];
  const rows: string[][] = [];
  table.find("tr").each((_, tr) => {
    const cells: string[] = [];
    $(tr)
      .find("td, th")
      .each((__, c) => {
        cells.push($(c).text().replace(/\s+/g, " ").trim());
      });
    rows.push(cells);
  });
  return rows;
}

function parseHuyThanh(html: string): Array<[string, number, number]> {
  const labels: Array<[string, string]> = [
    ["vàng huy thanh 24k", "HT_24K"],
    ["vàng thị trường 24k", "HT_MARKET"],
    ["22k", "HT_22K"],
    ["18k", "HT_18K"],
    ["14k", "HT_14K"],
    ["10k", "HT_10K"],
  ];
  const out: Array<[string, number, number]> = [];
  const seen = new Set<string>();
  for (const cells of tableRows(html)) {
    if (cells.length < 3) continue;
    const label = cells[0].toLowerCase();
    const match = labels.find(([needle]) => label.includes(needle));
    if (!match || seen.has(match[1])) continue;
    const buy = parseShopPrice(cells[1], 10);
    if (buy === null) continue;
    out.push([match[1], buy, parseShopPrice(cells[2], 10) ?? 0]);
    seen.add(match[1]);
  }
  return out;
}

function parseKimTin(html: string): Array<[string, number, number]> {
  const $ = cheerio.load(html);
  const panel = $("#gold-area-panel-HN").length
    ? $("#gold-area-panel-HN").first()
    : $(".gold-area-panel").first();
  if (!panel.length) return [];
  const table = panel.find("table").first();
  if (!table.length) return [];
  const out: Array<[string, number, number]> = [];
  const seen = new Set<string>();
  table.find("tr").each((_, tr) => {
    const cells: string[] = [];
    $(tr)
      .find("td, th")
      .each((__, c) => {
        cells.push($(c).text().replace(/\s+/g, " ").trim());
      });
    if (cells.length < 4) return;
    const text = cells.join(" ").toUpperCase();
    const content = cells[cells.length - 3];
    let code = "";
    if (text.includes("VÀNG MIẾNG SJC")) code = "KT_SJC";
    else if (text.includes("NHẪN TRÒN TRƠN")) code = "KT_RING9999";
    else if (text.includes("TRANG SỨC")) {
      if (content.includes("99.7")) code = "KT_TS23K";
      else if (content.includes("999.9")) code = "KT_TS9999";
      else if (content.includes("99.9")) code = "KT_TS999";
      else code = "KT_TS9999";
    } else return;

    if (seen.has(code)) return;
    const buy = parseShopPrice(cells[cells.length - 2], 10_000);
    if (buy === null) return;
    out.push([code, buy, parseShopPrice(cells[cells.length - 1], 10_000) ?? 0]);
    seen.add(code);
  });
  return out;
}

function parseKimThanh(html: string): Array<[string, number, number]> {
  const items: Array<[string, string]> = [
    ["nhẫn trơn 99.99", "KTH_RING9999"],
    ["nhẫn trơn 990", "KTH_RING990"],
    ["nữ trang 980", "KTH_TS980"],
    ["nữ trang 610", "KTH_TS610"],
    ["trang sức trắng 750", "KTH_TS750"],
    ["trang sức 10k", "KTH_TS416"],
  ];
  const $ = cheerio.load(html);
  const out: Array<[string, number, number]> = [];
  const seen = new Set<string>();
  $(".column-brandgold").each((_, block) => {
    const name = $(block).text().replace(/\s+/g, " ").trim().toLowerCase();
    if (name.includes("đính đá")) return;
    const match = items.find(([needle]) => name.includes(needle));
    if (!match || seen.has(match[1])) return;
    const body = $(block).nextAll(".column-typegold").first();
    if (!body.length) return;
    const buyCell = body.find(".col-buy").first();
    const sellCell = body.find(".col-sell").first();
    if (!buyCell.length || !sellCell.length) return;
    const buy = parseShopPrice(buyCell.text(), 10);
    if (buy === null) return;
    out.push([match[1], buy, parseShopPrice(sellCell.text(), 10) ?? 0]);
    seen.add(match[1]);
  });
  return out;
}

function parseKimNganPhuc(html: string): Array<[string, number, number]> {
  const items: Array<[string, string]> = [
    ["nhẫn ép vỉ", "KNP_RING9999"],
    ["vàng trang sức 24k", "KNP_TS24K"],
  ];
  const out: Array<[string, number, number]> = [];
  const seen = new Set<string>();
  for (const cells of tableRows(html)) {
    if (cells.length < 3) continue;
    const label = cells[0].toLowerCase();
    const match = items.find(([needle]) => label.includes(needle));
    if (!match || seen.has(match[1])) continue;
    const buy = parseShopPrice(cells[1], 10_000);
    if (buy === null) continue;
    out.push([match[1], buy, parseShopPrice(cells[2], 10_000) ?? 0]);
    seen.add(match[1]);
  }
  return out;
}

interface ShopSpec {
  key: string;
  url: string;
  parse: (html: string) => Array<[string, number, number]>;
  proxyUrl?: string;
}

const SHOPS: ShopSpec[] = [
  { key: "huythanh", url: "https://huythanhjewelry.vn/gia-vang-hom-nay", parse: parseHuyThanh },
  {
    key: "kimtin",
    url: "https://kimtin.com.vn/",
    parse: parseKimTin,
    proxyUrl: "https://r.jina.ai/https://kimtin.com.vn/",
  },
  { key: "kimthanh", url: "https://kimthanhh.com/gia-vang", parse: parseKimThanh },
  { key: "kimnganphuc", url: "https://kimnganphuc.vn/gia-vang", parse: parseKimNganPhuc },
];

export class PrivateShopsProvider implements GoldProvider {
  readonly name = "shops";
  private cache: ProviderQuote[] = [];
  private cacheTs = 0;

  private async loadShop(spec: ShopSpec): Promise<ProviderQuote[]> {
    const useProxy = process.env.KIMTIN_PROXY !== "0";
    const headers = { "User-Agent": BROWSER_UA, "Accept-Language": "vi,en;q=0.8" };
    let html = "";
    try {
      const res = await fetchText(spec.url, spec.proxyUrl ? 8000 : 14000, headers);
      if (res.status >= 400) throw new Error(`HTTP ${res.status}`);
      html = res.text;
    } catch (err) {
      if (!spec.proxyUrl || !useProxy) throw err;
      const res = await fetchText(spec.proxyUrl, 12000, {
        ...headers,
        "x-return-format": "html",
      });
      if (res.status >= 400) throw new Error(`HTTP ${res.status} proxy`);
      html = res.text;
    }

    const quotes: ProviderQuote[] = [];
    for (const [code, buy, sell] of spec.parse(html)) {
      const meta = BY_CODE[code];
      if (!meta) continue;
      quotes.push({
        code,
        name: meta.name,
        buy,
        sell,
        change_buy: 0,
        change_sell: 0,
        unit: meta.unit,
        per: meta.per,
        source: `shops:${spec.key}`,
      });
    }
    if (!quotes.length) throw new Error(`${spec.key}: không parse được giá nào`);
    return quotes;
  }

  async fetchCurrent(): Promise<ProviderQuote[]> {
    const now = Math.floor(Date.now() / 1000);
    if (this.cache.length && now - this.cacheTs < 300) return this.cache;

    const results = await Promise.allSettled(SHOPS.map((s) => this.loadShop(s)));
    const quotes: ProviderQuote[] = [];
    for (const r of results) {
      if (r.status === "fulfilled") quotes.push(...r.value);
    }
    if (!quotes.length) {
      if (this.cache.length) return this.cache;
      throw new Error("không tiệm nào trả được giá");
    }
    this.cache = quotes;
    this.cacheTs = now;
    return quotes;
  }
}

// ============================================================================
// MergedProvider
// ============================================================================
// ============================================================================
// SjcProvider — giá niêm yết chính chủ SJC (PriceService.ashx)
// Cổng dữ liệu mà website sjc.com.vn dùng để nạp bảng giá. Trả JSON hoặc
// HTML tùy thời điểm nên parse cả hai. Giá trên bảng SJC tính theo nghìn
// đồng/lượng — chuẩn hoá về đồng/lượng như mọi provider khác. Provider này
// đặt CUỐI danh sách gộp: hàng nào lấy được sẽ thắng vang.today cho các mã
// SJC; nếu SJC chặn (Cloudflare 403) thì nó tự rớt, các nguồn khác gánh.
// ============================================================================
const SJC_SERVICE = "https://sjc.com.vn/GoldPrice/Services/PriceService.ashx";

const SJC_BUY_KEYS = ["buy", "buyprice", "buy_price", "giamua", "gia_mua", "mua", "bid"];
const SJC_SELL_KEYS = ["sell", "sellprice", "sell_price", "giaban", "gia_ban", "ban", "ask"];
const SJC_NAME_KEYS = ["name", "typename", "type_name", "type", "label", "title", "productname", "product"];
const SJC_BRANCH_KEYS = ["branch", "branchname", "city", "area", "region", "location"];

// Chuẩn hoá 1 giá SJC về đồng/lượng theo độ lớn của số thô.
function sjcToVnd(v: number): number {
  if (v >= 1e7) return v; // đã là đồng/lượng
  if (v >= 1e6) return v * 10; // đồng/chỉ -> đồng/lượng
  if (v >= 1e4) return v * 1000; // nghìn đồng/lượng -> đồng/lượng
  return v;
}

// Tên loại vàng trên bảng SJC -> các mã nội bộ dùng chung 1 giá niêm yết.
function sjcCodesFor(rawName: string): string[] {
  const name = rawName.toLowerCase();
  if (!name.includes("sjc")) return [];
  const isRing = name.includes("nhẫn") || name.includes("nhan");
  if (isRing) {
    if (name.includes("0.5") || name.includes("0,5")) return ["SJC_NHAN_05"];
    return ["SJ9999", "SJC_NHAN_1"];
  }
  if (name.includes("1l") || name.includes("1 lượng") || name.includes("1 luong")) {
    return ["SJL1L10", "VNGSJC"];
  }
  if (name.includes("5 chỉ") || name.includes("5 chi")) return ["SJC_5CHI"];
  if (name.includes("chỉ") || name.includes("chi")) return ["SJC_1CHI"];
  return [];
}

interface SjcRow {
  name: string;
  buy: number;
  sell: number;
  isHcm: boolean;
}

// Gom mọi object có khoá mua/bán trong payload JSON (đi đệ quy toàn cây).
function sjcRowsFromJson(payload: unknown): SjcRow[] {
  const rows: SjcRow[] = [];
  const walk = (node: unknown): void => {
    if (Array.isArray(node)) {
      node.forEach(walk);
      return;
    }
    if (!node || typeof node !== "object") return;
    const obj = node as Record<string, unknown>;
    const lower = new Map<string, unknown>();
    for (const [k, v] of Object.entries(obj)) lower.set(k.toLowerCase(), v);
    const pick = (keys: string[]): unknown => {
      for (const k of keys) if (lower.has(k)) return lower.get(k);
      return undefined;
    };
    const buy = num(pick(SJC_BUY_KEYS)) ?? vnNum(String(pick(SJC_BUY_KEYS) ?? ""));
    const sell = num(pick(SJC_SELL_KEYS)) ?? vnNum(String(pick(SJC_SELL_KEYS) ?? ""));
    if (buy !== null && sell !== null && buy > 0 && sell > 0) {
      const name = String(pick(SJC_NAME_KEYS) ?? "");
      const branch = String(pick(SJC_BRANCH_KEYS) ?? "");
      const full = `${branch} ${name}`.trim();
      rows.push({
        name: full || name,
        buy: sjcToVnd(buy),
        sell: sjcToVnd(sell),
        isHcm: /hồ chí minh|ho chi minh|hcm/i.test(full),
      });
    }
    Object.values(obj).forEach(walk);
  };
  walk(payload);
  return rows;
}

// Dự phòng: parse bảng HTML (ashx đôi khi trả fragment HTML thay vì JSON).
function sjcRowsFromHtml(html: string): SjcRow[] {
  const rows: SjcRow[] = [];
  const $ = cheerio.load(html);
  $("table tr").each((_, tr) => {
    const cells = $(tr)
      .find("td")
      .map((__, td) => $(td).text().trim())
      .get();
    if (cells.length < 3) return;
    const name = cells[0];
    const nums = cells.slice(1).map((c) => vnNum(c)).filter((n): n is number => n !== null && n > 0);
    if (nums.length < 2) return;
    rows.push({
      name,
      buy: sjcToVnd(nums[0]),
      sell: sjcToVnd(nums[1]),
      isHcm: /hồ chí minh|ho chi minh/i.test(name),
    });
  });
  return rows;
}

export class SjcProvider implements GoldProvider {
  readonly name = "sjc";

  async fetchCurrent(): Promise<ProviderQuote[]> {
    const headers: Record<string, string> = {
      "User-Agent": BROWSER_UA,
      Referer: "https://sjc.com.vn/",
      Accept: "application/json, text/javascript, */*; q=0.01",
      "X-Requested-With": "XMLHttpRequest",
    };

    let text = "";
    let status = 0;
    try {
      const got = await fetchText(SJC_SERVICE, 15000, headers);
      status = got.status;
      text = got.text;
    } catch {
      // thử POST như widget trên trang SJC vẫn làm khi GET lỗi mạng
      const res = await fetch(SJC_SERVICE, {
        method: "POST",
        headers,
        signal: AbortSignal.timeout(15000),
      });
      status = res.status;
      text = await res.text();
    }
    if (status === 403 || status === 503) {
      throw new Error(`SJC chặn truy cập (HTTP ${status})`);
    }
    if (!text) throw new Error("SJC trả rỗng");

    let rows: SjcRow[] = [];
    try {
      rows = sjcRowsFromJson(JSON.parse(text));
    } catch {
      rows = [];
    }
    if (!rows.length) rows = sjcRowsFromHtml(text);
    if (!rows.length) throw new Error("không parse được dữ liệu SJC");

    // Mỗi loại vàng giữ 1 hàng: ưu tiên chi nhánh Hồ Chí Minh, sau đó hàng đầu tiên.
    const byCode = new Map<string, SjcRow>();
    for (const row of rows) {
      const codes = sjcCodesFor(row.name);
      if (!codes.length) continue;
      if (row.buy < 5e7 || row.buy > 5e8 || row.sell < row.buy) continue;
      for (const code of codes) {
        const prev = byCode.get(code);
        if (!prev || (row.isHcm && !prev.isHcm)) byCode.set(code, row);
      }
    }
    if (!byCode.size) throw new Error("SJC không có hàng nào khớp mã nội bộ");

    const now = Math.floor(Date.now() / 1000);
    const quotes: ProviderQuote[] = [];
    for (const [code, row] of byCode) {
      const meta = BY_CODE[code];
      quotes.push({
        code,
        name: meta?.name ?? code,
        buy: row.buy,
        sell: row.sell,
        change_buy: 0,
        change_sell: 0,
        unit: meta?.unit ?? "VND",
        per: meta?.per ?? "lượng",
        source: this.name,
        updated_at: now,
      });
    }
    return quotes;
  }
}

export class MergedProvider implements GoldProvider {
  readonly name = "mix";
  private subs: GoldProvider[];
  private timeoutMs: number;
  lastErrors: Record<string, string> = {};
  lastOk: Record<string, number> = {};

  constructor(subs: GoldProvider[], timeoutMs = 18000) {
    this.subs = subs;
    this.timeoutMs = timeoutMs;
  }

  async fetchCurrent(): Promise<ProviderQuote[]> {
    const results = await Promise.all(
      this.subs.map(async (sub) => {
        try {
          const quotes = await Promise.race([
            sub.fetchCurrent(),
            new Promise<never>((_, rej) =>
              setTimeout(() => rej(new Error("timeout")), this.timeoutMs),
            ),
          ]);
          delete this.lastErrors[sub.name];
          this.lastOk[sub.name] = Math.floor(Date.now() / 1000);
          return quotes;
        } catch (err) {
          this.lastErrors[sub.name] = err instanceof Error ? err.message : String(err);
          return [] as ProviderQuote[];
        }
      }),
    );

    const out = results.flat();
    if (!out.length) {
      const detail = Object.entries(this.lastErrors)
        .map(([k, v]) => `${k}: ${v}`)
        .join("; ");
      throw new Error(`mọi provider đều chết: ${detail || "không rõ"}`);
    }
    return out;
  }

  supportsHistory(code: string): boolean {
    return this.subs.some((s) => s.supportsHistory?.(code));
  }

  async fetchHistory(code: string, days: number): Promise<Omit<DailyRow, "code">[]> {
    for (const sub of this.subs) {
      if (!sub.supportsHistory?.(code) || !sub.fetchHistory) continue;
      try {
        return await sub.fetchHistory(code, days);
      } catch {
        continue;
      }
    }
    throw new Error(`không provider nào có history cho ${code}`);
  }
}

// ============================================================================
// FX USD/VND
// ============================================================================
export async function fetchUsdVnd(): Promise<[number, string] | null> {
  try {
    const { data } = await fetchJson<{ rates?: { VND?: number } }>(
      "https://open.er-api.com/v6/latest/USD",
      8000,
    );
    const vnd = Number(data?.rates?.VND ?? 0);
    if (vnd > 0) return [vnd, "er-api"];
  } catch {
    // fallback
  }

  try {
    const { data } = await fetchJson<{ usd?: { vnd?: number } }>(
      "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
      8000,
    );
    const vnd = Number(data?.usd?.vnd ?? 0);
    if (vnd > 0) return [vnd, "currency-api"];
  } catch {
    // ignore
  }
  return null;
}

// ============================================================================
// Technicals (TradingView Scanner)
// ============================================================================
const TF_SUFFIX: Record<string, string> = {
  "15": "|15",
  "60": "|60",
  "240": "|240",
  "1D": "",
  "1W": "|1W",
};

function ratingOf(value: number): [string, string] {
  if (value <= -0.5) return ["strong_sell", "Bán mạnh"];
  if (value < -0.1) return ["sell", "Bán"];
  if (value <= 0.1) return ["neutral", "Trung lập"];
  if (value < 0.5) return ["buy", "Mua"];
  return ["strong_buy", "Mua mạnh"];
}

let techCache: { ts: number; data: Record<string, unknown> } | null = null;

export async function getTechnicals(): Promise<Record<string, unknown> | null> {
  const now = Math.floor(Date.now() / 1000);
  if (techCache && now - techCache.ts < 60) {
    return { ts: techCache.ts, stale: false, ...techCache.data };
  }

  const fields = ["name", "close", "change"];
  for (const suffix of Object.values(TF_SUFFIX)) {
    fields.push(`Recommend.All${suffix}`, `Recommend.MA${suffix}`, `Recommend.Other${suffix}`);
  }

  try {
    const url = `https://scanner.tradingview.com/symbol?symbol=${encodeURIComponent("OANDA:XAUUSD")}&fields=${encodeURIComponent(fields.join(","))}&no_404=false`;
    const { data: raw } = await fetchJson<Record<string, unknown>>(url, 10000);
    const frames: Record<string, unknown> = {};
    for (const [tf, suffix] of Object.entries(TF_SUFFIX)) {
      const total = num(raw[`Recommend.All${suffix}`]);
      if (total === null) continue;
      const [rating, label] = ratingOf(total);
      const ma = num(raw[`Recommend.MA${suffix}`]);
      const other = num(raw[`Recommend.Other${suffix}`]);
      frames[tf] = {
        all: Number(total.toFixed(4)),
        ma: ma !== null ? Number(ma.toFixed(4)) : null,
        other: other !== null ? Number(other.toFixed(4)) : null,
        rating,
        label,
      };
    }
    if (Object.keys(frames).length > 0) {
      const parsed = {
        symbol: "OANDA:XAUUSD",
        close: num(raw.close),
        change: num(raw.change),
        frames,
      };
      techCache = { ts: now, data: parsed };
      return { ts: now, stale: false, ...parsed };
    }
  } catch {
    // fall through
  }

  if (techCache) {
    return { ts: techCache.ts, stale: true, ...techCache.data };
  }
  return null;
}

// ============================================================================
// Extras (silver, domestic silver, Vietcombank FX, Petrolimex fuel)
// ============================================================================
const OZ_PER_LUONG = 37.5 / 31.1034768;
const xmlParser = new XMLParser({ ignoreAttributes: false, attributeNamePrefix: "@_" });

async function fetchSilver(): Promise<{ price_usd: number; change_usd: number; source: string } | null> {
  for (const sym of ["TVC:SILVER", "OANDA:XAGUSD", "FX:XAGUSD"]) {
    try {
      const url = `https://scanner.tradingview.com/symbol?symbol=${encodeURIComponent(sym)}&fields=close,change_abs`;
      const { data } = await fetchJson<{ close?: number; change_abs?: number }>(url, 7000);
      const price = Number(data?.close ?? 0);
      if (price > 0) {
        return { price_usd: price, change_usd: Number(data?.change_abs ?? 0), source: "TradingView" };
      }
    } catch {
      // next
    }
  }
  try {
    const { data } = await fetchJson<{ price?: number }>("https://api.gold-api.com/price/XAG", 7000);
    const price = Number(data?.price ?? 0);
    if (price > 0) return { price_usd: price, change_usd: 0, source: "gold-api" };
  } catch {
    // ignore
  }
  return null;
}

const FX_ORDER = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "SGD", "CNY", "HKD", "KRW", "THB"];

async function fetchVcbFx() {
  try {
    const { status, text } = await fetchText(
      "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx",
      10000,
    );
    if (status >= 400) return null;
    const parsed = xmlParser.parse(text) as {
      ExrateList?: { Exrate?: Array<Record<string, string>> | Record<string, string> };
    };
    const rawList = parsed?.ExrateList?.Exrate;
    const nodes = Array.isArray(rawList) ? rawList : rawList ? [rawList] : [];
    const byCode = new Map<string, { code: string; name: string; buy: number | null; transfer: number | null; sell: number | null }>();

    const parseVcbVal = (s: string | undefined) => {
      if (!s || s.trim() === "" || s.trim() === "-") return null;
      const n = Number(s.replace(/,/g, ""));
      return Number.isFinite(n) ? n : null;
    };

    for (const node of nodes) {
      const code = (node["@_CurrencyCode"] ?? "").trim();
      if (!code) continue;
      byCode.set(code, {
        code,
        name: (node["@_CurrencyName"] ?? "").trim(),
        buy: parseVcbVal(node["@_Buy"]),
        transfer: parseVcbVal(node["@_Transfer"]),
        sell: parseVcbVal(node["@_Sell"]),
      });
    }
    const items = FX_ORDER.map((c) => byCode.get(c)).filter(Boolean);
    return items.length ? items : null;
  } catch {
    return null;
  }
}

const FUEL_KEYS = ["E5 RON 92", "RON 95 Mức 3", "RON 95 Mức 5", "DO 0,05S", "DO 0,001S", "Dầu hỏa"];

async function fetchFuel() {
  try {
    const { status, text } = await fetchText("https://giaxanghomnay.com/", 10000);
    if (status >= 400) return null;
    const $ = cheerio.load(text);
    const parseFuelNum = (s: string) => {
      const m = s.match(/-?[\d][\d.,]*/);
      if (!m) return null;
      const n = Number(m[0].replace(/[.,]/g, ""));
      return Number.isFinite(n) ? n : null;
    };
    for (const table of $("table").toArray()) {
      const head = $(table).text();
      if (!head.includes("Giá vùng 1")) continue;
      const items: Array<{ name: string; change: number; zone1: number; zone2: number | null }> = [];
      $(table)
        .find("tr")
        .each((_, tr) => {
          const cells = $(tr)
            .find("td, th")
            .toArray()
            .map((c) => $(c).text().replace(/\s+/g, " ").trim());
          if (cells.length < 4 || !FUEL_KEYS.some((k) => cells[0].includes(k))) return;
          const zone1 = parseFuelNum(cells[cells.length - 2]);
          const zone2 = parseFuelNum(cells[cells.length - 1]);
          if (zone1 === null) return;
          items.push({
            name: cells[0],
            change: parseFuelNum(cells[1]) ?? 0,
            zone1,
            zone2,
          });
        });
      if (items.length) return items;
    }
    return null;
  } catch {
    return null;
  }
}

const SILVER_BRANDS = ["DOJI", "Bảo Tín Minh Châu", "Phú Quý", "Bảo Tín Mạnh Hải", "Kim Ngân Phúc"];

async function fetchSilverDomestic() {
  const items: Array<{
    brand: string;
    name: string;
    buy: number | null;
    sell: number | null;
    change: number | null;
    source: string;
  }> = [];

  try {
    const { status, text } = await fetchText("https://webgia.tv/gia-bac", 10000);
    if (status < 400) {
      const $ = cheerio.load(text);
      const seen: Record<string, number> = {};
      $("table tr").each((_, tr) => {
        const cells = $(tr)
          .find("td, th")
          .toArray()
          .map((c) => $(c).text().replace(/\s+/g, " ").trim());
        if (cells.length < 4 || cells[0] === "Sản phẩm") return;
        const label = cells[0].split("·")[0].trim();
        const brand = SILVER_BRANDS.find((b) => label.endsWith(b));
        if (!brand || brand === "Bảo Tín Mạnh Hải") return;
        if ((seen[brand] ?? 0) >= 2) return;
        const buy = vnNum(cells[1]);
        const sell = vnNum(cells[2]);
        if (buy === null && sell === null) return;
        const name = label.slice(0, -brand.length).trim();
        const chRaw = (cells[3] ?? "").trim();
        let change: number | null = null;
        if (chRaw.startsWith("±")) change = 0;
        else if (chRaw && chRaw !== "-") {
          const v = vnNum(chRaw.replace(/[^\d.,-]/g, ""));
          if (v !== null) change = chRaw.startsWith("▼") ? -v : v;
        }
        seen[brand] = (seen[brand] ?? 0) + 1;
        items.push({ brand, name, buy, sell, change, source: "webgia" });
      });
    }
  } catch {
    // ignore
  }

  try {
    const { status, text } = await fetchText("https://baotinmanhhai.vn/bang-gia-vang", 10000);
    if (status < 400) {
      for (const row of parseBtmhSilver(text)) {
        items.push({ ...row, brand: "Bảo Tín Mạnh Hải", source: "btmh" });
      }
    }
  } catch {
    // ignore
  }
  return items.length ? items : null;
}

// ============================================================================
// Thị trường mở rộng: chỉ số CK VN, crypto, dầu thô, chỉ số toàn cầu
// ============================================================================
async function tvQuote(
  symbol: string,
): Promise<{ close: number; change_abs: number; change: number } | null> {
  try {
    const url = `https://scanner.tradingview.com/symbol?symbol=${encodeURIComponent(symbol)}&fields=close,change_abs,change`;
    const { data } = await fetchJson<{ close?: number; change_abs?: number; change?: number }>(url, 7000);
    const close = Number(data?.close ?? 0);
    if (!(close > 0)) return null;
    return {
      close,
      change_abs: Number(data?.change_abs ?? 0),
      change: Number(data?.change ?? 0),
    };
  } catch {
    return null;
  }
}

const INDEX_DEFS: Array<[string, string]> = [
  ["VNINDEX", "VN-Index"],
  ["VN30", "VN30"],
  ["HNX", "HNX-Index"],
  ["HNX30", "HNX30"],
];

async function fetchIndices() {
  const now = Math.floor(Date.now() / 1000);
  const from = now - 20 * 86400;
  const items: Array<{
    code: string;
    name: string;
    close: number;
    change: number;
    change_pct: number;
    volume: number | null;
    ts: number;
  }> = [];
  await Promise.all(
    INDEX_DEFS.map(async ([symbol, name]) => {
      try {
        const url = `https://services.entrade.com.vn/chart-api/v2/ohlcs/index?from=${from}&to=${now}&symbol=${symbol}&resolution=1D`;
        const { data } = await fetchJson<{ t?: number[]; c?: number[]; v?: number[] }>(url, 9000, {
          "User-Agent": BROWSER_UA,
        });
        const t = data?.t ?? [];
        const c = data?.c ?? [];
        if (!t.length || !c.length) return;
        const i = c.length - 1;
        const close = c[i];
        const prev = i > 0 ? c[i - 1] : close;
        const change = close - prev;
        items.push({
          code: symbol,
          name,
          close,
          change,
          change_pct: prev > 0 ? (change / prev) * 100 : 0,
          volume: data?.v?.[i] ?? null,
          ts: t[i] ?? now,
        });
      } catch {
        // bỏ qua chỉ số lỗi, giữ các chỉ số còn lại
      }
    }),
  );
  items.sort((a, b) => INDEX_DEFS.findIndex(([s]) => s === a.code) - INDEX_DEFS.findIndex(([s]) => s === b.code));
  return items.length ? items : null;
}

const CRYPTO_DEFS: Array<[string, string, string]> = [
  ["bitcoin", "BTC", "Bitcoin"],
  ["ethereum", "ETH", "Ethereum"],
  ["solana", "SOL", "Solana"],
];

async function fetchCrypto() {
  try {
    const ids = CRYPTO_DEFS.map(([id]) => id).join(",");
    const { data } = await fetchJson<
      Record<string, { usd?: number; vnd?: number; usd_24h_change?: number }>
    >(
      `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd,vnd&include_24hr_change=true`,
      9000,
    );
    const items = CRYPTO_DEFS.map(([id, code, name]) => {
      const row = data?.[id];
      if (!row?.usd) return null;
      return {
        code,
        name,
        usd: Number(row.usd),
        vnd: row.vnd ? Number(row.vnd) : null,
        change_24h: Number(row.usd_24h_change ?? 0),
      };
    }).filter(Boolean);
    return items.length ? items : null;
  } catch {
    return null;
  }
}

async function fetchOil() {
  const defs: Array<[string, string, string]> = [
    ["BRENT", "Dầu Brent", "NYMEX:BZ1!"],
    ["WTI", "Dầu WTI", "NYMEX:CL1!"],
  ];
  const items: Array<{
    code: string;
    name: string;
    price: number;
    change_abs: number;
    change_pct: number;
  }> = [];
  for (const [code, name, symbol] of defs) {
    const q = await tvQuote(symbol);
    if (q) {
      items.push({ code, name, price: q.close, change_abs: q.change_abs, change_pct: q.change });
    }
  }
  return items.length ? items : null;
}

async function fetchGlobal() {
  const defs: Array<[string, string, string, string]> = [
    ["DXY", "Chỉ số USD (DXY)", "TVC:DXY", ""],
    ["US10Y", "Lợi suất Mỹ 10 năm", "TVC:US10Y", "%"],
  ];
  const items: Array<{
    code: string;
    name: string;
    value: number;
    change_abs: number;
    change_pct: number;
    unit: string;
  }> = [];
  for (const [code, name, symbol, unit] of defs) {
    const q = await tvQuote(symbol);
    if (q) {
      items.push({ code, name, value: q.close, change_abs: q.change_abs, change_pct: q.change, unit });
    }
  }
  return items.length ? items : null;
}

const EXTRAS_TTL: Record<string, number> = {
  silver: 120,
  silver_domestic: 600,
  fx: 1800,
  fuel: 3600,
  indices: 300,
  crypto: 120,
  oil: 180,
  global: 180,
};
const extrasCache: Record<string, { ts: number; data: unknown }> = {};

async function cachedSection<T>(
  key: string,
  now: number,
  fetcher: () => Promise<T | null>,
  wrap: (data: T) => Record<string, unknown>,
): Promise<Record<string, unknown> | null> {
  const cached = extrasCache[key];
  if (cached && now - cached.ts < EXTRAS_TTL[key]) {
    return { ts: cached.ts, stale: false, ...wrap(cached.data as T) };
  }
  const fresh = await fetcher();
  if (fresh === null) {
    if (!cached) return null;
    return { ts: cached.ts, stale: true, ...wrap(cached.data as T) };
  }
  extrasCache[key] = { ts: now, data: fresh };
  return { ts: now, stale: false, ...wrap(fresh) };
}

export async function getExtras(): Promise<Record<string, unknown>> {
  const now = Math.floor(Date.now() / 1000);
  const [silver, silverDomestic, fx, fuel] = await Promise.all([
    cachedSection("silver", now, fetchSilver, (d) => {
      const out: Record<string, unknown> = { ...d };
      const latestFx = db.latestFx();
      if (latestFx?.usd_vnd) {
        out.vnd_per_luong = Math.round(d.price_usd * latestFx.usd_vnd * OZ_PER_LUONG);
      }
      return out;
    }),
    cachedSection("silver_domestic", now, fetchSilverDomestic, (items) => ({
      source: "Hãng + WebGia",
      items,
    })),
    cachedSection("fx", now, fetchVcbFx, (items) => ({
      source: "Vietcombank",
      items,
    })),
    cachedSection("fuel", now, fetchFuel, (items) => ({
      source: "Petrolimex",
      items,
    })),
  ]);
  const [indices, crypto, oil, globalIdx] = await Promise.all([
    cachedSection("indices", now, fetchIndices, (items) => ({
      source: "Entrade/DNSE",
      items,
    })),
    cachedSection("crypto", now, fetchCrypto, (items) => ({
      source: "CoinGecko",
      items,
    })),
    cachedSection("oil", now, fetchOil, (items) => ({
      source: "TradingView",
      items,
    })),
    cachedSection("global", now, fetchGlobal, (items) => ({
      source: "TradingView",
      items,
    })),
  ]);
  return {
    ts: now,
    silver,
    silver_domestic: silverDomestic,
    fx,
    fuel,
    indices,
    crypto,
    oil,
    global: globalIdx,
  };
}

// ============================================================================
// News (VnExpress, CafeF, VietnamNet, VTV RSS)
// ============================================================================
const RSS_FEEDS: Array<[string, string]> = [
  ["VnExpress", "https://vnexpress.net/rss/kinh-doanh.rss"],
  ["CafeF", "https://cafef.vn/thi-truong-chung-khoan.rss"],
  ["VietnamNet", "https://vietnamnet.vn/rss/kinh-doanh.rss"],
  ["VTV", "https://vtv.vn/rss/kinh-te.rss"],
];
const GOLD_RE = /vàng|gold|xau|sjc|doji|pnj|ounce|kim loại quý|lượng vàng/i;
const IMG_RE = /<img[^>]+src=["']([^"']+)["']/i;

export async function refreshNews(): Promise<number> {
  const merged = new Map<
    string,
    { link: string; title: string; source: string; published: number; image: string }
  >();

  await Promise.allSettled(
    RSS_FEEDS.map(async ([source, url]) => {
      const { status, text } = await fetchText(url, 12000, {
        "User-Agent": BROWSER_UA,
        Accept: "application/rss+xml, application/xml, text/xml, */*",
      });
      if (status >= 400) return;
      const parsed = xmlParser.parse(text) as {
        rss?: { channel?: { item?: Array<Record<string, unknown>> | Record<string, unknown> } };
      };
      const rawItems = parsed?.rss?.channel?.item;
      const items = (Array.isArray(rawItems) ? rawItems : rawItems ? [rawItems] : []).slice(0, 40);

      for (const item of items) {
        const title = String(item.title ?? "").replace(/\s+/g, " ").trim();
        const link = String(item.link ?? "").trim();
        if (!title || !link) continue;
        const desc = String(item.description ?? "");
        if (!GOLD_RE.test(`${title} ${desc}`)) continue;
        const pubMs = item.pubDate ? Date.parse(String(item.pubDate)) : NaN;
        const published = Number.isFinite(pubMs) ? Math.floor(pubMs / 1000) : 0;

        let image = "";
        const enc = item.enclosure as Record<string, string> | undefined;
        if (enc?.["@_url"] && (enc["@_type"] ?? "").startsWith("image")) {
          image = enc["@_url"];
        } else {
          const media =
            (item["media:content"] as Record<string, string> | undefined) ??
            (item["media:thumbnail"] as Record<string, string> | undefined);
          if (media?.["@_url"]) image = media["@_url"];
          else {
            const m = desc.match(IMG_RE);
            if (m) image = m[1];
          }
        }

        const prev = merged.get(link);
        if (!prev || published > prev.published) {
          merged.set(link, { link, title, source, published, image });
        }
      }
    }),
  );

  const now = Math.floor(Date.now() / 1000);
  const rows = [...merged.values()].map((r) => ({ ...r, fetched_at: now }));
  if (rows.length) {
    db.upsertNews(rows);
  }
  db.pruneNews(now - 7 * 86400);
  return rows.length;
}
