/** Dấu hiệu Aurum — lục giác vàng, dùng lại cho splash/favicon. */
export default function Logo({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden>
      <defs>
        <linearGradient id="aurum-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffe088" />
          <stop offset="55%" stopColor="#d4af37" />
          <stop offset="100%" stopColor="#a37c1b" />
        </linearGradient>
      </defs>
      <path
        d="M50 4 91 27v46L50 96 9 73V27z"
        fill="none"
        stroke="url(#aurum-g)"
        strokeWidth="6"
        strokeLinejoin="round"
      />
      <path
        d="M31 68 50 30l19 38"
        fill="none"
        stroke="url(#aurum-g)"
        strokeWidth="8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M39 56h22" stroke="url(#aurum-g)" strokeWidth="8" strokeLinecap="round" />
    </svg>
  );
}
