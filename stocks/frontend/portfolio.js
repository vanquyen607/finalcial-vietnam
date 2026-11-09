/* Portfolio + P&L — CRUD, summary, allocation bar. */
"use strict";
(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function fmt(n, d = 0) {
    if (n == null || n !== n) return "—";
    return Number(n).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function sign(n, d = 1) { return (n > 0 ? "+" : "") + fmt(n, d); }
  function cls(n) { return n > 0 ? "up" : n < 0 ? "down" : "flat"; }

  const ALLOC_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
                        "#06b6d4", "#f97316", "#84cc16", "#ec4899", "#64748b"];

  async function loadPortfolio() {
    try {
      const st = await api("/api/me/portfolio");
      renderSummary(st);
      renderPositions(st.positions || []);
      renderAlloc(st.allocation || []);
    } catch (e) { /* ignore */ }
  }

  function renderSummary(st) {
    const box = $("#portSummary");
    if (!box) return;
    if (!st.count) { box.innerHTML = ""; return; }
    box.innerHTML = `
      <div class="pp-cell"><div class="pp-k">Tổng giá trị</div><div class="pp-v">${fmt(st.total_value)}</div></div>
      <div class="pp-cell"><div class="pp-k">Tổng vốn</div><div class="pp-v">${fmt(st.total_cost)}</div></div>
      <div class="pp-cell"><div class="pp-k">Lãi/Lỗ</div><div class="pp-v ${cls(st.total_pl)}">${sign(st.total_pl)} (${st.total_pl_pct != null ? sign(st.total_pl_pct, 1) + "%" : "—"})</div></div>`;
  }

  function parseNum(val) {
    if (!val) return NaN;
    // Chuẩn hóa: thay dấu phẩy thành dấu chấm nếu người dùng gõ theo kiểu VN (vd: 12,5)
    // Nếu có cả chấm và phẩy (vd: 125,000.5 hoặc 125.000,5)
    let s = String(val).trim();
    if (s.includes(",") && s.includes(".")) {
      if (s.lastIndexOf(",") > s.lastIndexOf(".")) {
        // Kiểu 125.000,5
        s = s.replace(/\./g, "").replace(",", ".");
      } else {
        // Kiểu 125,000.5
        s = s.replace(/,/g, "");
      }
    } else if (s.includes(",")) {
      s = s.replace(",", ".");
    }
    return parseFloat(s);
  }

  function renderPositions(items) {
    const box = $("#portPositions");
    if (!box) return;
    if (!items.length) { box.innerHTML = `<div class="empty">Chưa có vị thế nào.</div>`; return; }
    box.innerHTML = `<table class="pp-table"><thead><tr>
      <th>Mã</th><th>SL</th><th>GTBTC</th><th>Giá hiện tại</th><th>GTHT</th><th>P&L</th><th>%</th><th></th>
    </tr></thead><tbody>` +
      items.map(p => `<tr>
        <td><b>${esc(p.symbol)}</b></td>
        <td>${fmt(p.qty, Number.isInteger(p.qty) ? 0 : 2)}</td>
        <td>${fmt(p.avg_price, 1)}</td>
        <td>${fmt(p.close, 1)}</td>
        <td>${fmt(p.value)}</td>
        <td class="${cls(p.pl)}">${sign(p.pl)}</td>
        <td class="${cls(p.pl_pct)}">${p.pl_pct != null ? sign(p.pl_pct, 1) + "%" : "—"}</td>
        <td><button class="btn icon ghost pp-del" data-sym="${esc(p.symbol)}" title="Xoá">🗑</button></td>
      </tr>`).join("") +
      `</tbody></table>`;

    $$(".pp-del", box).forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm(`Xoá ${btn.dataset.sym} khỏi danh mục?`)) return;
        await api(`/api/me/portfolio/${encodeURIComponent(btn.dataset.sym)}`, { method: "DELETE" });
        loadPortfolio();
      });
    });
  }

  function renderAlloc(alloc) {
    const box = $("#portAlloc");
    if (!box) return;
    if (!alloc.length) { box.innerHTML = ""; return; }
    let html = `<div class="pp-alloc-label">Phân bổ</div><div class="pp-bar">`;
    alloc.forEach((a, i) => {
      html += `<span class="pp-seg" style="width:${a.weight}%;background:${ALLOC_COLORS[i % ALLOC_COLORS.length]}" title="${esc(a.symbol)} ${a.weight}%"></span>`;
    });
    html += `</div><div class="pp-legend">`;
    alloc.forEach((a, i) => {
      html += `<span class="pp-leg"><i style="background:${ALLOC_COLORS[i % ALLOC_COLORS.length]}"></i>${esc(a.symbol)} ${a.weight}%</span>`;
    });
    html += `</div>`;
    box.innerHTML = html;
  }

  /* ---------------- form ---------------- */
  function initForm() {
    const form = $("#portForm");
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const sym = ($("#portSym").value || "").toUpperCase().trim();
      const qty = parseNum($("#portQty").value);
      const price = parseNum($("#portPrice").value);
      if (!sym || isNaN(qty) || isNaN(price)) {
        alert("Vui lòng nhập số lượng và giá hợp lệ!");
        return;
      }
      if (qty <= 0 || price <= 0) {
        alert("Số lượng và giá phải lớn hơn 0!");
        return;
      }
      try {
        const r = await api("/api/me/portfolio", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol: sym, qty, avg_price: price })
        });
        if (r.status === "ok") {
          form.reset();
          loadPortfolio();
        } else if (r.message) {
          alert(r.message);
        }
      } catch (err) { alert("Lỗi: " + err.message); }
    });
  }

  /* ---------------- panel toggle ---------------- */
  function initPanel() {
    const btn = $("#btnPortfolio");
    const panel = $("#portPanel");
    const close = $("#btnClosePort");
    if (!btn || !panel) return;
    btn.addEventListener("click", () => {
      panel.hidden = !panel.hidden;
      if (!panel.hidden) loadPortfolio();
    });
    if (close) close.addEventListener("click", () => { panel.hidden = true; });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initPanel();
    initForm();
  });
})();
