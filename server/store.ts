import { BY_CODE } from "./symbols.ts";

export interface QuoteRow {
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

export interface DailyRow {
  code: string;
  date: string;
  buy: number;
  sell: number;
  day_change_buy: number;
  day_change_sell: number;
  updates: number;
}

export interface AlertRow {
  id: number;
  code: string;
  name?: string;
  direction: "up" | "down";
  threshold: number;
  target_price: number | null;
  note: string;
  active: number;
  created_at: number;
  triggered_at: number | null;
}

export interface FxRow {
  ts: number;
  usd_vnd: number;
  source: string;
}

export interface NewsRow {
  link: string;
  title: string;
  source: string;
  published: number;
  image: string;
  fetched_at: number;
}

class InMemoryStore {
  private quotesByCode = new Map<string, QuoteRow[]>();
  private latestByCode = new Map<string, QuoteRow>();
  private dailyByCode = new Map<string, Map<string, DailyRow>>();
  private alertsList: AlertRow[] = [];
  private nextAlertId = 1;
  private fxList: FxRow[] = [];
  private newsByLink = new Map<string, NewsRow>();

  insertQuotes(rows: QuoteRow[]): void {
    for (const row of rows) {
      this.latestByCode.set(row.code, row);
      const list = this.quotesByCode.get(row.code) ?? [];
      const last = list[list.length - 1];
      if (last && last.ts === row.ts) {
        list[list.length - 1] = row;
      } else if (!list.some((r) => r.ts === row.ts)) {
        list.push(row);
        list.sort((a, b) => a.ts - b.ts);
      }
      this.quotesByCode.set(row.code, list);
    }
  }

  latestQuotes(): Record<string, QuoteRow> {
    return Object.fromEntries(this.latestByCode.entries());
  }

  series(code: string, sinceTs: number): { ts: number; buy: number; sell: number }[] {
    const list = this.quotesByCode.get(code) ?? [];
    return list
      .filter((r) => r.ts >= sinceTs)
      .map((r) => ({ ts: r.ts, buy: r.buy, sell: r.sell }));
  }

  sparklines(
    sinceTs: number,
    codes: string[],
    maxPoints = 60,
  ): Record<string, { ts: number; buy: number }[]> {
    const out: Record<string, { ts: number; buy: number }[]> = {};
    for (const code of codes) {
      const list = (this.quotesByCode.get(code) ?? []).filter((r) => r.ts >= sinceTs);
      if (!list.length) continue;
      const step = Math.max(1, Math.floor(list.length / maxPoints));
      const sampled: { ts: number; buy: number }[] = [];
      for (let i = 0; i < list.length; i += step) {
        sampled.push({ ts: list[i].ts, buy: list[i].buy });
      }
      out[code] = sampled;
    }
    return out;
  }

  pruneQuotes(olderThanTs: number): number {
    let removed = 0;
    for (const [code, list] of this.quotesByCode.entries()) {
      const filtered = list.filter((r) => r.ts >= olderThanTs);
      removed += list.length - filtered.length;
      this.quotesByCode.set(code, filtered);
    }
    return removed;
  }

  upsertDaily(rows: DailyRow[]): void {
    for (const row of rows) {
      let byDate = this.dailyByCode.get(row.code);
      if (!byDate) {
        byDate = new Map();
        this.dailyByCode.set(row.code, byDate);
      }
      byDate.set(row.date, row);
    }
  }

  upsertDailySnapshot(rows: Omit<DailyRow, "updates">[]): void {
    for (const row of rows) {
      let byDate = this.dailyByCode.get(row.code);
      if (!byDate) {
        byDate = new Map();
        this.dailyByCode.set(row.code, byDate);
      }
      const existing = byDate.get(row.date);
      byDate.set(row.date, {
        ...row,
        updates: (existing?.updates ?? 0) + 1,
      });
    }
  }

  daily(code: string, days: number): DailyRow[] {
    const byDate = this.dailyByCode.get(code);
    if (!byDate) return [];
    const sorted = [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
    return sorted.slice(-days);
  }

  insertFx(usdVnd: number, source: string): void {
    const ts = Math.floor(Date.now() / 1000);
    this.fxList.push({ ts, usd_vnd: usdVnd, source });
  }

  latestFx(): FxRow | null {
    return this.fxList.length ? this.fxList[this.fxList.length - 1] : null;
  }

  pruneFx(olderThanTs: number): void {
    this.fxList = this.fxList.filter((r) => r.ts >= olderThanTs);
  }

  upsertNews(rows: NewsRow[]): void {
    for (const row of rows) {
      this.newsByLink.set(row.link, row);
    }
  }

  listNews(limit = 30): NewsRow[] {
    return [...this.newsByLink.values()]
      .sort((a, b) => b.published - a.published)
      .slice(0, limit);
  }

  pruneNews(olderThanTs: number): void {
    for (const [link, row] of this.newsByLink.entries()) {
      if (row.fetched_at < olderThanTs) {
        this.newsByLink.delete(link);
      }
    }
  }

  listAlerts(): AlertRow[] {
    return [...this.alertsList]
      .sort((a, b) => b.id - a.id)
      .map((a) => ({ ...a, name: BY_CODE[a.code]?.name ?? a.code }));
  }

  activeAlerts(): AlertRow[] {
    return this.alertsList.filter((a) => a.active === 1);
  }

  addAlert(
    code: string,
    direction: "up" | "down",
    threshold: number,
    note: string,
    targetPrice: number | null,
  ): AlertRow {
    const row: AlertRow = {
      id: this.nextAlertId++,
      code,
      name: BY_CODE[code]?.name ?? code,
      direction,
      threshold,
      target_price: targetPrice,
      note,
      active: 1,
      created_at: Math.floor(Date.now() / 1000),
      triggered_at: null,
    };
    this.alertsList.push(row);
    return row;
  }

  deleteAlert(id: number): boolean {
    const before = this.alertsList.length;
    this.alertsList = this.alertsList.filter((a) => a.id !== id);
    return this.alertsList.length < before;
  }

  setAlertActive(id: number, active: boolean): boolean {
    const found = this.alertsList.find((a) => a.id === id);
    if (!found) return false;
    found.active = active ? 1 : 0;
    return true;
  }

  markTriggered(id: number): void {
    const found = this.alertsList.find((a) => a.id === id);
    if (found) {
      found.triggered_at = Math.floor(Date.now() / 1000);
    }
  }
}

export const db = new InMemoryStore();
