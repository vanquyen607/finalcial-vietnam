/* Phan Tich Co Phieu VN — core.js (tach tu app.js) */
/* Phân Tích Cổ Phiếu VN — frontend */
const $ = (s) => document.querySelector(s);
const fmt = (n, d = 2) => (n == null || isNaN(n) ? "—" : Number(n).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d }));
const cls = (n) => (n > 0 ? "up" : n < 0 ? "down" : "flat");
const sign = (n, d = 2) => (n > 0 ? "+" : "") + fmt(n, d);
/* "2026-10-08" → "08/10/2026" */
const fmtDate = (s) => {
  const m = String(s || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : (s || "—");
};
/* escape dữ liệu từ server/API trước khi chèn innerHTML — chống XSS */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
/* chỉ cho phép http(s) — chặn javascript:/data: trong href */
const safeUrl = (u) => (/^https?:\/\//i.test(String(u || "")) ? String(u) : "#");

let selectedSym = null;
let chart = null;
let lastDetail = null;
let lastPrice = null;
let screenRows = [];
let detailBusy = false;
let lastNewsHTML = "";
let newsExpanded = false;
let pollTimers = { overview: null, screen: null, session: null };

/* sort / filter */
let sortBy = "score";
let sortDir = -1;
let filterBy = "all";
let BASKET = [];
try {
  const s = JSON.parse(localStorage.getItem("ck_sort") || "null");
  if (s && s.key) { sortBy = s.key; sortDir = s.dir === 1 ? 1 : -1; }
  const f = localStorage.getItem("ck_filter");
  if (f) filterBy = f;
} catch (e) {}
function saveSortState() {
  try { localStorage.setItem("ck_sort", JSON.stringify({ key: sortBy, dir: sortDir })); } catch (e) {}
}
function saveFilterState() {
  try { localStorage.setItem("ck_filter", filterBy); } catch (e) {}
}

/* watchlist ⭐ — "Của tôi" */
let watchList = [];
try {
  watchList = JSON.parse(localStorage.getItem("ck_watch") || "[]")
    .filter((s) => typeof s === "string" && /^[A-Z]{2,6}$/.test(s));
} catch (e) {}
const inWatch = (sym) => watchList.includes(sym);
function toggleWatch(sym) {
  if (inWatch(sym)) {
    watchList = watchList.filter((s) => s !== sym);
    toast(`Đã bỏ ${sym} khỏi ⭐ Của tôi`);
  } else {
    watchList.push(sym);
    toast(`Đã thêm ${sym} vào ⭐ Của tôi`, "ok");
  }
  try { localStorage.setItem("ck_watch", JSON.stringify(watchList)); } catch (e) {}
}

/* so sánh 2 mã */
let compareMode = false;
let compareSym = null;
let lastStale = false;

/* báo giá — mỗi cảnh báo 1 lần / phiên */
const firedAlerts = new Set();

/* ---------------- clock ---------------- */
function tickClock() {
  const d = new Date();
  $("#clock").textContent = d.toLocaleString("vi-VN", { hour12: false });
}
setInterval(tickClock, 1000);
tickClock();

const HTTP_MSG = {
  429: "Quá nhiều yêu cầu — đợi ít phút rồi thử lại",
  500: "Máy chủ đang bận — thử lại sau",
  503: "Máy chủ đang khởi động — thử lại sau",
};
/* token quản trị (tùy chọn) — chỉ cần khi server đặt ADMIN_TOKEN */
let adminToken = "";
try { adminToken = localStorage.getItem("ck_admin") || ""; } catch (e) {}
function setAdminToken(t) {
  adminToken = (t || "").trim();
  try {
    if (adminToken) localStorage.setItem("ck_admin", adminToken);
    else localStorage.removeItem("ck_admin");
  } catch (e) {}
}
function askAdminToken() {
  const t = prompt("Nhập token quản trị (ADMIN_TOKEN) để thực hiện thao tác này:");
  if (t == null) return false;
  setAdminToken(t);
  return !!adminToken;
}
async function api(path, opts) {
  opts = opts || {};
  const headers = Object.assign({}, opts.headers || {});
  if (adminToken) headers["X-Admin-Token"] = adminToken;
  opts.headers = headers;
  let r;
  try { r = await fetch(path, opts); }
  catch (e) { throw new Error("Mất kết nối máy chủ"); }
  if (r.status === 401) { const e = new Error("Cần token quản trị"); e.code = 401; throw e; }
  if (!r.ok) throw new Error(HTTP_MSG[r.status] || `Lỗi máy chủ (HTTP ${r.status})`);
  return r.json();
}
/* thao tác cần quyền: nếu 401 thì hỏi token rồi thử lại 1 lần */
async function apiAdmin(path, opts) {
  try { return await api(path, opts); }
  catch (e) {
    if (e.code === 401 && askAdminToken()) return await api(path, opts);
    throw e;
  }
}

/* ---------------- toast ---------------- */
function toast(msg, kind = "") {
  const t = document.createElement("div");
  t.className = "toast " + kind;
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), 350); }, 3400);
}

