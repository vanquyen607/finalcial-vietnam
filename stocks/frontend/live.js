/* Phan Tich Co Phieu VN — live.js (tach tu app.js) */
/* ---------------- live mode ---------------- */
const LIVE_MS = 60000;
let liveOn = true;
try { liveOn = localStorage.getItem("ck_live") !== "0"; } catch (e) {}
let nextLive = Date.now() + LIVE_MS;
let inSession = true;

function setLiveBtn() {
  $("#btnLive").classList.toggle("off", !liveOn || !inSession);
}

async function loadSession() {
  try {
    const s = await api("/api/session");
    inSession = !!s.in_session;
  } catch (e) {}
  setLiveBtn();
}

function liveTick() {
  const el = $("#liveCount");
  if (!liveOn) { el.textContent = "tắt — bấm để bật"; return; }
  if (document.hidden) { el.innerHTML = `<span class="warn">tạm dừng (tab ẩn)</span>`; return; }
  if (!inSession) { el.innerHTML = `<span class="warn">ngoài giờ giao dịch</span>`; return; }
  const left = Math.max(0, Math.ceil((nextLive - Date.now()) / 1000));
  el.textContent = `cập nhật sau ${left}s`;
  if (left <= 0) { nextLive = Date.now() + LIVE_MS; doLive(); }
}

function doLive() {
  loadOverview(true, true);
  loadBreadth();
  if (selectedSym && !detailBusy && !compareMode) openSymbol(selectedSym, true);
}

/* ---------------- events ---------------- */
$("#btnRunScreen").addEventListener("click", runScreen);
$("#btnRefreshOverview").addEventListener("click", () => {
  loadOverview(true);
  toast("Đang làm mới chỉ số…");
});
$("#btnAnalyze").addEventListener("click", () => openSymbol($("#symInput").value));
$("#btnTheme").addEventListener("click", toggleTheme);

/* news: mở rộng / thu gọn (delegation — #detail chỉ bị thay innerHTML nên listener không mất) */
$("#detail").addEventListener("click", (e) => {
  if (e.target.closest(".news-more")) {
    newsExpanded = !newsExpanded;
    syncNewsState();
    const box = document.getElementById("news");
    if (box) lastNewsHTML = box.innerHTML;
    return;
  }
  /* ⭐ thêm/bỏ theo dõi */
  const star = e.target.closest("[data-star]");
  if (star && lastDetail) {
    toggleWatch(lastDetail.symbol);
    const on = inWatch(lastDetail.symbol);
    star.classList.toggle("on", on);
    star.textContent = on ? "★" : "☆";
    star.setAttribute("aria-pressed", String(on));
    star.title = `Thêm/bỏ ${lastDetail.symbol} vào ⭐ Của tôi`;
    renderScreen(screenRows);
    return;
  }
  /* thoát so sánh */
  if (e.target.closest("#btnCmpClose")) exitCompare();
});

/* ---------------- nút So sánh ---------------- */
$("#btnCompare").addEventListener("click", () => {
  if (compareMode) { exitCompare(); return; }
  if (!lastDetail) { toast("Hãy phân tích một mã trước khi so sánh", "warn"); return; }
  compareMode = true;
  syncCompareUI();
  $("#symInput").value = "";
  hideSuggest();
  $("#symInput").focus();
  toast(`Nhập mã thứ 2 để so sánh với ${lastDetail.symbol}`, "ok");
});

/* ---------------- export CSV ---------------- */
function exportCsv() {
  const rows = visibleRows();
  if (!rows.length) { toast("Không có dòng nào để xuất", "warn"); return; }
  const head = ["#", "Ma", "Gia", "20 phien %", "RSI", "KL/TB20", "Diem", "Tin hieu"];
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = [head.map(esc).join(",")];
  rows.forEach((r, i) => {
    lines.push([i + 1, r.symbol, r.close, r.r20, r.rsi, r.vol_ratio, r.score, r.verdict].map(esc).join(","));
  });
  const d = new Date();
  const p2 = (n) => String(n).padStart(2, "0");
  const name = `man_loc_${p2(d.getDate())}${p2(d.getMonth() + 1)}${d.getFullYear()}.csv`;
  const blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
  toast(`Đã xuất ${rows.length} dòng → ${name}`, "ok");
}
$("#btnCsv").addEventListener("click", exportCsv);

/* phím Back/Forward của trình duyệt + link #MÃ chia sẻ được */
window.addEventListener("hashchange", () => {
  if (compareMode) return;   /* đang so sánh → bỏ qua, chờ người dùng thoát */
  const h = location.hash.slice(1).toUpperCase();
  if (h && h !== selectedSym && /^[A-Z]{2,6}$/.test(h)) openSymbol(h);
});

$("#noticeClose").addEventListener("click", () => {
  $("#notice").classList.add("hidden");
  try { localStorage.setItem("ck_notice", "off"); } catch (e) {}
});

