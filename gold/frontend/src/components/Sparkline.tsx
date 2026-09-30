interface Props {
  values: number[];
  width?: number;
  height?: number;
  /** Nếu chưa có dữ liệu, vẽ đường phẳng mờ */
  empty?: boolean;
}

/** Sparkline mini (SVG) — không dùng thư viện để giữ nhẹ. */
export default function Sparkline({ values, height = 44, empty }: Props) {
  const pts = values.slice(-60);
  const show = pts.length > 1 && !empty;

  let path = "";
  let fill = "";
  let color = "#8e8e93";

  if (show) {
    const min = Math.min(...pts);
    const max = Math.max(...pts);
    const span = max - min;
    const w = 100;
    const h = 40;
    const step = w / (pts.length - 1);
    // giá không đổi → vẽ đường ngang giữa khung
    const yFor = (v: number) => (span ? h - ((v - min) / span) * h : h / 2);
    const coords = pts.map((v, i) => [i * step, yFor(v)] as const);
    path = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
    fill = `${path} L${w},${h} L0,${h} Z`;
    color = pts[pts.length - 1] >= pts[0] ? "#30d158" : "#ff453a";
  }

  return (
    <svg className="spark" viewBox="0 0 100 40" preserveAspectRatio="none" height={height}>
      {!show ? (
        <line x1="0" y1="20" x2="100" y2="20" stroke="#2c2c2e" strokeWidth="1" strokeDasharray="3 3" />
      ) : (
        <>
          <defs>
            <linearGradient id={`g-${color.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.30" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={fill} fill={`url(#g-${color.slice(1)})`} />
          <path d={path} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
        </>
      )}
    </svg>
  );
}
