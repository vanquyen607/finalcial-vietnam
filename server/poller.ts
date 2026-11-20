import { WebSocket } from "ws";
import { db, type QuoteRow } from "./store.ts";
import {
  BtmhProvider,
  MergedProvider,
  MiHongProvider,
  MockProvider,
  NgocThamProvider,
  PrivateShopsProvider,
  SimplizeProvider,
  SjcProvider,
  VangTodayProvider,
  fetchUsdVnd,
  refreshNews,
  type GoldProvider,
  type ProviderQuote,
} from "./providers.ts";
import { GOLD_TYPES } from "./symbols.ts";

export const SJC_CODE = "SJL1L10";
const OZ_PER_TAEL = 37.5 / 31.1034768;

export function computePremium(
  sjcSell: number,
  xauSpot: number,
  usdVnd: number,
): { world_vnd_luong: number; gap_abs: number; gap_pct: number } | null {
  if (!sjcSell || !xauSpot || !usdVnd) return null;
  const world = xauSpot * usdVnd * OZ_PER_TAEL;
  if (world <= 0) return null;
  const gap = sjcSell - world;
  return {
    world_vnd_luong: Math.round(world),
    gap_abs: Math.round(gap),
    gap_pct: Number(((gap / world) * 100).toFixed(2)),
  };
}

class BroadcastHub {
  private clients = new Map<WebSocket, Set<string>>();

  get count(): number {
    return this.clients.size;
  }

  connect(ws: WebSocket, topics: Set<string>): void {
    this.clients.set(ws, topics);
  }

  setTopics(ws: WebSocket, topics: Set<string>): void {
    if (this.clients.has(ws)) {
      this.clients.set(ws, topics);
    }
  }

  disconnect(ws: WebSocket): void {
    this.clients.delete(ws);
  }

  broadcast(payload: Record<string, unknown>, topic: string): void {
    const raw = JSON.stringify(payload);
    for (const [ws, topics] of this.clients.entries()) {
      if (!topics.has(topic)) continue;
      if (ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(raw);
        } catch {
          this.clients.delete(ws);
        }
      }
    }
  }
}

export const hub = new BroadcastHub();

function dayChangePct(buy: number, change: number): number {
  const prev = buy - change;
  if (!prev) return 0;
  return Number(((change / prev) * 100).toFixed(4));
}

function evaluateAlerts(quotes: Record<string, QuoteRow>): Record<string, unknown>[] {
  const events: Record<string, unknown>[] = [];
  for (const alert of db.activeAlerts()) {
    const q = quotes[alert.code];
    if (!q) continue;
    const pct = dayChangePct(q.buy, q.change_buy);
    const target = alert.target_price;
    const hit =
      target !== null
        ? alert.direction === "up"
          ? q.buy >= target
          : q.buy <= target
        : alert.direction === "up"
          ? pct >= alert.threshold
          : pct <= -alert.threshold;
    if (!hit) continue;
    db.markTriggered(alert.id);
    db.setAlertActive(alert.id, false);
    const message =
      target === null
        ? `${q.name} ${alert.direction === "up" ? "tăng" : "giảm"} ${Math.abs(pct).toFixed(2)}% (ngưỡng ${alert.threshold.toFixed(2)}%)`
        : `${q.name} ${alert.direction === "up" ? "tăng" : "giảm"}: giá mua ${q.buy.toLocaleString("vi-VN")} ${alert.direction === "up" ? "≥" : "≤"} ${target.toLocaleString("vi-VN")}`;
    events.push({
      type: "alert",
      alert_id: alert.id,
      code: alert.code,
      name: q.name,
      direction: alert.direction,
      threshold: alert.threshold,
      target_price: target,
      pct,
      buy: q.buy,
      sell: q.sell,
      note: alert.note,
      ts: Math.floor(Date.now() / 1000),
      message,
    });
  }
  return events;
}

function buildProvider(name: string): GoldProvider {
  if (name === "mock") return new MockProvider();
  return new MergedProvider([
    new VangTodayProvider(),
    new MiHongProvider(),
    new BtmhProvider(),
    new NgocThamProvider(),
    new SimplizeProvider(),
    new PrivateShopsProvider(),
    new SjcProvider(),
  ]);
}

