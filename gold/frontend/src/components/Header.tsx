import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { fmtAgo, fmtClock } from "../lib/format";
import { ageSeconds } from "../lib/useNow";
import { useTheme } from "../lib/useTheme";
import Logo from "./Logo";
import Ticker from "./Ticker";
import { useMarket } from "../state/Market";

const LINKS = [
  { to: "/", label: "Bảng giá", end: true },
  { to: "/chart", label: "Biểu đồ", end: false },
  { to: "/news", label: "Tin tức", end: false },
  { to: "/alerts", label: "Cảnh báo", end: false },
  { to: "/settings", label: "Cài đặt", end: false },
];

export default function Header() {
  const { status, connected, quoteList } = useMarket();
  const { theme, toggleTheme } = useTheme();
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const live = connected && status.state === "live";
  const label = !connected ? "Mất kết nối" : status.state === "error" ? "Lỗi nguồn" : "Live";
  const source = status.source === "mock" ? "Mock" : status.source || "";
  const age = ageSeconds(status.last_success, now);

  return (
    <header className="topbar">
      <div className="topbar__inner">
        <NavLink to="/" className="brand">
          <Logo size={30} />
          <span>
            <span className="brand__name">Aurum Terminal</span>
            <span className="brand__tag">Giá vàng realtime</span>
          </span>
        </NavLink>

        <nav className="nav">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}>
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="topbar__status">
          <span className="meta hide-sm">
            {quoteList.length} loại, {source || "…"}
          </span>
          <span className="meta hide-sm hide-md">
            Cập nhật {age !== null ? fmtAgo(age) : "…"}
          </span>
          <span className="row" style={{ gap: 6 }}>
            <i className={`dot ${live ? "dot--live" : status.state === "error" ? "dot--err" : ""}`} />
            <span className="meta">{label}</span>
          </span>
          <button
            type="button"
            className="btn-theme-toggle"
            onClick={toggleTheme}
            title={theme === "dark" ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}
            aria-label="Đổi giao diện"
          >
            {theme === "dark" ? (
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
              </svg>
            )}
          </button>
          <span className="meta mono topbar__clock hide-sm">{fmtClock(Math.floor(now / 1000))}</span>
        </div>
      </div>

      <Ticker />
    </header>
  );
}
