import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { ExtrasPayload } from "./types";

export function useExtras() {
  const [data, setData] = useState<ExtrasPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await api.extras();
      setData(res);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 120_000);
    return () => window.clearInterval(id);
  }, [refresh]);

  return { data, loading, error, refresh };
}
