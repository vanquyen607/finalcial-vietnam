/* Phân Tích Cổ Phiếu VN — frontend */
const $ = (s) => document.querySelector(s);
const fmt = (n, d = 2) => (n == null || isNaN(n) ? "—" : Number(n).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d }));
const cls = (n) => (n > 0 ? "up" : n < 0 ? "down" : "flat");
const sign = (n, d = 2) => (n > 0 ? "+" : "") + fmt(n, d);

let selectedSym = null;
let chart = null;
let lastDetail = null;
let lastPrice = null;
let screenRows = [];
let detailBusy = false;
let lastNewsHTML = "";
let pollTimers = { overview: null, screen: null, session: null };

/* sort / filter */
let sortBy = "score";
let sortDir = -1;
let filterBy = "all";
let BASKET = [];

/* ---------------- clock ---------------- */
function tickClock() {
  const d = new Date();
  $("#clock").textContent = d.toLocaleString("vi-VN", { hour12: false });
}
setInterval(tickClock, 1000);
tickClock();

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
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
  b.textContent = t === "dark" ? "☀️" : "🌙";
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

/* ---------------- overview ---------------- */
async function loadOverview(refresh = false, silent = false) {
  try {
    const st = await api("/api/overview" + (refresh ? "?refresh=1" : ""));
    if (st.status === "fetching") {
      if (!silent) $("#cards").innerHTML = `<div class="card"><div class="loading-line"><span class="spinner"></span> Đang tải chỉ số…</div></div>`;
      clearTimeout(pollTimers.overview);
      pollTimers.overview = setTimeout(() => loadOverview(false, silent), 4000);
      return;
    }
    if (st.status !== "ready") {
      if (!silent) $("#cards").innerHTML = `<div class="card"><div class="err">Không tải được chỉ số: ${st.message || "?"}</div></div>`;
      else toast("Làm mới chỉ số thất bại", "err");
      return;
    }
    renderCards(st);
    clearTimeout(pollTimers.overview);
  } catch (e) {
    if (!silent) $("#cards").innerHTML = `<div class="card"><div class="err">Lỗi: ${e.message}</div></div>`;
  }
}

function renderCards(st) {
  const box = $("#cards");
  box.innerHTML = "";
  (st.indices || []).forEach((ix) => {
    const el = document.createElement("div");
    el.className = "card";
    el.innerHTML = `
      <div class="label">${ix.label} · phiên ${ix.date}</div>
      <div class="big ${cls(ix.chg_pct)}">${fmt(ix.close, 2)}</div>
      <div class="chg ${cls(ix.chg_pct)}">${sign(ix.chg, 2)} điểm (${sign(ix.chg_pct, 2)}%)</div>
      <div class="row">
        <span class="chip">MA20 <b>${fmt(ix.ma20, 0)}</b></span>
        <span class="chip">MA50 <b>${fmt(ix.ma50, 0)}</b></span>
        <span class="chip">MA200 <b>${fmt(ix.ma200, 0)}</b></span>
        <span class="chip">20 phiên <b class="${cls(ix.r20)}">${sign(ix.r20, 1)}%</b></span>
        <span class="chip">Vùng 30 phiên <b>${fmt(ix.lo30, 0)} – ${fmt(ix.hi30, 0)}</b></span>
        <span class="chip">KL <b>${fmt(ix.vol_last_m, 0)}tr</b>/TB20 ${fmt(ix.vol20_m, 0)}tr</span>
      </div>
      <div class="trend">Xu hướng: <b>${ix.trend}</b> ${ix.above_ma200 ? "" : "· ⚠️ dưới MA200"}</div>`;
    box.appendChild(el);
  });
  const meta = document.createElement("div");
  meta.className = "card";
  meta.innerHTML = `<div class="label">Nguồn & cập nhật</div>
    <div class="trend" style="margin-top:7px">Cập nhật: <b>${st.updated_at || "—"}</b></div>
    <div class="trend">${st.stale ? "⚠️ Dữ liệu cũ hơn 30 phút — bấm ⟳ Chỉ số" : "Tự làm mới theo Live (60s trong phiên)"}</div>
    <div class="trend">vnstock/VCI · cache 30 phút</div>`;
  box.appendChild(meta);
}

