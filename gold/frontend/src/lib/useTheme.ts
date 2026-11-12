import { useEffect, useState } from "react";

export type Theme = "dark" | "light";

export function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const stored = localStorage.getItem("ck_theme") || localStorage.getItem("aurum_theme");
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

// Theme dùng chung toàn app: mọi component gọi useTheme() đều thấy cùng giá trị.
// Trước đây mỗi hook giữ state riêng nên bấm toggle ở Header không cập nhật biểu đồ
// (grid/crosshair vẫn màu theme cũ tới khi reload).
let current: Theme = getInitialTheme();
const listeners = new Set<(t: Theme) => void>();

function applyTheme(next: Theme) {
  current = next;
  document.documentElement.setAttribute("data-theme", next);
  try {
    localStorage.setItem("ck_theme", next);
    localStorage.setItem("aurum_theme", next);
  } catch {}
  listeners.forEach((l) => l(next));
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(current);

  useEffect(() => {
    if (document.documentElement.getAttribute("data-theme") !== current) {
      applyTheme(current);
    }
    const listener = (t: Theme) => setThemeState(t);
    listeners.add(listener);

    const onStorage = (e: StorageEvent) => {
      if (
        (e.key === "ck_theme" || e.key === "aurum_theme") &&
        (e.newValue === "light" || e.newValue === "dark")
      ) {
        applyTheme(e.newValue);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => {
      listeners.delete(listener);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const setTheme = (t: Theme) => applyTheme(t);
  const toggleTheme = () => applyTheme(current === "dark" ? "light" : "dark");

  return { theme, setTheme, toggleTheme };
}
