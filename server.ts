import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express, { type NextFunction, type Request, type Response } from "express";
import { WebSocketServer } from "ws";
import { SJC_CODE, computePremium, hub, poller } from "./server/poller.ts";
import { getExtras, getTechnicals, refreshNews } from "./server/providers.ts";
import { db } from "./server/store.ts";
import { GOLD_TYPES, brandGroups, featuredTypes, resolve } from "./server/symbols.ts";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 3000);
const IS_PROD = process.env.NODE_ENV === "production";
const API_TOKEN = (process.env.GOLD_API_TOKEN || "").trim();
const RATE_LIMIT = Number(process.env.GOLD_RATE_LIMIT_PER_MIN || 120);
const CORS_ORIGINS = (process.env.GOLD_CORS_ORIGINS || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const app = express();
app.use(express.json());

// CORS
app.use((req: Request, res: Response, next: NextFunction) => {
  const origin = req.headers.origin;
  if (origin && (CORS_ORIGINS.includes("*") || CORS_ORIGINS.includes(origin))) {
    res.setHeader("Access-Control-Allow-Origin", origin);
  }
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type,X-Api-Token");
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  next();
});

// Rate limiter for /api/*
const hits = new Map<string, number[]>();
app.use("/api", (req: Request, res: Response, next: NextFunction) => {
  if (RATE_LIMIT <= 0) {
    next();
    return;
  }
  const now = Date.now();
  const ip =
    (req.headers["x-forwarded-for"] as string | undefined)?.split(",")[0]?.trim() ||
    req.socket.remoteAddress ||
    "unknown";
  if (hits.size > 1000) hits.clear();
  const recent = (hits.get(ip) ?? []).filter((ts) => now - ts < 60_000);
  if (recent.length >= RATE_LIMIT) {
    res.status(429).json({ detail: "Quá nhiều yêu cầu — thử lại sau ít giây." });
    return;
  }
  recent.push(now);
  hits.set(ip, recent);
  next();
});

function requireToken(req: Request, res: Response, next: NextFunction): void {
  if (!API_TOKEN) {
    next();
    return;
  }
  const provided = req.headers["x-api-token"];
  if (provided !== API_TOKEN) {
    res.status(401).json({ detail: "Yêu cầu X-Api-Token hợp lệ." });
    return;
  }
  next();
}

// ============================================================================
// API Routes
// ============================================================================
app.get("/api", (_req: Request, res: Response) => {
  res.json({
    endpoints: [
      "/api/health",
      "/api/symbols",
      "/api/quotes",
      "/api/quotes/{ref}",
      "/api/history/{ref}",
      "/api/alerts",
      "/api/ws",
    ],
  });
});

app.get("/api/health", (_req: Request, res: Response) => {
  res.json({
    ok: true,
    app: "Aurum Terminal",
    time: Math.floor(Date.now() / 1000),
    status: { ...poller.status, clients: hub.count },
    clients: hub.count,
  });
});

app.get("/api/metrics", requireToken, (_req: Request, res: Response) => {
  res.json({
    ts: Math.floor(Date.now() / 1000),
    metrics: poller.metrics,
    source: poller.status.source,
    polls: poller.status.polls,
    last_success: poller.status.last_success,
    last_error: poller.status.last_error,
  });
});

app.get("/api/symbols", (req: Request, res: Response) => {
  const featured = req.query.featured === "true" || req.query.featured === "1";
  const items = featured ? featuredTypes() : GOLD_TYPES;
  const brands = brandGroups(featured).map((g) => ({
    brand: g.brand,
    label: g.label,
    order: g.order,
    count: g.count,
  }));
  res.json({ count: items.length, items, brands });
});

app.get("/api/quotes", (_req: Request, res: Response) => {
  const latest = Object.keys(poller.latest).length ? poller.latest : db.latestQuotes();
  const items = Object.values(latest).sort((a, b) => a.code.localeCompare(b.code));
  res.json({
    ts: Math.floor(Date.now() / 1000),
    source: poller.status.source,
    count: items.length,
    items,
  });
});

app.get("/api/quotes/:ref", (req: Request, res: Response) => {
  const meta = resolve(String(req.params.ref));
  if (!meta) {
    res.status(404).json({ detail: `Không tìm thấy loại vàng: ${req.params.ref}` });
    return;
  }
  const latest = Object.keys(poller.latest).length ? poller.latest : db.latestQuotes();
  const row = latest[meta.code];
  if (!row) {
    res.status(503).json({ detail: "Chưa có dữ liệu giá (poller chưa chạy)" });
    return;
  }
  res.json(row);
});

app.get("/api/sparklines", (req: Request, res: Response) => {
  const hours = Math.max(1, Math.min(168, Number(req.query.hours) || 24));
  const since = Math.floor(Date.now() / 1000) - hours * 3600;
  const series = db.sparklines(
    since,
    GOLD_TYPES.map((m) => m.code),
  );
  const count = Object.values(series).reduce((acc, arr) => acc + arr.length, 0);
  res.json({ since, series, count });
});

app.get("/api/history/:ref", async (req: Request, res: Response) => {
  const meta = resolve(String(req.params.ref));
  if (!meta) {
    res.status(404).json({ detail: `Không tìm thấy loại vàng: ${req.params.ref}` });
    return;
  }
  const days = Math.max(1, Math.min(30, Number(req.query.days) || 30));
  const code = meta.code;

  let daily = db.daily(code, days);
  if (daily.length < Math.min(days, 3) && poller.provider.supportsHistory?.(code)) {
    try {
      const rows = (await poller.provider.fetchHistory?.(code, days)) ?? [];
      if (rows.length) {
        db.upsertDaily(rows.filter((r) => r.date).map((r) => ({ code, ...r })));
        daily = db.daily(code, days);
      }
    } catch {
      // fall through to mock history fallback
    }
  }

  if (daily.length < 2) {
    const mockRows = await poller.fallback.fetchHistory(code, days);
    daily = mockRows.map((r) => ({ code, ...r }));
  }

  const now = Math.floor(Date.now() / 1000);
  const since = now - 24 * 3600;
  let intraday = db.series(code, since);
  if (intraday.length < 2) {
    const latest = poller.latest[code];
    const baseBuy = latest?.buy ?? (meta.unit === "USD" ? 4177.8 : 140_500_000);
    const baseSell = latest?.sell ?? (meta.unit === "USD" ? 0 : baseBuy * 1.021);
    intraday = Array.from({ length: 12 }, (_, idx) => {
      const offset = (11 - idx) * 1800;
      const factor = 1 + Math.sin(idx / 2) * 0.0005;
      return {
        ts: now - offset,
        buy: Math.round(baseBuy * factor * 100) / 100,
        sell: baseSell > 0 ? Math.round(baseSell * factor * 100) / 100 : 0,
      };
    });
  }

  res.json({
    code,
    meta,
    days,
    daily,
    intraday,
    source: poller.status.source,
  });
});

app.get("/api/premium", (_req: Request, res: Response) => {
  const latest = Object.keys(poller.latest).length ? poller.latest : db.latestQuotes();
  const sjc = latest[SJC_CODE];
  const xau = latest["XAUUSD"];
  const fx = db.latestFx();
  if (!sjc || !xau || !fx) {
    res.status(503).json({ detail: "Chưa đủ dữ liệu (giá SJC / XAUUSD / tỷ giá)" });
    return;
  }
  const gap = computePremium(sjc.sell, xau.buy, fx.usd_vnd);
  if (!gap) {
    res.status(503).json({ detail: "Dữ liệu giá chưa hợp lệ để tính chênh lệch" });
    return;
  }
  res.json({
    ts: Math.floor(Date.now() / 1000),
    sjc: { code: SJC_CODE, name: sjc.name, sell: sjc.sell, source: sjc.source },
    xau: { buy: xau.buy, source: xau.source },
    fx: { usd_vnd: fx.usd_vnd, source: fx.source, ts: fx.ts },
    ...gap,
  });
});

app.get("/api/extras", async (_req: Request, res: Response) => {
  const data = await getExtras();
  res.json(data);
});

app.get("/api/technicals", async (_req: Request, res: Response) => {
  const data = await getTechnicals();
  if (!data) {
    res.status(503).json({ detail: "Chưa lấy được chỉ số kỹ thuật từ TradingView" });
    return;
  }
  res.json(data);
});

app.get("/api/news", async (req: Request, res: Response) => {
  const limit = Math.max(1, Math.min(100, Number(req.query.limit) || 30));
  let items = db.listNews(limit);
  if (!items.length) {
    try {
      await refreshNews();
      items = db.listNews(limit);
    } catch {
      // ignore if offline
    }
  }
  res.json({ count: items.length, items });
});

app.get("/api/alerts", (_req: Request, res: Response) => {
  res.json({ items: db.listAlerts() });
});

app.post("/api/alerts", requireToken, (req: Request, res: Response) => {
  const body = (req.body ?? {}) as {
    code?: string;
    direction?: string;
    threshold?: number;
    note?: string;
    target_price?: number | null;
  };
  const meta = resolve(String(body.code ?? ""));
  if (!meta) {
    res.status(404).json({ detail: `Không tìm thấy loại vàng: ${body.code}` });
    return;
  }
  const direction = body.direction === "down" ? "down" : body.direction === "up" ? "up" : null;
  if (!direction) {
    res.status(422).json({ detail: "direction phải là 'up' hoặc 'down'" });
    return;
  }
  const threshold = Number(body.threshold ?? 0);
  const targetPrice =
    body.target_price !== undefined && body.target_price !== null && Number(body.target_price) > 0
      ? Number(body.target_price)
      : null;
  if (targetPrice === null && threshold <= 0) {
    res.status(422).json({ detail: "Cần ngưỡng % > 0 hoặc giá mục tiêu > 0" });
    return;
  }
  const row = db.addAlert(
    meta.code,
    direction,
    Number(threshold.toFixed(4)),
    String(body.note ?? "").trim(),
    targetPrice,
  );
  res.status(201).json(row);
});

app.delete("/api/alerts/:id", requireToken, (req: Request, res: Response) => {
  const id = Number(req.params.id);
  if (!db.deleteAlert(id)) {
    res.status(404).json({ detail: "Không tồn tại alert" });
    return;
  }
  res.json({ deleted: id });
});

app.patch("/api/alerts/:id", requireToken, (req: Request, res: Response) => {
  const id = Number(req.params.id);
  const active = req.query.active === "true" || req.query.active === "1";
  if (!db.setAlertActive(id, active)) {
    res.status(404).json({ detail: "Không tồn tại alert" });
    return;
  }
  res.json({ id, active });
});

// ============================================================================
// HTTP + WebSocket + Vite / Static SPA
// ============================================================================
const server = http.createServer(app);
const wss = new WebSocketServer({ noServer: true });

wss.on("connection", (ws, req) => {
  const url = new URL(req.url || "/api/ws", "http://localhost");
  const rawTopics = url.searchParams.get("topics") || "quote,status,alert";
  const wanted = new Set(
    rawTopics
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );
  if (!wanted.size) wanted.add("quote");

  hub.connect(ws, wanted);
  const latest = Object.keys(poller.latest).length ? poller.latest : db.latestQuotes();
  ws.send(
    JSON.stringify({
      type: "snapshot",
      ts: Math.floor(Date.now() / 1000),
      quotes: Object.values(latest),
      status: { ...poller.status, clients: hub.count },
    }),
  );

  ws.on("message", (raw) => {
    try {
      const msg = JSON.parse(String(raw)) as { op?: string; topics?: string[] };
      if (msg.op === "subscribe") {
        const next = new Set(Array.isArray(msg.topics) && msg.topics.length ? msg.topics : wanted);
        hub.setTopics(ws, next);
        ws.send(JSON.stringify({ type: "subscribed", topics: [...next].sort() }));
      } else if (msg.op === "ping") {
        ws.send(JSON.stringify({ type: "pong", ts: Math.floor(Date.now() / 1000) }));
      }
    } catch {
      // ignore invalid JSON
    }
  });

  ws.on("close", () => hub.disconnect(ws));
  ws.on("error", () => hub.disconnect(ws));
});

server.on("upgrade", (req, socket, head) => {
  const pathname = new URL(req.url || "/", "http://localhost").pathname;
  if (pathname === "/api/ws") {
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit("connection", ws, req);
    });
  } else if (!IS_PROD) {
    // Allow non-API upgrades (e.g. Vite) to close cleanly if unhandled
    socket.destroy();
  } else {
    socket.destroy();
  }
});

async function startServer() {
  if (!IS_PROD) {
    const { createServer: createViteServer } = await import("vite");
    const vite = await createViteServer({
      configFile: path.resolve(__dirname, "vite.config.ts"),
      server: { middlewareMode: true, hmr: false },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distDir = path.resolve(__dirname, "dist");
    app.use(express.static(distDir));
    app.get("*", (_req: Request, res: Response) => {
      res.sendFile(path.join(distDir, "index.html"));
    });
  }

  if (process.env.GOLD_ENABLE_POLLER !== "0") {
    await poller.start();
  } else {
    await poller.seed();
  }

  server.listen(PORT, "0.0.0.0", () => {
    console.log(`Aurum Terminal listening on http://0.0.0.0:${PORT}`);
  });
}

void startServer();

process.on("SIGTERM", () => {
  poller.stop();
  server.close();
});
process.on("SIGINT", () => {
  poller.stop();
  server.close();
});