class Poller {
  readonly provider: GoldProvider;
  readonly fallback = new MockProvider();
  latest: Record<string, QuoteRow> = {};
  status: {
    state: "starting" | "live" | "error";
    source: string;
    last_success: number | null;
    last_error: string | null;
    polls: number;
    clients: number;
  };
  metrics: {
    poll_errors: number;
    last_poll_ms: number | null;
    provider_errors: Record<string, number>;
    provider_health: { errors: Record<string, string>; ok: Record<string, number> };
    fx: { ok: number; err: number; last_ok: number | null; last_err: number | null };
    news: { ok: number; err: number; last_ok: number | null; last_err: number | null };
  };

  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private histTimer: ReturnType<typeof setInterval> | null = null;
  private lastFx = 0;
  private lastNews = 0;
  private dayKey = "";
  private dayOpen = new Map<string, [number, number]>();

  constructor() {
    const providerName = process.env.GOLD_PROVIDER || "vangtoday";
    this.provider = buildProvider(providerName);
    this.status = {
      state: "starting",
      source: this.provider.name,
      last_success: null,
      last_error: null,
      polls: 0,
      clients: 0,
    };
    this.metrics = {
      poll_errors: 0,
      last_poll_ms: null,
      provider_errors: {},
      provider_health: { errors: {}, ok: {} },
      fx: { ok: 0, err: 0, last_ok: null, last_err: null },
      news: { ok: 0, err: 0, last_ok: null, last_err: null },
    };
  }

  private toRows(quotes: ProviderQuote[]): QuoteRow[] {
    const now = Math.floor(Date.now() / 1000);
    return quotes.map((q) => ({
      ts: q.updated_at || now,
      code: q.code,
      name: q.name,
      buy: q.buy,
      sell: q.sell,
      change_buy: q.change_buy,
      change_sell: q.change_sell,
      unit: q.unit,
      per: q.per,
      source: q.source,
    }));
  }

  private applyDayChange(rows: QuoteRow[], now: number): void {
    const day = new Date(now * 1000).toISOString().slice(0, 10);
    if (day !== this.dayKey) {
      this.dayKey = day;
      this.dayOpen.clear();
    }
    for (const r of rows) {
      let open = this.dayOpen.get(r.code);
      if (!open) {
        open = [r.buy, r.sell];
        this.dayOpen.set(r.code, open);
      }
      if (!r.change_buy && r.buy !== open[0]) {
        r.change_buy = r.buy - open[0];
      }
      if (!r.change_sell && r.sell && open[1] && r.sell !== open[1]) {
        r.change_sell = r.sell - open[1];
      }
    }
  }

  async seed(): Promise<void> {
    if (!Object.keys(this.latest).length) {
      const mockQuotes = await this.fallback.fetchCurrent();
      const rows = this.toRows(mockQuotes);
      this.latest = Object.fromEntries(rows.map((r) => [r.code, r]));
      this.status.state = "live";
      this.status.source = "mock";
      this.status.last_success = Math.floor(Date.now() / 1000);
    }
    if (!db.latestFx()) {
      db.insertFx(25450, "seed");
    }
  }