$("#btnLive").addEventListener("click", async () => {
  liveOn = !liveOn;
  try { localStorage.setItem("ck_live", liveOn ? "1" : "0"); } catch (e) {}
  setLiveBtn();
  try {
    if (liveOn) {
      await apiAdmin("/api/screen/run?auto=1", { method: "POST" });
      nextLive = Date.now() + 5000;
      doLive();
      toast("Live bật — tự làm mới 60s trong phiên", "ok");
    } else {
      await apiAdmin("/api/screen/stop", { method: "POST" });
      toast("Đã tắt Live — dữ liệu dùng cache", "warn");
    }
  } catch (e) { toast("Không kết nối được server", "err"); }
  loadScreen();
});

/* sort/filter chips */
/* sort — 1 nguồn sự thật: chips ở toolbar và cột bảng cùng gọi setSort() */
function syncSortUI() {
  document.querySelectorAll("#sortChips .chip-btn").forEach((c) => {
    const on = c.dataset.sort === sortBy;
    c.classList.toggle("on", on);
    c.querySelector(".arr").textContent = on ? (sortDir === -1 ? "▼" : "▲") : "▼";
  });
  document.querySelectorAll(".tbl thead th.sortable").forEach((th) => {
    const on = th.dataset.sort === sortBy;
    th.querySelector(".arr").textContent = on ? (sortDir === -1 ? "▼" : "▲") : "";
    th.setAttribute("aria-sort", on ? (sortDir === -1 ? "descending" : "ascending") : "none");
  });
}
function setSort(key) {
  if (key === sortBy) sortDir = -sortDir;
  else { sortBy = key; sortDir = -1; }
  saveSortState();
  syncSortUI();
  renderScreen(screenRows);
}

$("#sortChips").addEventListener("click", (e) => {
  const b = e.target.closest(".chip-btn");
  if (b) setSort(b.dataset.sort);
});

document.querySelectorAll(".tbl thead th.sortable").forEach((th) => {
  th.addEventListener("click", () => setSort(th.dataset.sort));
});

$("#filterChips").addEventListener("click", (e) => {
  const b = e.target.closest(".chip-btn");
  if (!b) return;
  filterBy = b.dataset.filter;
  saveFilterState();
  syncFilterUI();
  renderScreen(screenRows);
});

function syncFilterUI() {
  document.querySelectorAll("#filterChips .chip-btn").forEach((c) => {
    c.classList.toggle("on", c.dataset.filter === filterBy);
    c.classList.toggle("good", c.dataset.filter === "good" && c.classList.contains("on"));
    c.classList.toggle("bad", c.dataset.filter === "bad" && c.classList.contains("on"));
  });
}

/* search input */
const input = $("#symInput");
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { openSymbol(input.value); }
  if (e.key === "Escape") {
    if (compareMode) exitCompare();
    else { hideSuggest(); input.blur(); }
  }
});
input.addEventListener("input", (e) => {
  e.target.value = e.target.value.toUpperCase().replace(/[^A-Z]/g, "");
  renderSuggest(e.target.value);
});
input.addEventListener("blur", () => setTimeout(hideSuggest, 150));

/* global hotkeys */
document.addEventListener("keydown", (e) => {
  const typing = ["INPUT", "TEXTAREA"].includes(document.activeElement.tagName);
  if (e.key === "/" && !typing) { e.preventDefault(); input.focus(); input.select(); }
  if ((e.key === "t" || e.key === "T") && !typing && !e.ctrlKey && !e.metaKey) toggleTheme();
  /* ↑/↓ di chuyển chọn mã theo đúng thứ tự bảng đang hiển thị */
  if ((e.key === "ArrowDown" || e.key === "ArrowUp") && !typing && !compareMode) {
    const rows = visibleRows();
    if (!rows.length) return;
    e.preventDefault();
    const step = e.key === "ArrowDown" ? 1 : -1;
    let i = rows.findIndex((r) => r.symbol === selectedSym);
    i = (i === -1 ? (step === 1 ? 0 : rows.length - 1) : i + step);
    i = Math.max(0, Math.min(rows.length - 1, i));
    const next = rows[i];
    if (next.symbol !== selectedSym) openSymbol(next.symbol);
    setTimeout(() => {
      const tr = document.querySelector(`#screenBody tr[data-sym="${next.symbol}"]`);
      if (tr) { tr.focus(); tr.scrollIntoView({ block: "nearest" }); }
    }, 80);
  }
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && liveOn) nextLive = Date.now() + 3000;
});

/* ---------------- init ---------------- */
applyTheme(document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark");
setLiveBtn();
syncSortUI();
syncFilterUI();
syncCompareUI();

async function loadBasket() {
  try {
    const s = await api("/api/symbols");
    BASKET = s.basket || [];
  } catch (e) {}
}

if (location.hash && /^[#A-Za-z]{2,7}$/.test(location.hash)) openSymbol(location.hash.slice(1));

loadBasket();
loadSession();
setInterval(loadSession, 60000);
setInterval(liveTick, 1000);
loadOverview();
loadBreadth();
loadScreen();

if (liveOn) {
  api("/api/screen/run?auto=1", { method: "POST" }).then(() => loadScreen()).catch(() => {});
}
