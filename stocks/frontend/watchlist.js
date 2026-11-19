/* watchlist.js — Quản lý Watchlist per-user UI */
"use strict";
(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function fmt(n, d = 1) {
    if (n == null || n !== n) return "—";
    return Number(n).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
  }

  async function loadWatchlist() {
    const box = $("#watchlistContent");
    if (!box) return;
    const sess = localStorage.getItem("ck_session");
    if (!sess) {
      box.innerHTML = `<div class="empty">Vui lòng đăng nhập để lưu danh sách theo dõi.</div>`;
      return;
    }
    try {
      const res = await api("/api/me/watchlist");
      if (res && res.status === "ok") {
        renderWatchlist(res.watchlist || []);
      }
    } catch (e) {
      box.innerHTML = `<div class="err">Lỗi tải danh sách yêu thích.</div>`;
    }
  }

  function renderWatchlist(items) {
    const box = $("#watchlistContent");
    if (!box) return;
    if (!items.length) {
      box.innerHTML = `<div class="empty">Chưa có mã nào trong danh sách theo dõi.<br/>Thêm mã bằng form bên dưới hoặc bấm dấu ⭐ trên chi tiết cổ phiếu.</div>`;
      return;
    }

    box.innerHTML = `<table class="pp-table"><thead><tr>
      <th>Mã</th><th>Ghi chú</th><th>Giá mục tiêu</th><th>Hành động</th>
    </tr></thead><tbody>` +
      items.map(item => `<tr>
        <td><a href="#${esc(item.symbol)}" class="wl-link" style="color:var(--accent);font-weight:700;">${esc(item.symbol)}</a></td>
        <td><span class="meta">${esc(item.note || "—")}</span></td>
        <td>${item.price_target ? fmt(item.price_target) : "—"}</td>
        <td>
          <button class="btn icon ghost wl-del" data-sym="${esc(item.symbol)}" title="Bỏ theo dõi">🗑</button>
        </td>
      </tr>`).join("") +
      `</tbody></table>`;

    $$(".wl-del", box).forEach(btn => {
      btn.addEventListener("click", async () => {
        const sym = btn.dataset.sym;
        if (!confirm(`Xóa ${sym} khỏi danh sách theo dõi?`)) return;
        await toggleWatch(sym);
        loadWatchlist();
      });
    });

    $$(".wl-link", box).forEach(a => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const sym = a.textContent.trim();
        if (typeof openSymbol === "function") openSymbol(sym);
        $("#watchlistPanel").hidden = true;
      });
    });
  }

  window.updateWatchlistPanel = loadWatchlist;

  document.addEventListener("DOMContentLoaded", () => {
    const btn = $("#btnSideWatchlist");
    const panel = $("#watchlistPanel");
    const close = $("#btnCloseWatchlist");
    const form = $("#watchlistForm");

    if (btn && panel) {
      btn.addEventListener("click", () => {
        panel.hidden = !panel.hidden;
        if (!panel.hidden) loadWatchlist();
      });
    }

    if (close && panel) {
      close.addEventListener("click", () => { panel.hidden = true; });
    }

    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const sym = ($("#wlSym").value || "").toUpperCase().trim();
        const note = ($("#wlNote").value || "").trim();
        const target = $("#wlTarget").value ? parseFloat($("#wlTarget").value) : null;
        if (!sym) return;

        try {
          const res = await api("/api/me/watchlist", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol: sym, note, price_target: target })
          });
          if (res.status === "ok") {
            form.reset();
            toast(`Đã thêm ${sym} vào theo dõi!`, "ok");
            if (!watchList.includes(sym)) watchList.push(sym);
            loadWatchlist();
            if (typeof renderScreen === "function") renderScreen();
          }
        } catch (err) {
          alert("Lỗi: " + err.message);
        }
      });
    }
  });
})();