  async tick(): Promise<void> {
    const started = performance.now();
    let rows: QuoteRow[];
    let source: string;
    try {
      const quotes = await this.provider.fetchCurrent();
      rows = this.toRows(quotes);
      source = this.provider.name;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      this.status.last_error = msg;
      this.metrics.provider_errors[this.provider.name] =
        (this.metrics.provider_errors[this.provider.name] ?? 0) + 1;
      const fallbackQuotes = await this.fallback.fetchCurrent();
      rows = this.toRows(fallbackQuotes);
      source = this.fallback.name;
    }

    const now = Math.floor(Date.now() / 1000);
    if (this.provider instanceof MergedProvider) {
      this.metrics.provider_health = {
        errors: { ...this.provider.lastErrors },
        ok: { ...this.provider.lastOk },
      };
    }

    const isMock = source === this.fallback.name;
    if (!isMock) {
      this.applyDayChange(rows, now);
    }

    const prev = this.latest;
    const changed = rows.filter(
      (r) =>
        !prev[r.code] ||
        prev[r.code].buy !== r.buy ||
        prev[r.code].sell !== r.sell,
    );

    const nextSnapshot: Record<string, QuoteRow> = { ...prev };
    for (const r of rows) nextSnapshot[r.code] = r;
    this.latest = nextSnapshot;

    if (!isMock) {
      db.insertQuotes(rows);
      const today = new Date(now * 1000).toISOString().slice(0, 10);
      db.upsertDailySnapshot(
        rows.map((r) => ({
          code: r.code,
          date: today,
          buy: r.buy,
          sell: r.sell,
          day_change_buy: r.change_buy,
          day_change_sell: r.change_sell,
        })),
      );
    }

    this.status = {
      state: "live",
      source,
      last_success: now,
      last_error: isMock ? this.status.last_error : null,
      polls: this.status.polls + 1,
      clients: hub.count,
    };
    this.metrics.last_poll_ms = Math.round((performance.now() - started) * 10) / 10;

    const events = changed.length && !isMock ? evaluateAlerts(this.latest) : [];
    hub.broadcast(
      {
        type: "quotes",
        ts: now,
        source,
        changed: changed.map((r) => r.code),
        quotes: rows,
      },
      "quote",
    );
    for (const ev of events) {
      hub.broadcast(ev, "alert");
    }
    hub.broadcast({ type: "status", ...this.status }, "status");

    if (this.status.polls % 20 === 0) {
      db.pruneQuotes(now - 7 * 86400);
      db.pruneFx(now - 7 * 86400);
    }

    await this.maybeRefreshAux(now);
  }

  private async maybeRefreshAux(now: number): Promise<void> {
    if (now - this.lastFx >= 1800) {
      this.lastFx = now;
      try {
        const got = await fetchUsdVnd();
        if (got) {
          db.insertFx(got[0], got[1]);
          this.metrics.fx.ok += 1;
          this.metrics.fx.last_ok = now;
        }
      } catch {
        this.metrics.fx.err += 1;
        this.metrics.fx.last_err = now;
      }
    }
    if (now - this.lastNews >= 900) {
      this.lastNews = now;
      try {
        await refreshNews();
        this.metrics.news.ok += 1;
        this.metrics.news.last_ok = now;
      } catch {
        this.metrics.news.err += 1;
        this.metrics.news.last_err = now;
      }
    }
  }

  async refreshHistory(): Promise<void> {
    for (const meta of GOLD_TYPES) {
      const code = meta.code;
      if (!this.provider.supportsHistory?.(code) || !this.provider.fetchHistory) continue;
      try {
        const rows = await this.provider.fetchHistory(code, 30);
        const payload = rows.filter((r) => r.date).map((r) => ({ code, ...r }));
        if (payload.length) db.upsertDaily(payload);
      } catch {
        // ignore single symbol history error
      }
    }
  }

  async start(): Promise<void> {
    await this.seed();
    const intervalMs = Math.max(5000, Number(process.env.GOLD_POLL_INTERVAL || 30) * 1000);
    void this.tick().catch(() => {
      this.metrics.poll_errors += 1;
    });
    void this.refreshHistory().catch(() => undefined);

    this.pollTimer = setInterval(() => {
      void this.tick().catch((err) => {
        this.metrics.poll_errors += 1;
        this.status.state = "error";
        this.status.last_error = err instanceof Error ? err.message : String(err);
        hub.broadcast({ type: "status", ...this.status }, "status");
      });
    }, intervalMs);

    this.histTimer = setInterval(() => {
      void this.refreshHistory().catch(() => undefined);
    }, 600_000);
  }

  stop(): void {
    if (this.pollTimer) clearInterval(this.pollTimer);
    if (this.histTimer) clearInterval(this.histTimer);
    this.pollTimer = null;
    this.histTimer = null;
  }
}

export const poller = new Poller();
