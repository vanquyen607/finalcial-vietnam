import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { fmtAgo, fmtClock } from "../lib/format";
import { ageSeconds } from "../lib/useNow";
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
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const live = connected && status.state === "live";
  const label = !connected ? "NGẮT KẾT NỐI" : status.state === "error" ? "LỖI NGUỒN" : "LIVE";
  const source = status.source === "mock" ? "MOCK" : (status.source || "").toUpperCase();
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
            {quoteList.length} LOẠI · {source || "…"}
          </span>
          <span className="meta hide-sm">
            LẤY DỮ LIỆU {age !== null ? fmtAgo(age).toUpperCase() : "…"}
          </span>
          <span className="row" style={{ gap: 6 }}>
            <i className={`dot ${live ? "dot--live" : status.state === "error" ? "dot--err" : ""}`} />
            <span className="meta">{label}</span>
          </span>
          <span className="meta mono topbar__clock">{fmtClock(Math.floor(now / 1000))}</span>
        </div>
      </div>

      <Ticker />
    </header>
  );
}
