import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api, wsUrl } from "../lib/api";
import type { BrandInfo, GoldType, Quote, Status } from "../lib/types";

export interface Toast {
  id: number;
  message: string;
  kind: "alert" | "info";
}

interface MarketValue {
  symbols: GoldType[];
  metaByCode: Record<string, GoldType>;
  /** thứ tự + tên hiển thị các nhà bán (backend sắp sẵn) */
  brands: BrandInfo[];
  quotes: Record<string, Quote>;
  quoteList: Quote[];
  status: Status;
  connected: boolean;
  loading: boolean;
  toasts: Toast[];
  dismissToast: (id: number) => void;
  refresh: () => Promise<void>;
}

const MarketCtx = createContext<MarketValue | null>(null);

function toArray(v: unknown): Quote[] {
  return Array.isArray(v) ? (v as Quote[]) : [];
}

export function MarketProvider({ children }: { children: ReactNode }) {
  const [symbols, setSymbols] = useState<GoldType[]>([]);
  const [brands, setBrands] = useState<BrandInfo[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [status, setStatus] = useState<Status>({ state: "starting" });
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const toastId = useRef(0);

  const pushToast = useCallback((message: string, kind: Toast["kind"] = "alert") => {
    const id = ++toastId.current;
    setToasts((t) => [...t.slice(-2), { id, message, kind }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000);
    if (kind === "alert" && "Notification" in window && Notification.permission === "granted") {
      try {
        new Notification("Aurum Terminal", { body: message, icon: "/icons/icon-192.png" });
      } catch {
        /* ignore */
      }
    }
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [q, s] = await Promise.all([api.quotes(), api.symbols()]);
      setQuotes(Object.fromEntries(q.items.map((x) => [x.code, x])));
      setSymbols(s.items);
      if (s.brands?.length) setBrands(s.brands);
      setStatus((prev) => ({ ...prev, source: q.source ?? prev.source ?? undefined }));
    } catch (e) {
      setStatus((prev) => ({ ...prev, state: "error", last_error: String(e) }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // ---- WebSocket với retry exponential ----
  useEffect(() => {
    let closed = false;
    let timer: number | undefined;

    const connect = () => {
      if (closed) return;
      const ws = new WebSocket(wsUrl(["quote", "status", "alert"]));
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setConnected(true);
      };
      ws.onmessage = (ev) => {
        let msg: Record<string, unknown>;
        try {
          msg = JSON.parse(ev.data as string);
        } catch {
          return;
        }
        if (msg.type === "snapshot" || msg.type === "quotes") {
          const list = toArray(msg.quotes);
          if (list.length) {
            setQuotes((prev) => {
              const next = { ...prev };
              for (const q of list) next[q.code] = q;
              return next;
            });
            setLoading(false);
          }
          if (msg.type === "snapshot" && msg.status) setStatus(msg.status as Status);
        } else if (msg.type === "status") {
          const { type: _t, ...rest } = msg as Record<string, unknown>;
          setStatus(rest as unknown as Status);
        } else if (msg.type === "alert") {
          pushToast(String(msg.message ?? "Cảnh báo giá vàng"), "alert");
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (closed) return;
        const wait = Math.min(15_000, 1000 * 2 ** retryRef.current++);
        timer = window.setTimeout(connect, wait);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closed = true;
      if (timer) window.clearTimeout(timer);
      wsRef.current?.close();
    };
  }, [pushToast]);

  const value = useMemo<MarketValue>(() => {
    const list = Object.values(quotes).sort((a, b) => {
      const fa = symbols.find((s) => s.code === a.code)?.featured ? 0 : 1;
      const fb = symbols.find((s) => s.code === b.code)?.featured ? 0 : 1;
      return fa - fb || a.name.localeCompare(b.name, "vi");
    });
    return {
      symbols,
      metaByCode: Object.fromEntries(symbols.map((s) => [s.code, s])),
      brands,
      quotes,
      quoteList: list,
      status,
      connected,
      loading,
      toasts,
      dismissToast,
      refresh,
    };
  }, [symbols, brands, quotes, status, connected, loading, toasts, dismissToast, refresh]);

  return <MarketCtx.Provider value={value}>{children}</MarketCtx.Provider>;
}

export function useMarket(): MarketValue {
  const ctx = useContext(MarketCtx);
  if (!ctx) throw new Error("useMarket phải dùng trong <MarketProvider>");
  return ctx;
}