/* ---------------- screen ---------------- */
async function loadScreen() {
  try {
    const st = await api("/api/screen");
    const auto = st.auto ? `auto · vòng #${st.cycles}` : "chạy 1 lần";
    if (st.status === "running" || st.running) {
      const pct = st.total ? Math.round((st.done / st.total) * 100) : 0;
      $("#screenBar").style.width = pct + "%";
      $("#screenMeta").textContent = `${st.done}/${st.total} · hiện tại: ${st.current || "…"} · ${auto}`;
      renderScreen(st.results || []);
      clearTimeout(pollTimers.screen);
      pollTimers.screen = setTimeout(loadScreen, 3000);
      return;
    }
    $("#screenBar").style.width = "100%";
    if (st.results && st.results.length) {
      const t = st.generated_at ? new Date(st.generated_at * 1000) : null;
      const src = st.source === "seed" ? " · mẫu, bấm Chạy màn lọc" : "";
      const nxt = st.auto && st.next_in ? ` · quét lại sau ${st.next_in}s` : "";
      $("#screenMeta").textContent = `${st.results.length} mã · ${t ? "lúc " + t.toLocaleTimeString("vi-VN") : ""} · ${auto}${nxt}${src}`;
      renderScreen(st.results);
    } else {
      $("#screenMeta").textContent = "chưa có dữ liệu — bấm Chạy màn lọc";
      $("#screenBody").innerHTML = `<tr><td colspan="8" class="empty">Chưa có dữ liệu. Bấm <b>Chạy màn lọc 40 mã</b> (lần đầu ~6 phút).</td></tr>`;
    }
    clearTimeout(pollTimers.screen);
    pollTimers.screen = setTimeout(loadScreen, 8000);
  } catch (e) {
    $("#screenMeta").textContent = "lỗi: " + e.message;
    clearTimeout(pollTimers.screen);
    pollTimers.screen = setTimeout(loadScreen, 15000);
  }
}

function renderTicker() {
  const el = $("#tickerTrack");
  if (!el || !screenRows.length) return;
  const withR5 = screenRows.filter((r) => typeof r.r5 === "number");
  if (!withR5.length) return;
  const gain = withR5.slice().sort((a, b) => b.r5 - a.r5).slice(0, 8);
  const lose = withR5.slice().sort((a, b) => a.r5 - b.r5).slice(0, 8);
  const items = [...gain, ...lose];
  const html = items.map((r) => `
    <span class="tk" title="${r.symbol}: đổi ${sign(r.r5, 1)}% trong 5 phiên">
      <b>${r.symbol}</b><span class="tk-p">${fmt(r.close, r.close < 50 ? 1 : 0)}</span>
      <span class="tk-c ${r.r5 >= 0 ? "up" : "down"}">${sign(r.r5, 1)}%</span>
    </span>`).join("");
  el.innerHTML = html + html;
}

