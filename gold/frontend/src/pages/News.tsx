import { useEffect, useState } from "react";
import { fmtAgo } from "../lib/format";
import { ageSeconds, useNow } from "../lib/useNow";

interface NewsItem {
  link: string;
  title: string;
  source: string;
  published: number;
  image: string;
}

export default function News() {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const now = useNow(30_000);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await fetch("/api/news?limit=40");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as { items: NewsItem[] };
        if (alive) setItems(data.items ?? []);
      } catch (e) {
        if (alive) setError(String(e));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page__title">Tin tức vàng</h1>
          <p className="page__sub">
            Tổng hợp tin liên quan vàng từ VnExpress · CafeF · VietnamNet · VTV — bấm để đọc gốc
          </p>
        </div>
        <span className="meta">{items.length} TIN</span>
      </div>

      {loading ? (
        <div className="empty">Đang tải tin tức…</div>
      ) : error ? (
        <div className="empty">{error}</div>
      ) : !items.length ? (
        <div className="empty">Chưa có tin vàng mới.</div>
      ) : (
        <section className="panel">
          <div className="panel__body" style={{ display: "grid", gap: 4 }}>
            {items.map((n) => {
              const age = n.published ? ageSeconds(n.published, now) : null;
              return (
                <a
                  key={n.link}
                  href={n.link}
                  target="_blank"
                  rel="noreferrer"
                  className="row"
                  style={{ gap: 14, padding: "10px 4px", textDecoration: "none", color: "inherit" }}
                >
                  {n.image ? (
                    <img
                      src={n.image}
                      alt=""
                      loading="lazy"
                      style={{
                        width: 132,
                        height: 76,
                        objectFit: "cover",
                        borderRadius: 8,
                        flexShrink: 0,
                      }}
                    />
                  ) : null}
                  <span style={{ minWidth: 0 }}>
                    <span style={{ display: "block", fontWeight: 600, lineHeight: 1.45 }}>
                      {n.title}
                    </span>
                    <span className="meta">
                      {n.source}
                      {age !== null ? ` · ${fmtAgo(age).toUpperCase()}` : ""}
                    </span>
                  </span>
                </a>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
