/* Phan Tich Co Phieu VN — overview.js (tach tu app.js) */
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
      if (!silent) $("#cards").innerHTML = `<div class="card"><div class="err">Không tải được chỉ số: ${esc(st.message || "?")}</div></div>`;
      else toast("Làm mới chỉ số thất bại", "err");
      return;
    }
    renderCards(st);
    clearTimeout(pollTimers.overview);
    /* du lieu qua cu (>30 phut) -> tu refresh MOT lan, khong can nhan tau */
    if (st.stale && !refresh && !loadOverview.autoDone) {
      loadOverview.autoDone = true;
      setTimeout(() => loadOverview(true, true), 400);
    }
  } catch (e) {
    if (!silent) $("#cards").innerHTML = `<div class="card"><div class="err">Lỗi: ${esc(e.message)}</div></div>`;
  }
}

function renderCards(st) {
  const box = $("#cards");
  box.innerHTML = "";
  (st.indices || []).forEach((ix) => {
    const el = document.createElement("div");
    el.className = "card";
    el.innerHTML = `
      <div class="label"><b>${ix.label}</b><span>· phiên ${fmtDate(ix.date)}</span></div>
      <div class="ix-val">
        <span class="big ${cls(ix.chg_pct)}">${fmt(ix.close, 2)}</span>
        <span class="chg ${cls(ix.chg_pct)}">${sign(ix.chg, 2)} điểm (${sign(ix.chg_pct, 2)}%)</span>
      </div>
      <div class="ix-grid">
        <div class="ix-cell"><span>MA20</span><b>${fmt(ix.ma20, 0)}</b></div>
        <div class="ix-cell"><span>MA50</span><b>${fmt(ix.ma50, 0)}</b></div>
        <div class="ix-cell"><span>MA200</span><b>${fmt(ix.ma200, 0)}</b></div>
        <div class="ix-cell"><span>20 phiên</span><b class="${cls(ix.r20)}">${sign(ix.r20, 1)}%</b></div>
        <div class="ix-cell"><span>Vùng 30 phiên</span><b>${fmt(ix.lo30, 0)} – ${fmt(ix.hi30, 0)}</b></div>
        <div class="ix-cell"><span>KL / TB20</span><b>${fmt(ix.vol_last_m, 0)}tr / ${fmt(ix.vol20_m, 0)}tr</b></div>
      </div>
      <div class="trend">Xu hướng: <b>${ix.trend}</b> ${ix.above_ma200 === false ? "· ⚠️ dưới MA200" : ""}</div>`;
    box.appendChild(el);
  });
  const meta = document.createElement("div");
  meta.className = "card meta";
  meta.innerHTML = `<div class="label">Nguồn &amp; cập nhật</div>
    <div class="trend" style="margin-top:7px">Cập nhật: <b>${st.updated_at || "—"}</b></div>
    <div class="trend">${st.stale ? "⚠️ Dữ liệu cũ hơn 30 phút — bấm ⟳ Chỉ số" : "Tự làm mới theo Live (60s trong phiên)"}</div>
    <div class="trend">vnstock/VCI · cache 30 phút</div>`;
  box.appendChild(meta);
  updateNotice(st);
  loadRegime(st);
}

/* ---------------- regime banner ---------------- */
async function loadRegime(ovState) {
  try {
    const st = await api("/api/regime");
    renderRegime(st, ovState);
  } catch (e) { /* im lang — regime la phu */ }
}
function renderRegime(st, ovState) {
  const el = document.getElementById("regimeBanner");
  if (!el || st.status !== "ready") { if (el) el.hidden = true; return; }
  const r = st.regime;
  const icons = { bull: "📈", bear: "📉", neutral: "➖" };
  const labels = { bull: "THỊ TRƯỜNG THUẬN LỢI", bear: "THỊ TRƯỜNG BẤT LỢI", neutral: "THỊ TRƯỜNG TRUNG TÍNH" };
  el.hidden = false;
  el.className = `regime-banner ${r}`;
  el.innerHTML = `<span class="r-ico">${icons[r] || "➖"}</span>
    <span class="r-txt">${labels[r] || "TRUNG TÍNH"}<span class="r-reason">${esc(regimeReason(st, ovState))}</span></span>`;
}
/* Ly do regime: so chi so lay tu du lieu overview dang hien (luon khop the chi so),
   phan breadth lay tu /api/regime. Chi hien tin hieu ung ho verdict (nhu cu). */
