import type { Alert, BrandInfo, GoldType, HistoryPayload, Quote, Status } from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ ok: boolean; status: Status; clients: number }>("/health"),
  symbols: (featured = false) =>
    request<{ count: number; items: GoldType[]; brands?: BrandInfo[] }>(
      `/symbols?featured=${featured}`,
    ),
  quotes: () => request<{ ts: number; source: string | null; count: number; items: Quote[] }>("/quotes"),
  quote: (ref: string) => request<Quote>(`/quotes/${encodeURIComponent(ref)}`),
  history: (ref: string, days = 30) =>
    request<HistoryPayload>(`/history/${encodeURIComponent(ref)}?days=${days}`),
  alerts: () => request<{ items: Alert[] }>("/alerts"),
  createAlert: (body: { code: string; direction: "up" | "down"; threshold: number; note: string }) =>
    request<Alert>("/alerts", { method: "POST", body: JSON.stringify(body) }),
  deleteAlert: (id: number) => request<{ deleted: number }>(`/alerts/${id}`, { method: "DELETE" }),
  toggleAlert: (id: number, active: boolean) =>
    request<{ id: number; active: boolean }>(`/alerts/${id}?active=${active}`, { method: "PATCH" }),
};

export function wsUrl(topics: string[]): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.host;
  return `${proto}://${host}/api/ws?topics=${encodeURIComponent(topics.join(","))}`;
}