function renderScreen(rows) {
  screenRows = rows || [];
  renderTicker();
  const filtered = screenRows.filter((r) => filterBy === "all" || r.tone === filterBy);
  const rows2 = filtered.slice().sort((a, b) => {
    const x = a[sortBy] ?? -Infinity, y = b[sortBy] ?? -Infinity;
    return (x < y ? -1 : x > y ? 1 : 0) * sortDir;
  });

  const body = $("#screenBody");
  $("#rowCount").textContent = rows2.length !== screenRows.length
    ? `${rows2.length}/${screenRows.length} mã`
    : (screenRows.length ? screenRows.length + " mã" : "");

  if (!rows2.length) {
    body.innerHTML = `<tr><td colspan="8" class="empty">${screenRows.length ? "Không có mã nào khớp bộ lọc." : "Chưa có dữ liệu."}</td></tr>`;
    return;
  }
  body.innerHTML = rows2
    .map((r, i) => {
      const tone = r.tone || "neutral";
      return `<tr data-sym="${r.symbol}" tabindex="0" class="${r.symbol === selectedSym ? "sel" : ""}">
        <td class="rank">${i + 1}</td>
        <td><span class="sym">${r.symbol}</span></td>
        <td>${fmt(r.close, r.close < 50 ? 1 : 0)}</td>
        <td class="${cls(r.r20)}">${sign(r.r20, 1)}%</td>
        <td class="${r.rsi > 70 ? "down" : r.rsi < 30 ? "up" : ""}">${fmt(r.rsi, 0)}</td>
        <td>${fmt(r.vol_ratio, 2)}×</td>
        <td><span class="score ${tone}">${r.score}</span></td>
        <td><span class="tag ${tone}">${r.verdict}</span></td>
      </tr>`;
    })
    .join("");
  body.querySelectorAll("tr[data-sym]").forEach((tr) => {
    tr.addEventListener("click", () => openSymbol(tr.dataset.sym));
    tr.addEventListener("keydown", (e) => { if (e.key === "Enter") openSymbol(tr.dataset.sym); });
  });
}

async function runScreen() {
  const btn = $("#btnRunScreen");
  btn.disabled = true;
  try {
    await api("/api/screen/run", { method: "POST" });
    toast("Đã bắt đầu quét 40 mã — lần đầu ~6 phút", "ok");
    clearTimeout(pollTimers.screen);
    loadScreen();
  } catch (e) {
    toast("Không khởi động được màn lọc: " + e.message, "err");
  } finally {
    setTimeout(() => { btn.disabled = false; }, 1500);
  }
}

/* ---------------- detail ---------------- */
async function openSymbol(sym, refresh = false) {
  sym = (sym || "").toUpperCase().trim();
  if (!/^[A-Z]{2,6}$/.test(sym)) {
    $("#detail").innerHTML = `<div class="err">Mã không hợp lệ (2–6 chữ cái, VD: HPG)</div>`;
    return;
  }
  selectedSym = sym;
  detailBusy = true;
  document.querySelectorAll("#screenBody tr").forEach((tr) => {
    tr.classList.toggle("sel", tr.dataset.sym === sym);
  });
  $("#symInput").value = sym;
  hideSuggest();
  if (!refresh) {
    lastNewsHTML = "";
    lastPrice = null;
    $("#detail").innerHTML = `<div class="loading-line"><span class="spinner"></span> Đang phân tích <b>${sym}</b> — chờ lượt gọi dữ liệu (~10–20 giây)…</div>`;
  }
  try {
    const st = await api(`/api/symbol/${sym}` + (refresh ? "?refresh=1" : ""));
    detailBusy = false;
    if (st.status !== "ready") {
      if (!refresh) $("#detail").innerHTML = `<div class="err">${st.message || "Không có dữ liệu"}</div>`;
      else toast(st.message || "Không tải được " + sym, "err");
      return;
    }
    renderDetail(st.data, st.stale);
    if (!refresh) loadNews(sym);
  } catch (e) {
    detailBusy = false;
    if (!refresh) $("#detail").innerHTML = `<div class="err">Lỗi: ${e.message}</div>`;
  }
}

