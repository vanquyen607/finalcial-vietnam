/* Trợ lý AI hỏi đáp theo mã — gọi /api/symbol/{sym}/ask (Gemini, key ở server). */
const AI_CHIPS = [
  "Vì sao điểm này?",
  "Rủi ro chính là gì?",
  "So với peers thế nào?",
  "Kế hoạch vào lệnh có hợp lý không?",
];
const aiBusySyms = new Set();

function aiKey(sym) { return "ck_ai_" + sym; }

function aiHistory(sym) {
  try {
    const a = JSON.parse(localStorage.getItem(aiKey(sym)) || "[]");
    return Array.isArray(a) ? a : [];
  } catch (e) { return []; }
}

function aiPush(sym, role, text) {
  const h = aiHistory(sym);
  h.push({ role, text, t: Date.now() });
  try { localStorage.setItem(aiKey(sym), JSON.stringify(h.slice(-16))); } catch (e) {}
}

function aiBubble(m) {
  return `<div class="ai-msg ${m.role}"><div class="ai-who">${m.role === "user" ? "Bạn" : "AI"}</div>` +
    `<div class="ai-text">${esc(m.text)}</div></div>`;
}

function aiRenderLog(sym) {
  const log = document.getElementById("aiLog");
  if (!log) return;
  log.innerHTML = aiHistory(sym).map(aiBubble).join("");
  log.scrollTop = log.scrollHeight;
}

function initAI(sym) {
  const box = document.getElementById("aiBox");
  if (!box) return;

  const chips = document.getElementById("aiChips");
  if (chips) {
    chips.innerHTML = AI_CHIPS.map((q) =>
      `<button type="button" class="ai-chip" data-q="${esc(q)}">${esc(q)}</button>`).join("");
    chips.querySelectorAll(".ai-chip").forEach((b) => {
      b.onclick = () => {
        const input = document.getElementById("aiInput");
        if (input) { input.value = b.dataset.q; input.focus(); }
      };
    });
  }

  const clear = document.getElementById("aiClear");
  if (clear) clear.onclick = () => {
    try { localStorage.removeItem(aiKey(sym)); } catch (e) {}
    aiRenderLog(sym);
  };

  aiRenderLog(sym);

  const form = document.getElementById("aiForm");
  const input = document.getElementById("aiInput");
  if (!form || !input) return;

  form.onsubmit = async (ev) => {
    ev.preventDefault();
    const q = (input.value || "").trim();
    if (!q || aiBusySyms.has(sym)) return;

    aiBusySyms.add(sym);
    const send = document.getElementById("aiSend");
    if (send) send.disabled = true;
    input.value = "";
    aiPush(sym, "user", q);
    aiRenderLog(sym);

    const log = document.getElementById("aiLog");
    if (log) {
      log.insertAdjacentHTML("beforeend",
        `<div class="ai-msg ai pending" id="aiPending"><div class="ai-who">AI</div>` +
        `<div class="ai-text"><span class="spinner"></span> Đang trả lời…</div></div>`);
      log.scrollTop = log.scrollHeight;
    }

    try {
      const st = await api(`/api/symbol/${encodeURIComponent(sym)}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (sym !== selectedSym) return;
      if (st.status !== "ready") throw new Error(st.message || "AI chưa trả lời được");
      aiPush(sym, "ai", st.answer);
      aiRenderLog(sym);
    } catch (e) {
      if (sym === selectedSym) toast(e.message || "Lỗi AI", "err");
    } finally {
      aiBusySyms.delete(sym);
      const pend = document.getElementById("aiPending");
      if (pend) pend.remove();
      const btn = document.getElementById("aiSend");
      if (btn) btn.disabled = false;
    }
  };
}
