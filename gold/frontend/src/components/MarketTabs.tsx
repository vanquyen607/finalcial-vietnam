import { NavLink } from "react-router-dom";

const TABS = [
  { to: "/", label: "Giá vàng", end: true },
  { to: "/silver", label: "Bạc", end: false },
  { to: "/fuel", label: "Xăng dầu", end: false },
  { to: "/fx", label: "Ngoại tệ", end: false },
];

export default function MarketTabs() {
  return (
    <nav className="market-tabs" aria-label="Chuyển thị trường">
      {TABS.map((t) => (
        <NavLink
          key={t.to}
          to={t.to}
          end={t.end}
          className={({ isActive }) => `market-tabs__item ${isActive ? "active" : ""}`}
        >
          {t.label}
        </NavLink>
      ))}
    </nav>
  );
}
