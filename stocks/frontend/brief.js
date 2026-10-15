/* Brief — ban tin tong hop tu cache, khong goi API. */
"use strict";
(function () {
  const $ = (s, r) => (r || document).querySelector(s);

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function fmt(n, d = 1) {
    if (n == null || n !== n) return "—";
    return Number(n).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function sign(n, d = 1) { return (n > 0 ? "+" : "") + fmt(n, d); }
  function cls(n) { return n > 0 ? "up" : n < 0 ? "down" : "flat"; }

  const EV_ICONS = { dividend: "💰", listing: "📋", issuance: "📢", agm: "🏛", earnings: "📊", other: "📅" };
  const EV_LABELS = { dividend: "Cổ tức", listing: "Niêm yết", issuance: "Phát hành", agm: "ĐHCĐ", earnings: "KQKD", other: "Khác" };

  async function loadBrief() {
    const body = $("#briefBody");
    if (!body) return;
    body.innerHTML = `<div class="empty">Đang tạo…</div>`;
    try {
      const st = await api("/api/brief");
      renderBrief(st);
    } catch (e) {
      body.innerHTML = `<div class="empty">Lỗi: ${esc(e.message)}</div>`;
    }
  }

  function renderBrief(st) {
    const body = $("#briefBody");
    if (!body) return;
    let html = "";

    // Lines summary
    if (st.lines && st.lines.length) {
      html += `<div class="bp-summary">` +
        st.lines.map(l => `<div class="bp-line">${esc(l)}</div>`).join("") + `</div>`;
    }

    // Indices
    if (st.indices && st.indices.length) {
      html += `<div class="bp-sec">Chỉ số</div><div class="bp-grid">` +
        st.indices.map(i => `<div class="bp-cell">
          <div class="bp-k">${esc(i.name)}</div>
          <div class="bp-v">${fmt(i.value, 1)}</div>
          <div class="bp-chg ${cls(i.change_pct)}">${i.change_pct != null ? sign(i.change_pct, 2) + "%" : "—"}</div>
        </div>`).join("") + `</div>`;
    }

    // Regime
    if (st.regime && st.regime.state) {
      const s = st.regime.state;
      const icon = s === "bull" ? "📈" : s === "bear" ? "📉" : "➡️";
      const label = { bull: "Bull — thị trường tăng", bear: "Bear — thị trường giảm", neutral: "Trung tính" }[s] || s;
      html += `<div class="bp-sec">Regime</div>
        <div class="bp-regime ${s}">${icon} ${label}${st.regime.note ? ` — ${esc(st.regime.note)}` : ""}</div>`;
    }

    // Top screen
    if (st.top_screen && st.top_screen.length) {
      html += `<div class="bp-sec">Top màn lọc</div><table class="bp-table"><thead><tr>
        <th>Mã</th><th>Điểm</th><th>Giá</th><th>20 phiên</th><th>Tín hiệu</th>
      </tr></thead><tbody>` +
        st.top_screen.map(t => `<tr>
          <td><b>${esc(t.symbol)}</b></td>
          <td class="score ${t.tone}">${t.score}</td>
          <td>${fmt(t.close, 1)}</td>
          <td class="${cls(t.r20)}">${t.r20 != null ? sign(t.r20, 1) + "%" : "—"}</td>
          <td>${esc(t.verdict || "")}</td>
        </tr>`).join("") + `</tbody></table>`;
    }

    // Portfolio
    if (st.portfolio) {
      const p = st.portfolio;
      html += `<div class="bp-sec">Danh mục (${p.count} mã)</div>
        <div class="bp-port">
          <span>GTHT: <b>${fmt(p.total_value, 0)}</b></span>
          <span class="${cls(p.total_pl)}">P&L: <b>${sign(p.total_pl, 0)}</b> (${p.total_pl_pct != null ? sign(p.total_pl_pct, 1) + "%" : "—"})</span>
        </div>`;
    }

    // Upcoming events
    if (st.upcoming_events && st.upcoming_events.length) {
      html += `<div class="bp-sec">Sự kiện sắp tới</div><ul class="bp-events">` +
        st.upcoming_events.map(e => `<li>
          <span class="bp-ev-ico">${EV_ICONS[e.category] || "📅"}</span>
          <span class="bp-ev-date">${e.date}</span>
          <span class="bp-ev-sym">${esc(e.symbol)}</span>
          <span class="bp-ev-title">${esc(e.title)}</span>
        </li>`).join("") + `</ul>`;
    }

    // Alerts
    if (st.alert_count) {
      html += `<div class="bp-alerts">🔔 ${st.alert_count} alert chưa đọc — bấm 🔔 để xem</div>`;
    }

    if (!html) html = `<div class="empty">Chưa có dữ liệu cache. Chạy màn lọc trước.</div>`;
    body.innerHTML = html;
  }

  /* ---------------- panel ---------------- */
  function initPanel() {
    const btn = $("#btnBrief");
    const panel = $("#briefPanel");
    const close = $("#btnCloseBrief");
    const refresh = $("#btnRefreshBrief");
    if (!btn || !panel) return;
    btn.addEventListener("click", () => {
      panel.hidden = !panel.hidden;
      if (!panel.hidden) loadBrief();
    });
    if (close) close.addEventListener("click", () => { panel.hidden = true; });
    if (refresh) refresh.addEventListener("click", loadBrief);
  }

  document.addEventListener("DOMContentLoaded", initPanel);
})();
