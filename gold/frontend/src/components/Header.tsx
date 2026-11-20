import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { fmtAgo, fmtClock } from "../lib/format";
import { ageSeconds } from "../lib/useNow";
import { useTheme } from "../lib/useTheme";
import Logo from "./Logo";
import Ticker from "./Ticker";
import { useMarket } from "../state/Market";

function TabIcon({ id }: { id: "home" | "chart" | "news" | "alerts" | "settings" }) {
  switch (id) {
    case "home":
      return (
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <path d="M3 10h18M9 4v16" />
        </svg>
      );
    case "chart":
      return (
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M3 3v18h18" />
          <path d="m7 15 4-4 4 3 5-6" />
        </svg>
      );
    case "news":
      return (
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M4 5h13a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5Z" />
          <path d="M8 9h7M8 13h7M8 17h4" />
        </svg>
      );
    case "alerts":
      return (
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
      );
    case "settings":
      return (
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
        </svg>
      );
  }
}

const DESKTOP_LINKS: { to: string; label: string; end: boolean }[] = [
  { to: "/", label: "Bảng giá", end: true },
  { to: "/silver", label: "Bạc", end: false },
  { to: "/fuel", label: "Xăng dầu", end: false },
  { to: "/fx", label: "Ngoại tệ", end: false },
  { to: "/market", label: "Thị trường", end: false },
  { to: "/chart", label: "Biểu đồ", end: false },
  { to: "/news", label: "Tin tức", end: false },
  { to: "/alerts", label: "Cảnh báo", end: false },
  { to: "/settings", label: "Cài đặt", end: false },
];

const MOBILE_LINKS: { to: string; label: string; end: boolean; icon: "home" | "chart" | "news" | "alerts" | "settings" }[] = [
  { to: "/", label: "Bảng giá", end: true, icon: "home" },
  { to: "/chart", label: "Biểu đồ", end: false, icon: "chart" },
  { to: "/news", label: "Tin tức", end: false, icon: "news" },
  { to: "/alerts", label: "Cảnh báo", end: false, icon: "alerts" },
  { to: "/settings", label: "Cài đặt", end: false, icon: "settings" },
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
    <>
      <header className="topbar">
        <div className="topbar__inner">
          <NavLink to="/" className="brand">
            <Logo size={30} />
            <span>
              <span className="brand__name">Aurum Terminal</span>
              <span className="brand__tag">Giá vàng & thị trường realtime</span>
            </span>
          </NavLink>

          <div className="topbar__status">
            <span className="meta hide-sm">
              {quoteList.length} loại · {source || "…"}
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
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
                </svg>
              )}
            </button>
            <span className="meta mono topbar__clock hide-sm">{fmtClock(Math.floor(now / 1000))}</span>
          </div>
        </div>

        <nav className="navbar" aria-label="Điều hướng chính">
          <div className="navbar__inner">
            {DESKTOP_LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end} className="navbar__link">
                {l.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>

      <Ticker />

      <nav className="mobile-tabbar" aria-label="Điều hướng di động">
        {MOBILE_LINKS.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => `mobile-tabbar__item ${isActive ? "active" : ""}`}
          >
            <TabIcon id={l.icon} />
            <span>{l.label}</span>
          </NavLink>
        ))}
      </nav>
    </>
  );
}