function renderDetail(d, stale) {
  const tone = d.tone || "neutral";
  lastDetail = d;
  const priceFlash = lastPrice != null && lastPrice !== d.close
    ? (d.close > lastPrice ? " flash-up" : " flash-down")
    : "";
  const prevPrice = lastPrice;
  lastPrice = d.close;

  $("#detail").innerHTML = `
    <div class="detail">
      <div class="d-head">
        <span class="name">${d.symbol}</span>
        <span class="price${priceFlash}">${fmt(d.close, d.close < 50 ? 1 : 0)}</span>
        <span class="dchg ${cls(d.r5)}">5 phiên: ${sign(d.r5, 1)}%</span>
        <span class="date">phiên ${d.date}${stale ? " · cache cũ" : ""}</span>
      </div>
      <div class="verdict-line">
        <span class="big-tag ${tone}">${d.verdict}</span>
        <span class="score ${tone}" style="font-size:13.5px">Điểm ${d.score}/${d.max_score}</span>
        <span class="trend">${d.trend}</span>
      </div>

      <div class="metrics">
        <div class="metric"><div class="k">RSI 14</div><div class="v ${d.rsi > 70 ? "down" : d.rsi < 30 ? "up" : ""}">${fmt(d.rsi, 1)}</div></div>
        <div class="metric"><div class="k">MA20</div><div class="v">${fmt(d.ma20, 1)}</div></div>
        <div class="metric"><div class="k">MA50</div><div class="v">${fmt(d.ma50, 1)}</div></div>
        <div class="metric"><div class="k">MA200</div><div class="v">${fmt(d.ma200, 1)}</div></div>
        <div class="metric"><div class="k">KL / TB20</div><div class="v">${fmt(d.vol_ratio, 2)}×</div></div>
        <div class="metric"><div class="k">MACD hist</div><div class="v ${cls(d.macd_hist)}">${fmt(d.macd_hist, 3)}</div></div>
        <div class="metric"><div class="k">20 phiên</div><div class="v ${cls(d.r20)}">${sign(d.r20, 1)}%</div></div>
        <div class="metric"><div class="k">Hỗ trợ</div><div class="v">${fmt(d.sup, 1)}</div></div>
        <div class="metric"><div class="k">Kháng cự</div><div class="v">${fmt(d.res, 1)}</div></div>
        <div class="metric"><div class="k">52 tuần</div><div class="v" style="font-size:12.5px">${fmt(d.lo52, 0)}–${fmt(d.hi52, 0)}</div></div>
      </div>

      <div class="plan">
        <div class="cell k"><div class="k-label">Vùng vào lệnh</div><div class="k-val">${fmt(d.entry[0], 1)} – ${fmt(d.entry[1], 1)}</div></div>
        <div class="cell r"><div class="k-label">Cắt lỗ</div><div class="k-val">${fmt(d.stop, 1)}</div><div class="k-sub">rủi ro ${fmt(d.risk_pct, 1)}%</div></div>
        <div class="cell t"><div class="k-label">Chốt lời T1</div><div class="k-val">${fmt(d.t1, 1)}</div><div class="k-sub">RR ~1:${fmt(d.rr, 1)}</div></div>
        <div class="cell t"><div class="k-label">Chốt lời T2</div><div class="k-val">${fmt(d.t2, 1)}</div><div class="k-sub">đỉnh 52w ${fmt(d.hi52, 0)}</div></div>
      </div>

      <div class="entry-note">💡 ${d.entry_note}</div>
      <div class="narrative">${d.narrative}</div>

      <div class="chart-head">
        <h4>Biểu đồ nến 260 phiên</h4>
        <div class="chart-legend">
          <span><i style="background:#f0b423"></i>MA20</span>
          <span><i style="background:#4d8dff"></i>MA50</span>
          <span><i style="background:var(--up)"></i>Tăng</span>
          <span><i style="background:var(--down)"></i>Giảm</span>
        </div>
      </div>
      <div id="chart"></div>

      <div class="news" id="news">
        <h4>Tin tức ${d.symbol}</h4>
        <div class="loading-line"><span class="spinner"></span> Đang tải tin…</div>
      </div>
    </div>`;

  const newsBox = document.getElementById("news");
  if (newsBox && lastNewsHTML) newsBox.innerHTML = lastNewsHTML;
  drawChart(d.ohlcv);
}

