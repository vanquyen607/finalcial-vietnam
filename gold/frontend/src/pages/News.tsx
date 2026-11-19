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

function NewsMedia({ src, source }: { src: string; source: string }) {
  const [broken, setBroken] = useState(false);

  if (!src || broken) {
    return (
      <div className="news-card__media">
        <div className="news-card__placeholder">{source || "TIN VÀNG"}</div>
      </div>
    );
  }

  return (
    <div className="news-card__media">
      <img
        src={src}
        alt=""
        loading="lazy"
        referrerPolicy="no-referrer"
        onError={() => setBroken(true)}
      />
    </div>
  );
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
        <div className="news-grid" aria-busy="true" aria-label="Đang tải tin tức">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="news-card news-card--skeleton" aria-hidden="true">
              <div className="news-card__media skeleton" />
              <div className="news-card__body">
                <div>
                  <span className="skeleton skeleton-line" style={{ width: "95%", height: 15 }} />
                  <span className="skeleton skeleton-line" style={{ width: "74%", height: 15, marginTop: 7 }} />
                </div>
                <div className="news-card__meta">
                  <span className="skeleton skeleton-line" style={{ width: 68, height: 11 }} />
                  <span className="skeleton skeleton-line" style={{ width: 54, height: 11 }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="empty">{error}</div>
      ) : !items.length ? (
        <div className="empty">Chưa có tin vàng mới.</div>
      ) : (
        <div className="news-grid">
          {items.map((n) => {
            const age = n.published ? ageSeconds(n.published, now) : null;
            return (
              <a
                key={n.link}
                href={n.link}
                target="_blank"
                rel="noreferrer"
                className="news-card"
              >
                <NewsMedia src={n.image} source={n.source} />
                <div className="news-card__body">
                  <h2 className="news-card__title">{n.title}</h2>
                  <div className="news-card__meta meta">
                    <span>{n.source}</span>
                    {age !== null && <span>{fmtAgo(age).toUpperCase()}</span>}
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