/* ---------------- theme ---------------- */
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem("ck_theme", t); } catch (e) {}
  const b = $("#btnTheme");
  b.title = t === "dark" ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối";
  if (lastDetail && lastDetail.ohlcv) drawChart(lastDetail.ohlcv);
}
function toggleTheme() {
  const cur = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  applyTheme(cur === "light" ? "dark" : "light");
}
function cssVar(name, fallback) {
  return (getComputedStyle(document.documentElement).getPropertyValue(name) || "").trim() || fallback;
}

/* ---------------- notice ---------------- */
try {
  if (localStorage.getItem("ck_notice") === "off") $("#notice").classList.add("hidden");
} catch (e) {}

/* ---------------- sidebar ---------------- */
(function initSidebar() {
  const side = $("#sidebar");
  const backdrop = $("#sbBackdrop");
  const btn = $("#btnSidebar");
  const collapse = $("#btnCollapseSide");
  if (!side) return;

  // collapse state
  try {
    if (localStorage.getItem("ck_sidebar") === "collapsed") side.classList.add("collapsed");
  } catch (e) {}
  if (collapse) {
    collapse.textContent = side.classList.contains("collapsed") ? "›" : "‹";
    collapse.addEventListener("click", () => {
      side.classList.toggle("collapsed");
      collapse.textContent = side.classList.contains("collapsed") ? "›" : "‹";
      try { localStorage.setItem("ck_sidebar", side.classList.contains("collapsed") ? "collapsed" : "open"); } catch (e) {}
    });
  }

  // mobile drawer
  function openDrawer() {
    side.classList.add("open");
    if (backdrop) backdrop.classList.add("show");
    if (btn) btn.setAttribute("aria-expanded", "true");
  }
  function closeDrawer() {
    side.classList.remove("open");
    if (backdrop) backdrop.classList.remove("show");
    if (btn) btn.setAttribute("aria-expanded", "false");
  }
  if (btn) btn.addEventListener("click", () => side.classList.contains("open") ? closeDrawer() : openDrawer());
  if (backdrop) backdrop.addEventListener("click", closeDrawer);

  // action buttons
  side.querySelectorAll("[data-action]").forEach((el) => {
    el.addEventListener("click", () => {
      const a = el.getAttribute("data-action");
      if (a === "portfolio") $("#btnPortfolio") && $("#btnPortfolio").click();
      else if (a === "alerts") $("#btnAlerts") && $("#btnAlerts").click();
      else if (a === "brief") $("#btnBrief") && $("#btnBrief").click();
      else if (a === "ai") $("#aiFab") && $("#aiFab").click();
      else if (a === "runscreen") $("#btnRunScreen") && $("#btnRunScreen").click();
      closeDrawer();
    });
  });

  // scroll anchors
  side.querySelectorAll("[data-scroll]").forEach((el) => {
    el.addEventListener("click", (e) => {
      const href = el.getAttribute("href");
      if (href && href.startsWith("#")) {
        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: "smooth", block: "start" });
          closeDrawer();
        }
      }
    });
  });

  // active highlight on scroll
  const items = Array.from(side.querySelectorAll("[data-scroll]"));
  const targets = items.map((it) => {
    const t = document.querySelector(it.getAttribute("href"));
    return t ? { item: it, el: t } : null;
  }).filter(Boolean);
  if (targets.length && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        const t = targets.find((x) => x.el === en.target);
        if (t) {
          if (en.isIntersecting) {
            items.forEach((i) => i.classList.remove("active"));
            t.item.classList.add("active");
          }
        }
      });
    }, { rootMargin: "-30% 0px -60% 0px", threshold: 0 });
    targets.forEach((t) => io.observe(t.el));
  }

  // gold link url
  const sg = $("#sideGold");
  if (sg) {
    const h = location.hostname;
    sg.href = (h === "localhost" || h === "127.0.0.1") ? "http://127.0.0.1:8000/" : "https://finalcial-vietnam-1.onrender.com/";
  }
})();

/* ---------------- chuyển app: Cổ phiếu ↔ Vàng ---------------- */
function goldUrl() {
  const h = location.hostname;
  if (h === "localhost" || h === "127.0.0.1") return "http://127.0.0.1:8000/";
  return "https://finalcial-vietnam-1.onrender.com/";
}
try {
  const g = $("#navGold");
  if (g) g.href = goldUrl();
} catch (e) {}

