import { fmtPct, fmtSigned } from "../lib/format";

export default function ChangeChip({
  change,
  pct,
  unit,
  withAmount = true,
}: {
  change: number;
  pct: number;
  unit: string;
  withAmount?: boolean;
}) {
  const tone = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
  return (
    <span className={`chip chip--${tone}`}>
      {withAmount && <span>{fmtSigned(change, unit)}</span>}
      <span>{fmtPct(pct)}</span>
    </span>
  );
}