/* ---------------- chart ---------------- */
function sma(vals, n) {
  const out = [];
  let sum = 0;
  for (let i = 0; i < vals.length; i++) {
    sum += vals[i];
    if (i >= n) sum -= vals[i - n];
    if (i >= n - 1) out.push(sum / n);
  }
  return out;
}

function drawChart(ohlcv) {
  const box = document.getElementById("chart");
  if (!box || !window.LightweightCharts) return;
  if (chart) { chart.remove(); chart = null; }
  if (!ohlcv || !ohlcv.length) return;

  chart = LightweightCharts.createChart(box, {
    layout: {
      background: { color: cssVar("--chart-bg", "#0e141d") },
      textColor: cssVar("--chart-text", "#8b97ad"),
      fontFamily: "Segoe UI, sans-serif",
    },
    grid: {
      vertLines: { color: cssVar("--chart-grid", "#1b2331") },
      horzLines: { color: cssVar("--chart-grid", "#1b2331") },
    },
    rightPriceScale: { borderColor: cssVar("--chart-border", "#242f40") },
    timeScale: { borderColor: cssVar("--chart-border", "#242f40"), rightOffset: 4 },
    crosshair: { mode: 0 },
    autoSize: true,
  });

  const candles = chart.addCandlestickSeries({
    upColor: cssVar("--up", "#2ecc71"), downColor: cssVar("--down", "#ff5b5b"),
    borderVisible: false,
    wickUpColor: cssVar("--up", "#2ecc71"), wickDownColor: cssVar("--down", "#ff5b5b"),
  });
  candles.setData(ohlcv.map((r) => ({ time: r.time, open: r.open, high: r.high, low: r.low, close: r.close })));

  const closes = ohlcv.map((r) => r.close);
  const ma20 = sma(closes, 20).map((v, i) => ({ time: ohlcv[i + 19].time, value: v }));
  const ma50 = sma(closes, 50).map((v, i) => ({ time: ohlcv[i + 49].time, value: v }));

  const l20 = chart.addLineSeries({ color: "#f0b423", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
  l20.setData(ma20);
  const l50 = chart.addLineSeries({ color: "#4d8dff", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
  l50.setData(ma50);

  chart.timeScale().fitContent();
}

/* ---------------- news ---------------- */
async function loadNews(sym) {
  const box = document.getElementById("news");
  if (!box) return;
  try {
    const st = await api(`/api/symbol/${sym}/news`);
    const items = st.items || [];
    if (!items.length) {
      box.innerHTML = `<h4>Tin tức ${sym}</h4><div class="empty">Chưa có tin.</div>`;
      lastNewsHTML = box.innerHTML;
      return;
    }
    box.innerHTML =
      `<h4>Tin tức ${sym} <span style="text-transform:none;font-weight:400">(CafeF)</span></h4><ul>` +
      items.map((n) => `<li>
            <span class="n-date">${n.date}</span>
            <a class="n-title" href="${n.url}" target="_blank" rel="noopener">${n.title}</a>
            ${n.sub ? `<div class="n-sub">${n.sub}</div>` : ""}
          </li>`).join("") +
      `</ul>`;
    lastNewsHTML = box.innerHTML;
  } catch (e) {
    box.innerHTML = `<h4>Tin tức ${sym}</h4><div class="empty">Không tải được tin (${e.message}).</div>`;
  }
}

/* ---------------- suggestions ---------------- */
function hideSuggest() { $("#symSuggest").classList.remove("show"); }

function renderSuggest(q) {
  const box = $("#symSuggest");
  q = (q || "").toUpperCase().trim();
  if (!q) { hideSuggest(); return; }
  const list = BASKET.filter((s) => s.startsWith(q) || s.includes(q)).slice(0, 8);
  if (!list.length) { hideSuggest(); return; }
  box.innerHTML = list.map((sym) => {
    const r = screenRows.find((x) => x.symbol === sym);
    const tone = r ? r.tone : "neutral";
    return `<button type="button" data-sym="${sym}" role="option">
      <span class="s-sym">${sym}</span>
      <span class="s-hint">${r ? fmt(r.close, r.close < 50 ? 1 : 0) + " · " + sign(r.r20, 1) + "%" : "chưa có trong màn lọc"}</span>
      ${r ? `<span class="s-score score ${tone}">${r.score}</span>` : ""}
    </button>`;
  }).join("");
  box.classList.add("show");
  box.querySelectorAll("button").forEach((b) => {
    b.addEventListener("mousedown", (e) => { e.preventDefault(); openSymbol(b.dataset.sym); });
  });
}

/* ---------------- live mode ---------------- */
const LIVE_MS = 60000;
let liveOn = true;
try { liveOn = localStorage.getItem("ck_live") !== "0"; } catch (e) {}
let nextLive = Date.now() + LIVE_MS;
let inSession = true;

function setLiveBtn() {
  $("#btnLive").classList.toggle("off", !liveOn);
}

async function loadSession() {
  try {
    const s = await api("/api/session");
    inSession = !!s.in_session;
  } catch (e) {}
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
  if (selectedSym && !detailBusy) openSymbol(selectedSym, true);
}

/* ---------------- events ---------------- */
$("#btnRunScreen").addEventListener("click", runScreen);
$("#btnRefreshOverview").addEventListener("click", () => {
  loadOverview(true);
  toast("Đang làm mới chỉ số…");
});
$("#btnAnalyze").addEventListener("click", () => openSymbol($("#symInput").value));
$("#btnTheme").addEventListener("click", toggleTheme);

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
      await api("/api/screen/run?auto=1", { method: "POST" });
      nextLive = Date.now() + 5000;
      doLive();
      toast("Live bật — tự làm mới 60s trong phiên", "ok");
    } else {
      await api("/api/screen/stop", { method: "POST" });
      toast("Đã tắt Live — dữ liệu dùng cache", "warn");
    }
  } catch (e) { toast("Không kết nối được server", "err"); }
  loadScreen();
});