function regimeReason(st, ovState) {
  const vn = ovState && (ovState.indices || []).find((x) => x.code === "VNINDEX");
  const vnTxt = vn && vn.close != null && vn.ma50 != null
    ? `VN-Index ${vn.close.toFixed(1)} vs MA50 ${vn.ma50.toFixed(1)}`
    : (st.vn_label || "");
  const parts = [];
  if (st.regime === "bull") {
    if (st.vn_above_ma50 === true && vnTxt) parts.push(vnTxt);
    if (st.breadth_bull === true && st.breadth_label) parts.push(st.breadth_label);
  } else if (st.regime === "bear") {
    if (st.vn_above_ma50 === false && vnTxt) parts.push(vnTxt);
    if (st.breadth_bull === false && st.breadth_label) parts.push(st.breadth_label);
  } else {
    if (vnTxt) parts.push(vnTxt);
    else if (st.breadth_label) parts.push(st.breadth_label);
  }
  return parts.join(" · ") || st.reason || "";
}

/* notice: câu đầu tự lấy từ dữ liệu chỉ số, không còn hardcoded */
function updateNotice(st) {
  const el = document.getElementById("noticeText");
  const ix = (st.indices || [])[0];
  if (!el || !ix) return;
  el.textContent = `Thị trường ${ix.label}: ${ix.trend}${ix.above_ma200 === false ? " · ⚠️ dưới MA200" : ""} —`
    + " giải ngân từng phần, luôn đặt cắt Lỗ.";
}

/* ---------------- breadth (tăng/giảm + thanh khoản + ngoại theo sàn) ---------------- */
let breadthPending = false;
async function loadBreadth() {
  if (breadthPending) return;
  breadthPending = true;
  try {
    const st = await api("/api/breadth");
    renderBreadth(st);
    clearTimeout(pollTimers.breadth);
    if (st.status === "fetching") pollTimers.breadth = setTimeout(loadBreadth, 5000);
  } catch (e) { /* im lang — breadth la phu */ }
  finally { breadthPending = false; }
}
function renderBreadth(st) {
  const box = $("#breadthCard");
  if (!box) return;
  if (st.status === "empty" || st.status === "error" || !st.exchanges) {
    box.hidden = true;
    return;
  }
  const rows = [["HOSE", "hose"], ["HNX", "hnx"], ["UPCOM", "upcom"]].map(([lab, k]) => {
    const e = st.exchanges[k];
    if (!e || !e.n) return "";
    const tot = Math.max(1, e.up + e.flat + e.down);
    return `<div class="br-row">
      <span class="br-ex">${lab}</span>
      <span class="br-up">▲ ${e.up}</span>
      <span class="br-flat">– ${e.flat}</span>
      <span class="br-down">▼ ${e.down}</span>
      <span class="br-bar" role="img" aria-label="${lab}: ${e.up} tăng, ${e.flat} đứng, ${e.down} giảm">
        <i class="u" style="width:${(e.up / tot * 100).toFixed(1)}%"></i><i class="f" style="width:${(e.flat / tot * 100).toFixed(1)}%"></i><i class="d" style="width:${(e.down / tot * 100).toFixed(1)}%"></i>
      </span>
      <span class="br-val">${fmt(e.value_t, 0)} tỷ GTGD</span>
      <span class="br-fn ${cls(e.fnet_t)}">Ngoại ${sign(e.fnet_t, 1)} tỷ</span>
    </div>`;
  }).join("");
  if (!rows.trim()) { box.hidden = true; return; }
  box.hidden = false;
  box.innerHTML = `<div class="label">Thị trường hôm nay · tăng / đứng / giảm${st.stale ? " · dữ liệu cũ" : ""}</div>
    ${rows}
    <div class="trend">Tổng GTGD <b>${fmt(st.total && st.total.value_t, 0)} tỷ</b> · ngoại ròng toàn thị trường
      <b class="${cls(st.total && st.total.fnet_t)}">${sign(st.total && st.total.fnet_t, 1)} tỷ</b>
      · ${st.updated_at || ""}</div>`;
}

