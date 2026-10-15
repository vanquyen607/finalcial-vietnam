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
      <div class="label">${ix.label} · phiên ${fmtDate(ix.date)}</div>
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
      <div class="trend">Xu hướng: <b>${ix.trend}</b> ${ix.above_ma200 === false ? "· ⚠️ dưới MA200" : ""}</div>`;
    box.appendChild(el);
  });
  const meta = document.createElement("div");
  meta.className = "card";
  meta.innerHTML = `<div class="label">Nguồn & cập nhật</div>
    <div class="trend" style="margin-top:7px">Cập nhật: <b>${st.updated_at || "—"}</b></div>
    <div class="trend">${st.stale ? "⚠️ Dữ liệu cũ hơn 30 phút — bấm ⟳ Chỉ số" : "Tự làm mới theo Live (60s trong phiên)"}</div>
    <div class="trend">vnstock/VCI · cache 30 phút</div>`;
  box.appendChild(meta);
  updateNotice(st);
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
    return `<div class="br-row">
      <span class="br-ex">${lab}</span>
      <span class="br-up">▲ ${e.up}</span>
      <span class="br-flat">– ${e.flat}</span>
      <span class="br-down">▼ ${e.down}</span>
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

