/* Phan Tich Co Phieu VN — detail.js (tach tu app.js) */
/* ---------------- detail ---------------- */
async function openSymbol(sym, refresh = false) {
  sym = (sym || "").toUpperCase().trim();
  if (!/^[A-Z]{2,6}$/.test(sym)) {
    if (compareMode) { toast("Nhập mã hợp lệ để so sánh (2–6 chữ cái)", "warn"); return; }
    $("#detail").innerHTML = `<div class="err">Mã không hợp lệ (2–6 chữ cái, VD: HPG)</div>`;
    return;
  }
  if (compareMode && !refresh) { runCompare(sym); return; }   /* đang so sánh → mã nhập là mã thứ 2 */
  selectedSym = sym;
  detailBusy = true;
  document.querySelectorAll("#screenBody tr").forEach((tr) => {
    tr.classList.toggle("sel", tr.dataset.sym === sym);
    tr.setAttribute("aria-selected", String(tr.dataset.sym === sym));
  });
  $("#symInput").value = sym;
  hideSuggest();
  if (!refresh) {
    lastNewsHTML = "";
    newsExpanded = false;
    lastPrice = null;
    lastDetail = null;                 /* base của nút So sánh bị reset khi đổi mã */
    $("#btnCompare").disabled = true;
    $("#detail").innerHTML = `<div class="loading-line"><span class="spinner"></span> Đang phân tích <b>${sym}</b> — chờ lượt gọi dữ liệu (~10–20 giây)…</div>`;
  }
  try {
    const st = await api(`/api/symbol/${sym}` + (refresh ? "?refresh=1" : ""));
    if (sym !== selectedSym) return;   /* người dùng đã chọn mã khác — bỏ request cũ */
    detailBusy = false;
    if (st.status !== "ready") {
      if (!refresh) $("#detail").innerHTML = `<div class="err">${esc(st.message || "Không có dữ liệu")}</div>`;
      else toast(st.message || "Không tải được " + sym, "err");
      return;
    }
    renderDetail(st.data, st.stale);
    if (!refresh) {
      $("#detail").scrollTop = 0;          /* về đầu khi mở mã mới */
      if (location.hash.slice(1).toUpperCase() !== sym) location.hash = sym;
      loadNews(sym);
    }
  } catch (e) {
    if (sym !== selectedSym) return;
    detailBusy = false;
    if (!refresh) $("#detail").innerHTML = `<div class="err">Lỗi: ${esc(e.message)}</div>`;
  }
}

