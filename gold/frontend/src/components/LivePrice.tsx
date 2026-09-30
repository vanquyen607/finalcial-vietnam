import { useEffect, useRef, useState } from "react";
import { fmtPrice } from "../lib/format";

/** Giá nháy xanh/đỏ khi có tick mới từ WebSocket. */
export default function LivePrice({
  value,
  unit,
  className,
}: {
  value: number;
  unit: string;
  className?: string;
}) {
  const prev = useRef(value);
  const [cls, setCls] = useState("");

  useEffect(() => {
    if (value === prev.current) return;
    const up = value > prev.current;
    prev.current = value;
    setCls(up ? "flash-up" : "flash-down");
    const t = window.setTimeout(() => setCls(""), 1000);
    return () => window.clearTimeout(t);
  }, [value]);

  return <span className={`${cls} ${className ?? ""}`.trim()}>{fmtPrice(value, unit)}</span>;
}
