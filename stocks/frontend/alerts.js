/* Alert panel — load rules + alerts, them/xoa rule, badge count. */
"use strict";
(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];

  let unread = 0;

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function fmtTs(ts) {
    if (!ts) return "—";
    const d = new Date(ts * 1000);
    return d.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }

  /* ---------------- fetch ---------------- */
  async function loadAlerts() {
    try {
      const st = await api("/api/alerts?limit=50");
      renderAlerts(st.alerts || []);
      unread = (st.alerts || []).filter(a => !a.read).length;
      updateBadge();
    } catch (e) { /* ignore */ }
  }

  async function loadRules() {
    try {
      const st = await api("/api/alerts/rules");
      renderRules(st.rules || []);
    } catch (e) { /* ignore */ }
  }

  function updateBadge() {
    const b = $("#alertBadge");
    if (!b) return;
    if (unread > 0) { b.hidden = false; b.textContent = unread > 99 ? "99+" : unread; }
    else b.hidden = true;
  }

  /* ---------------- render ---------------- */
  function renderAlerts(items) {
    const box = $("#apAlerts");
    if (!box) return;
    if (!items.length) { box.innerHTML = `<div class="empty">Chưa có alert nào.</div>`; return; }
    const ICONS = { price_above: "📈", price_below: "📉", volume_spike: "📊",
                    score_at_least: "⭐", rsi_above: "🔥", rsi_below: "🧊" };
    box.innerHTML = `<ul class="ap-list">` + items.map(a => `
      <li class="ap-item${a.read ? "" : " ap-unread"}">
        <span class="ap-ico">${ICONS[a.type] || "🔔"}</span>
        <div class="ap-content">
          <div class="ap-msg">${esc(a.message)}</div>
          <div class="ap-meta">${fmtTs(a.ts)} · ${esc(a.type)}</div>
        </div>
      </li>`).join("") + `</ul>`;
  }

  function renderRules(items) {
    const box = $("#apRules");
    if (!box) return;
    if (!items.length) { box.innerHTML = `<div class="empty">Chưa có quy tắc.</div>`; return; }
    const LABELS = {
      price_above: "Giá ≥", price_below: "Giá ≤", volume_spike: "KL ≥",
      score_at_least: "Điểm ≥", rsi_above: "RSI ≥", rsi_below: "RSI ≤"
    };
    box.innerHTML = `<ul class="ap-list">` + items.map(r => `
      <li class="ap-item" data-id="${esc(r.id)}">
        <div class="ap-content">
          <div class="ap-msg"><b>${esc(r.symbol)}</b> ${LABELS[r.type] || r.type} ${r.threshold}${r.note ? ` — ${esc(r.note)}` : ""}</div>
          <div class="ap-meta">${r.active ? "🟢 hoạt động" : "⏸暂停"}${r.last_triggered ? ` · lần cuối ${fmtTs(r.last_triggered)}` : ""}</div>
        </div>
        <button class="btn icon ghost ap-del" title="Xoá" aria-label="Xoá">🗑</button>
      </li>`).join("") + `</ul>`;

    $$(".ap-del", box).forEach(btn => {
      btn.addEventListener("click", async () => {
        const li = btn.closest(".ap-item");
        if (!li) return;
        await api(`/api/alerts/rules/${encodeURIComponent(li.dataset.id)}`, { method: "DELETE" });
        loadRules();
      });
    });
  }

  /* ---------------- add rule ---------------- */
  function initForm() {
    const form = $("#ruleForm");
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const sym = ($("#ruleSym").value || "").toUpperCase().trim();
      const type = $("#ruleType").value;
      const th = parseFloat($("#ruleTh").value);
      const note = ($("#ruleNote").value || "").trim();
      if (!sym || isNaN(th)) return;
      try {
        const r = await api("/api/alerts/rules", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol: sym, type, threshold: th, note })
        });
        if (r.status === "ok") {
          form.reset();
          loadRules();
          // chuyen tab sang Rules
          switchTab("apRules");
        } else if (r.message) {
          alert(r.message);
        }
      } catch (err) { alert("Lỗi: " + err.message); }
    });
  }

  /* ---------------- tabs & panel ---------------- */
  function switchTab(id) {
    $$(".ap-tab").forEach(t => t.classList.toggle("active", t.dataset.tab === id));
    ["apAlerts", "apRules", "apNewRule"].forEach(t => {
      const el = $("#" + t);
      if (el) el.hidden = t !== id;
    });
  }

  function initPanel() {
    const btn = $("#btnAlerts");
    const panel = $("#alertPanel");
    const close = $("#btnCloseAlerts");
    if (!btn || !panel) return;

    btn.addEventListener("click", () => {
      panel.hidden = !panel.hidden;
      if (!panel.hidden) { loadAlerts(); loadRules(); }
    });
    if (close) close.addEventListener("click", () => { panel.hidden = true; });

    $$(".ap-tab").forEach(t => {
      t.addEventListener("click", () => switchTab(t.dataset.tab));
    });

    const clearBtn = $("#btnClearAlerts");
    if (clearBtn) clearBtn.addEventListener("click", async () => {
      await api("/api/alerts/clear", { method: "POST" });
      unread = 0;
      updateBadge();
      loadAlerts();
    });
  }

  /* ---------------- poll ---------------- */
  function startPoll() {
    setInterval(loadAlerts, 120000); // 2 phut
  }

  document.addEventListener("DOMContentLoaded", () => {
    initPanel();
    initForm();
    loadAlerts();
    startPoll();
  });
})();
