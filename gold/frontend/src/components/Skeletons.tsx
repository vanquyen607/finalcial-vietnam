export function HeroStatsSkeleton() {
  return (
    <div className="hero-stats" aria-busy="true" aria-label="Đang tải số liệu">
      <div className="hero-stat hero-stat--primary">
        <div className="hero-stat__head">
          <span className="skeleton skeleton-line" style={{ width: "48%", height: 12 }} />
          <span className="skeleton skeleton-line" style={{ width: "78%", height: 30, marginTop: 8 }} />
        </div>
        <span className="skeleton skeleton-chip" style={{ width: 124, height: 26, marginTop: 10 }} />
      </div>
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="hero-stat">
          <span className="skeleton skeleton-line" style={{ width: "54%", height: 12 }} />
          <span className="skeleton skeleton-line" style={{ width: "72%", height: 24, marginTop: 6 }} />
          <span className="skeleton skeleton-line" style={{ width: "44%", height: 11, marginTop: 4 }} />
        </div>
      ))}
    </div>
  );
}

export function MarketStripSkeleton() {
  return (
    <div className="extras" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <div key={i} className="extras__card">
          <div className="extras__head">
            <span className="skeleton skeleton-line" style={{ width: "36%", height: 14 }} />
            <span className="skeleton skeleton-line" style={{ width: "22%", height: 12 }} />
          </div>
          <div className="extras__rows">
            {[0, 1, 2].map((r) => (
              <div key={r} className="extras__row">
                <span className="skeleton skeleton-line" style={{ width: "42%", height: 13 }} />
                <span className="skeleton skeleton-line" style={{ width: "30%", height: 13 }} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function TablePanelSkeleton({ rows = 7 }: { rows?: number }) {
  return (
    <section className="panel panel--table" aria-busy="true" aria-label="Đang tải bảng giá">
      <div className="panel__head">
        <span className="skeleton skeleton-line" style={{ width: 150, height: 15 }} />
        <span className="skeleton skeleton-line" style={{ width: 96, height: 12 }} />
      </div>
      <div className="skeleton-table">
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="skeleton-row">
            <span className="skeleton skeleton-line" style={{ width: i % 3 === 0 ? "38%" : "48%", height: 15 }} />
            <span className="skeleton skeleton-line" style={{ width: "18%", height: 15 }} />
            <span className="skeleton skeleton-line" style={{ width: "18%", height: 15 }} />
          </div>
        ))}
      </div>
    </section>
  );
}