function renderDetail(d, stale) {
  const tone = d.tone || "neutral";
  lastDetail = d;
  lastStale = !!stale;
  const priceFlash = lastPrice != null && lastPrice !== d.close
    ? (d.close > lastPrice ? " flash-up" : " flash-down")
    : "";
  const prevPrice = lastPrice;
  lastPrice = d.close;
  const watched = inWatch(d.symbol);

  $("#detail").innerHTML = `
    <div class="detail">
      <div class="d-head">
        <span class="name">${d.symbol}</span>
        <button class="star${watched ? " on" : ""}" data-star type="button"
                aria-pressed="${watched}" title="Thêm/bỏ ${d.symbol} vào ⭐ Của tôi">${watched ? "★" : "☆"}</button>
        <span class="price${priceFlash}">${fmt(d.close, d.close < 50 ? 1 : 0)}</span>
        <span class="dchg ${cls(d.r5)}">5 phiên: ${sign(d.r5, 1)}%</span>
        <span class="date">phiên ${fmtDate(d.date)}${stale ? " · cache cũ" : ""}</span>
      </div>
      <div class="verdict-line">
        <span class="big-tag ${tone}">${d.verdict}</span>
        <span class="score ${tone}" style="font-size:13.5px">Điểm ${d.score}/${d.max_score}</span>
        <span class="trend">${d.trend}</span>
      </div>

      ${d.regime_gate ? `<div class="regime-note">⚠️ ${esc(d.regime_note || "Thị trường bất lợi — cân nhắc chờ.")}</div>` : ""}

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

      <div class="fund" id="fund"></div>

      <div class="plan">
        <div class="cell k"><div class="k-label">Vùng vào lệnh</div><div class="k-val">${fmt(d.entry[0], 1)} – ${fmt(d.entry[1], 1)}</div></div>
        <div class="cell r"><div class="k-label">Cắt lỗ (quản lý rủi ro)</div><div class="k-val">${fmt(d.stop, 1)}</div><div class="k-sub">rủi ro ${fmt(d.risk_pct, 1)}%</div></div>
        <div class="cell t"><div class="k-label">Chốt lời T1 (gợi ý)</div><div class="k-val">${fmt(d.t1, 1)}</div><div class="k-sub">RR ~1:${fmt(d.rr, 1)}</div></div>
        <div class="cell t"><div class="k-label">Chốt lời T2 (gợi ý)</div><div class="k-val">${fmt(d.t2, 1)}</div><div class="k-sub">đỉnh 52w ${fmt(d.hi52, 0)}</div></div>
      </div>

      <div class="backtest-note">📊 Backtest 3 năm (623 lệnh ≥10 điểm): stop/T1 giúp giảm thắng lớn hơn là cắt lỗ — max lợi nhuận từ +64% xuống +12%. Dùng stop để <b>chống lỗ nặng</b>, không kỳ vọng tối ưu lời. Hold 20 phiên không stop: TB +0.94%, t-stat 0.22 (không vượt index có ý nghĩa).</div>

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
  if (newsBox && lastNewsHTML) { newsBox.innerHTML = lastNewsHTML; syncNewsState(); }
  drawChart(d.ohlcv);
  syncCompareUI();
  checkAlerts(d);
  if (fundCache[d.symbol]) renderFund(fundCache[d.symbol]);
  else loadFundamentals(d.symbol);          /* lazy — khong block phan tich ky thuat */
}

/* ---------------- báo giá ---------------- */
function checkAlerts(d) {
  if (!d || !d.close || !d.stop) return;
  const p = d.close;
  const hits = [];
  if (p <= d.stop) hits.push({ k: "stop", kind: "err", msg: `${d.symbol} ⚠️ chạm vùng cắt lỗ ${fmt(d.stop, 1)} (giá ${fmt(p, 1)}) — xem xét thoát lệnh` });
  else if (p >= d.entry[0] && p <= d.entry[1]) hits.push({ k: "entry", kind: "ok", msg: `${d.symbol} 💰 đang trong vùng vào lệnh ${fmt(d.entry[0], 1)}–${fmt(d.entry[1], 1)}` });
  if (p >= d.t2) hits.push({ k: "t2", kind: "ok", msg: `${d.symbol} 🎯 đã đạt T2 ${fmt(d.t2, 1)} — chốt lời` });
  else if (p >= d.t1) hits.push({ k: "t1", kind: "ok", msg: `${d.symbol} 🎯 đã đạt T1 ${fmt(d.t1, 1)} — cân nhắc chốt lời` });

  hits.forEach((h) => {
    const id = `${d.symbol}:${h.k}`;
    if (firedAlerts.has(id)) return;
    firedAlerts.add(id);
    toast(h.msg, h.kind);
    if (window.Notification && Notification.permission === "granted") {
      try { new Notification("Báo giá " + d.symbol, { body: h.msg }); } catch (e) {}
    }
  });
}

/* ---------------- chỉ số cơ bản (fundamental) ----------------
   Chỉ giữ 6 chỉ số dễ hiểu cho người mới; di chuột ô nào xem ý nghĩa ô đó. */
const fundCache = {};
const fundPending = new Set();
const FUND_KEYS = [
  ["P/E", ["pe_ratio"], 1, "", "Giá cao gấp mấy lần so với lãi 1 năm — dưới 15 thường là rẻ"],
  ["P/B", ["pb_ratio"], 1, "", "Giá so với giá trị tài sản ròng trên sổ sách — dưới 1 là rẻ hơn sổ sách"],
  ["EPS", ["trailing_eps"], 0, "đ", "Lãi của 1 cổ phiếu trong 12 tháng qua"],
  ["ROE", ["roe_trailling", "roe"], 1, "%", "Lãi trên vốn bỏ ra — trên 15%/năm là tốt"],
  ["Biên gộp", ["gross_margin"], 1, "%", "Phần trăm lãi sau khi trừ giá vốn — càng cao càng khỏe"],
  ["Cổ tức", ["dividend_yield"], 1, "%", "Tiền cổ tức nhận được mỗi năm so với giá cổ phiếu"],
];
/* tag nhanh: người mới nhìn là biết đắt/rẻ, tốt/yếu */
const fundTag = (lab, v) => {
  if (lab === "P/E") return v < 10 ? '<span class="chip-mini up">Rẻ</span>'
    : v <= 20 ? '<span class="chip-mini">Vừa</span>'
    : '<span class="chip-mini down">Đắt</span>';
  if (lab === "ROE") return v >= 15 ? '<span class="chip-mini up">Tốt</span>'
    : v < 8 ? '<span class="chip-mini down">Yếu</span>' : "";
  return "";
};
async function loadFundamentals(sym) {
  const box = document.getElementById("fund");
  if (!box || fundCache[sym] || fundPending.has(sym)) return;
  fundPending.add(sym);
  box.innerHTML = `<div class="loading-line"><span class="spinner"></span> Đang tải chỉ số cơ bản…</div>`;
  try {
    const st = await api(`/api/symbol/${sym}/fundamentals`);
    fundPending.delete(sym);
    if (st.status !== "ready" || !st.data) { box.remove(); return; }
    fundCache[sym] = st;
    if (selectedSym === sym) renderFund(st);
  } catch (e) { fundPending.delete(sym); box.remove(); }
}
function renderFund(st) {
  const box = document.getElementById("fund");
  if (!box) return;
  const d = st.data || {};
  const cells = FUND_KEYS.map(([lab, keys, dp, suf, hint]) => {
    const k = keys.find((x) => d[x] != null && !isNaN(d[x]));
    if (!k) return "";
    return `<div class="metric" title="${hint}"><div class="k">${lab}</div>
      <div class="v">${fmt(d[k], dp)}${suf}${fundTag(lab, d[k])}</div></div>`;
  }).join("");
  if (!cells) { box.remove(); return; }
  box.innerHTML = `<h4>Chỉ số cơ bản${st.stale ? " · cache cũ" : ""}</h4>
    <div class="metrics">${cells}</div>
    <div class="fund-hint">💡 Di chuột vào tên chỉ số để xem ý nghĩa — P/E thấp thường rẻ, ROE cao sinh lời tốt.</div>`;
}

/* ---------------- so sánh 2 mã ---------------- */
function syncCompareUI() {
  const btn = $("#btnCompare");
  btn.classList.toggle("on", compareMode);
  btn.textContent = compareMode ? "✕ Hủy so sánh" : "⊕ So sánh";
  btn.disabled = !lastDetail && !compareMode;
  $("#symInput").placeholder = compareMode && lastDetail
    ? `Nhập mã thứ 2 để so sánh với ${lastDetail.symbol}…`
    : "Tìm mã cổ phiếu… (VD: HPG)";
}

async function runCompare(symB) {
  const base = lastDetail;
  if (!base) { compareMode = false; syncCompareUI(); toast("Chưa có mã thứ nhất để so sánh", "warn"); return; }
  if (symB === base.symbol) { toast("Hãy chọn mã khác mã đang xem", "warn"); return; }
  compareSym = symB;
  hideSuggest();
  $("#detail").innerHTML = `<div class="loading-line"><span class="spinner"></span> Đang tải <b>${symB}</b> để so sánh với <b>${base.symbol}</b>…</div>`;
  $("#detail").scrollTop = 0;
  try {
    const ensureFund = (sym) => fundCache[sym] ? Promise.resolve()
      : api(`/api/symbol/${sym}/fundamentals`).then((st) => {
          if (st.status === "ready" && st.data) fundCache[sym] = st;
        }).catch(() => {});
    const [st] = await Promise.all([
      api(`/api/symbol/${symB}`),
      ensureFund(base.symbol),
      ensureFund(symB),
    ]);
    if (!compareMode || compareSym !== symB) return;
    if (st.status !== "ready") throw new Error(st.message || "Không có dữ liệu");
    renderCompare(base, st.data);
  } catch (e) {
    if (!compareMode) return;
    toast("Không so sánh được: " + e.message, "err");
    exitCompare();
  }
}

function renderCompare(A, B) {
  const tagOf = (d) => `<span class="tag ${d.tone || "neutral"}">${d.verdict}</span>`;
  const scoreOf = (d) => `<span class="score ${d.tone || "neutral"}">${d.score}</span>`;
  const fval = (sym, keys) => {
    const d = (fundCache[sym] || {}).data || {};
    const k = keys.find((x) => d[x] != null && !isNaN(d[x]));
    return k ? fmt(d[k], 1) : "—";
  };
  const rows = [
    ["Giá đóng cửa", fmt(A.close, 1), fmt(B.close, 1)],
    ["5 phiên", sign(A.r5, 1) + "%", sign(B.r5, 1) + "%"],
    ["RSI 14", fmt(A.rsi, 1), fmt(B.rsi, 1)],
    ["MA20", fmt(A.ma20, 1), fmt(B.ma20, 1)],
    ["MA50", fmt(A.ma50, 1), fmt(B.ma50, 1)],
    ["MA200", fmt(A.ma200, 1), fmt(B.ma200, 1)],
    ["20 phiên", sign(A.r20, 1) + "%", sign(B.r20, 1) + "%"],
    ["KL / TB20", fmt(A.vol_ratio, 2) + "×", fmt(B.vol_ratio, 2) + "×"],
    ["MACD hist", fmt(A.macd_hist, 3), fmt(B.macd_hist, 3)],
    ["Hỗ trợ", fmt(A.sup, 1), fmt(B.sup, 1)],
    ["Kháng cự", fmt(A.res, 1), fmt(B.res, 1)],
    ["Vùng vào lệnh", `${fmt(A.entry[0], 1)} – ${fmt(A.entry[1], 1)}`, `${fmt(B.entry[0], 1)} – ${fmt(B.entry[1], 1)}`],
    ["Cắt lỗ", fmt(A.stop, 1), fmt(B.stop, 1)],
    ["Chốt lời T1 / T2", `${fmt(A.t1, 1)} / ${fmt(A.t2, 1)}`, `${fmt(B.t1, 1)} / ${fmt(B.t2, 1)}`],
    ["Tín hiệu", tagOf(A), tagOf(B)],
    ["Điểm", `${scoreOf(A)} / ${A.max_score}`, `${scoreOf(B)} / ${B.max_score}`],
    ["Xu hướng", A.trend || "—", B.trend || "—"],
    ["P/E", fval(A.symbol, ["pe_ratio"]), fval(B.symbol, ["pe_ratio"])],
    ["ROE", fval(A.symbol, ["roe_trailling", "roe"]), fval(B.symbol, ["roe_trailling", "roe"])],
    ["Cổ tức", fval(A.symbol, ["dividend_yield"]), fval(B.symbol, ["dividend_yield"])],
  ];
  $("#detail").innerHTML = `
    <div class="detail cmp">
      <div class="d-head">
        <span class="name">${A.symbol}</span>
        <span class="vs">vs</span>
        <span class="name">${B.symbol}</span>
        <span class="date">phiên ${fmtDate(A.date)} · ${fmtDate(B.date)}</span>
      </div>
      <div class="cmp-bar">
        <span class="cmp-note">💡 Nhập mã khác + Enter để đổi đối thủ, Esc hoặc bấm nút để thoát.</span>
        <button class="btn" id="btnCmpClose" type="button">✕ Hủy so sánh</button>
      </div>
      <table class="cmp-tbl">
        <thead><tr><th>Tiêu chí</th><th>${A.symbol}</th><th>${B.symbol}</th></tr></thead>
        <tbody>${rows.map(([k, a, b]) => `<tr><td>${k}</td><td>${a}</td><td>${b}</td></tr>`).join("")}</tbody>
      </table>
    </div>`;
  $("#detail").scrollTop = 0;
}

function exitCompare() {
  compareMode = false;
  compareSym = null;
  syncCompareUI();
  if (lastDetail) renderDetail(lastDetail, lastStale);
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
const NEWS_PREVIEW = 5;

function syncNewsState() {
  const box = document.getElementById("news");
  if (!box) return;
  const btn = box.querySelector(".news-more");
  if (!btn) return;
  box.classList.toggle("expanded", newsExpanded);
  btn.setAttribute("aria-expanded", String(newsExpanded));
  btn.textContent = newsExpanded ? "Thu gọn ▴" : `Xem ${box.querySelectorAll("li").length} tin ▾`;
}

async function loadNews(sym) {
  const box = document.getElementById("news");
  if (!box) return;
  try {
    const st = await api(`/api/symbol/${sym}/news`);
    if (sym !== selectedSym) return;
    const items = st.items || [];
    if (!items.length) {
      box.innerHTML = `<h4>Tin tức ${sym}</h4><div class="empty">Chưa có tin.</div>`;
      lastNewsHTML = box.innerHTML;
      return;
    }
    box.innerHTML =
      `<h4>Tin tức ${sym} · ${items.length} tin <span style="text-transform:none;font-weight:400">(CafeF)</span></h4><ul>` +
      items.map((n, i) => `<li${i >= NEWS_PREVIEW ? ' class="extra"' : ""}>
            <span class="n-date">${esc(n.date)}</span>
            <a class="n-title" href="${esc(safeUrl(n.url))}" target="_blank" rel="noopener noreferrer">${esc(n.title)}</a>
            ${n.sub ? `<div class="n-sub">${esc(n.sub)}</div>` : ""}
          </li>`).join("") +
      `</ul>` +
      (items.length > NEWS_PREVIEW ? `<button class="news-more" type="button"></button>` : "");
    syncNewsState();
    lastNewsHTML = box.innerHTML;
  } catch (e) {
    if (sym !== selectedSym) return;
    box.innerHTML = `<h4>Tin tức ${sym}</h4><div class="empty">Không tải được tin (${esc(e.message)}).</div>`;
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

