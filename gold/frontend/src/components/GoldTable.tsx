import { Fragment, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { changePct, fmtClock, fmtPct, fmtSigned, tone } from "../lib/format";
import { groupQuotes } from "../lib/groupQuotes";
import type { BrandInfo, GoldType, Quote } from "../lib/types";
import LivePrice from "./LivePrice";

interface Props {
  quotes: Quote[];
  metaByCode: Record<string, GoldType>;
  brands: BrandInfo[];
  fetchedAt?: number | null;
}

/** Bảng giá phẳng theo kiểu webgia: nhóm thương hiệu là một dòng tiêu đề. */
export default function GoldTable({ quotes, metaByCode, brands, fetchedAt }: Props) {
  const navigate = useNavigate();
  const groups = useMemo(
    () => groupQuotes(quotes, metaByCode, brands),
    [quotes, metaByCode, brands],
  );

  return (
    <div className="gold-table-wrap">
      <table className="gold-table">
        <thead>
          <tr>
            <th>Thương hiệu</th>
            <th>Loại vàng</th>
            <th className="num">Mua vào</th>
            <th className="num">Bán ra</th>
            <th className="num gt-spread">Chênh lệch</th>
            <th className="num gt-change">Thay đổi</th>
            <th className="num gt-time">Lúc</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((g) => (
            <Fragment key={g.brand}>
              <tr className="gold-table__group">
                <td colSpan={7}>
                  <span className="gold-table__brand">{g.label}</span>
                  <span className="gold-table__count">{g.items.length} loại</span>
                </td>
              </tr>
              {g.items.map((q) => {
                const meta = metaByCode[q.code];
                const pct = changePct(q.buy, q.change_buy);
                const t = tone(q.change_buy);
                const spread = q.sell > 0 ? q.sell - q.buy : 0;
                return (
                  <tr
                    key={q.code}
                    className="gold-table__row"
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/detail/${meta?.alias || q.code}`)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        navigate(`/detail/${meta?.alias || q.code}`);
                      }
                    }}
                  >
                    <td className="gt-brand">{g.label}</td>
                    <td>
                      <span className="gt-name">{meta?.product || q.name}</span>
                      <span className="gt-code">
                        {q.code} / {q.per || "lượng"}
                      </span>
                    </td>
                    <td className="num bid">
                      <LivePrice value={q.buy} unit={q.unit} />
                    </td>
                    <td className="num ask">
                      {q.sell > 0 ? <LivePrice value={q.sell} unit={q.unit} /> : "—"}
                    </td>
                    <td className="num muted gt-spread">{spread ? fmtSigned(spread, q.unit) : "—"}</td>
                    <td className={`num ${t} gt-change`}>
                      {q.change_buy ? (
                        <>
                          <span className="gt-delta">{fmtSigned(q.change_buy, q.unit)} </span>
                          <span>({fmtPct(pct)})</span>
                        </>
                      ) : (
                        fmtPct(0)
                      )}
                    </td>
                    <td className="num muted gt-time">{fmtClock(fetchedAt ?? q.ts)}</td>
                  </tr>
                );
              })}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
