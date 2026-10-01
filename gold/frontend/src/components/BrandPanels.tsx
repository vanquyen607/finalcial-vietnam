import { useCallback, useEffect, useMemo, useState } from "react";
import { fmtCompact } from "../lib/format";
import { groupQuotes } from "../lib/groupQuotes";
import { useMarket } from "../state/Market";
import PriceTable from "./PriceTable";

const STORE_KEY = "aurum.collapsed.brands";

function readCollapsed(): string[] {
  try {
    const raw = window.localStorage.getItem(STORE_KEY);
    const v: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

/** Bảng giá gộp theo nhà bán: mỗi nhà bán 1 khối, bấm header để gộp/mở. */
export default function BrandPanels({ fetchedAt }: { fetchedAt?: number | null }) {
  const { quoteList, metaByCode, brands } = useMarket();
  const [collapsed, setCollapsed] = useState<string[]>(readCollapsed);

  const groups = useMemo(
    () => groupQuotes(quoteList, metaByCode, brands),
    [quoteList, metaByCode, brands],
  );

  useEffect(() => {
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify(collapsed));
    } catch {
      /* localStorage có thể bị chặn (private mode) — bỏ qua */
    }
  }, [collapsed]);

  const toggle = useCallback((brand: string) => {
    setCollapsed((prev) =>
      prev.includes(brand) ? prev.filter((b) => b !== brand) : [...prev, brand],
    );
  }, []);

  const visible = groups.filter((g) => g.items.length > 0);
  const allClosed = visible.length > 0 && visible.every((g) => collapsed.includes(g.brand));
  const toggleAll = () => setCollapsed(allClosed ? [] : visible.map((g) => g.brand));

  if (!visible.length) return <div className="empty">Đang tải bảng giá theo nhà bán…</div>;

  return (
    <div className="bp">
      <div className="bp__toolbar">
        <span className="meta">
          {visible.length} NHÀ BÁN · {quoteList.length} LOẠI
        </span>
        {visible.length > 3 && (
          <button className="btn btn--ghost" onClick={toggleAll}>
            {allClosed ? "Mở tất cả" : "Gộp tất cả"}
          </button>
        )}
      </div>

      {visible.map((g) => {
        const open = !collapsed.includes(g.brand);
        const unit = g.unit;
        const range =
          g.maxBuy <= 0
            ? "—"
            : g.minBuy === g.maxBuy
              ? fmtCompact(g.maxBuy, unit)
              : `${fmtCompact(g.minBuy, unit)} – ${fmtCompact(g.maxBuy, unit)}`;

        return (
          <div className={`bp__group${open ? "" : " bp__group--closed"}`} key={g.brand}>
            <button
              type="button"
              className="bp__head"
              aria-expanded={open}
              onClick={() => toggle(g.brand)}
            >
              <span className="bp__chev" aria-hidden>
                ▸
              </span>
              <span className="bp__name">{g.label}</span>
              <span className="bp__count">{g.items.length} loại</span>
              <span className="bp__range mono">{range}</span>
              <span className="bp__moves">
                <span className="up">▲ {g.up}</span>
                <span className="down">▼ {g.down}</span>
                {g.flat > 0 && <span className="flat">─ {g.flat}</span>}
              </span>
            </button>

            {open && <PriceTable quotes={g.items} fetchedAt={fetchedAt} grouped />}
          </div>
        );
      })}
    </div>
  );
}