/* sort/filter chips */
$("#sortChips").addEventListener("click", (e) => {
  const b = e.target.closest(".chip-btn");
  if (!b) return;
  const key = b.dataset.sort;
  if (key === sortBy) sortDir = -sortDir;
  else { sortBy = key; sortDir = -1; }
  document.querySelectorAll("#sortChips .chip-btn").forEach((c) => {
    const on = c.dataset.sort === sortBy;
    c.classList.toggle("on", on);
    c.querySelector(".arr").textContent = on ? (sortDir === -1 ? "▼" : "▲") : "▼";
  });
  renderScreen(screenRows);
});

$("#filterChips").addEventListener("click", (e) => {
  const b = e.target.closest(".chip-btn");
  if (!b) return;
  filterBy = b.dataset.filter;
  document.querySelectorAll("#filterChips .chip-btn").forEach((c) => {
    c.classList.toggle("on", c.dataset.filter === filterBy);
    c.classList.toggle("good", c.dataset.filter === "good" && c.classList.contains("on"));
    c.classList.toggle("bad", c.dataset.filter === "bad" && c.classList.contains("on"));
  });
  renderScreen(screenRows);
});

/* search input */
const input = $("#symInput");
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { openSymbol(input.value); }
  if (e.key === "Escape") { hideSuggest(); input.blur(); }
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
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && liveOn) nextLive = Date.now() + 3000;
});

/* ---------------- init ---------------- */
applyTheme(document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark");
setLiveBtn();

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
loadScreen();

if (liveOn) {
  api("/api/screen/run?auto=1", { method: "POST" }).then(() => loadScreen()).catch(() => {});
}
