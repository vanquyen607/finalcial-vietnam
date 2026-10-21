/* Trợ lý AI hỏi đáp theo mã — panel nổi ở góc màn hình, gọi /api/symbol/{sym}/ask. */
const AI_CHIPS = [
  "Vì sao điểm này?",
  "Rủi ro chính là gì?",
  "So với peers thế nào?",
  "Kế hoạch vào lệnh có hợp lý không?",
];
const aiBusySyms = new Set();
let aiSym = null;

const aiEl = (id) => document.getElementById(id);

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

function aiFmt(s) {
  return esc(s)
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/\*([^*]{1,400})\*/g, "<i>$1</i>")
    .replace(/^\s*[*-]\s+/gm, "• ");
}

function aiBubble(m) {
  const body = m.role === "ai" ? aiFmt(m.text) : esc(m.text);
  return `<div class="ai-msg ${m.role}"><div class="ai-who">${m.role === "user" ? "Bạn" : "AI"}</div>` +
    `<div class="ai-text">${body}</div></div>`;
}

function aiRenderChips() {
  const chips = aiEl("aiChips");
  if (!chips) return;
  chips.innerHTML = AI_CHIPS.map((q) =>
    `<button type="button" class="ai-chip" data-q="${esc(q)}">${esc(q)}</button>`).join("");
  chips.querySelectorAll(".ai-chip").forEach((b) => {
    b.onclick = () => {
      const input = aiEl("aiInput");
      if (!input || !aiSym) return;
      input.value = b.dataset.q;
      input.focus();
    };
  });
}

function aiRenderLog() {
  const log = aiEl("aiLog");
  if (!log) return;
  if (!aiSym) {
    log.innerHTML = `<div class="ai-empty">Chọn một mã trong bảng hoặc mở form chi tiết, rồi bấm Hỏi AI.</div>`;
    return;
  }
  const h = aiHistory(aiSym);
  log.innerHTML = h.length
    ? h.map(aiBubble).join("")
    : `<div class="ai-empty">Hỏi nhanh về ${esc(aiSym)} — dữ liệu lấy từ cache của app.</div>`;
  log.scrollTop = log.scrollHeight;
}

function aiSyncHead() {
  const t = aiEl("aiTitle");
  const input = aiEl("aiInput");
  const send = aiEl("aiSend");
  if (t) t.textContent = aiSym ? `Hỏi AI · ${aiSym}` : "Hỏi AI";
  if (input) {
    input.placeholder = aiSym ? `Hỏi về ${aiSym}… (VD: rủi ro chính là gì?)` : "Chọn một mã để hỏi…";
    input.disabled = !aiSym;
  }
  if (send) send.disabled = !aiSym;
  const fab = aiEl("aiFab");
  if (fab) fab.title = aiSym ? `Hỏi AI về ${aiSym}` : "Chọn một mã để hỏi AI";
}

function setAISymbol(sym) {
  if (!sym) return;
  aiSym = sym;
  aiSyncHead();
  aiRenderLog();
}

function aiOpen(open, focus) {
  const panel = aiEl("aiPanel");
  const fab = aiEl("aiFab");
  if (!panel || !fab) return;
  panel.hidden = !open;
  fab.setAttribute("aria-expanded", String(open));
  fab.classList.toggle("open", open);
  try { localStorage.setItem("ck_ai_open", open ? "1" : "0"); } catch (e) {}
  if (!open) return;
  aiSyncHead();
  aiRenderLog();
  if (focus && aiSym) {
    const input = aiEl("aiInput");
    if (input) setTimeout(() => input.focus(), 30);
  }
}

async function aiSubmit() {
  const input = aiEl("aiInput");
  const sym = aiSym;
  const q = (input && input.value ? input.value : "").trim();
  if (!sym || !q || aiBusySyms.has(sym)) return;

  aiBusySyms.add(sym);
  const send = aiEl("aiSend");
  if (send) send.disabled = true;
  input.value = "";
  aiPush(sym, "user", q);
  aiRenderLog();

  const log = aiEl("aiLog");
  if (log) {
    log.insertAdjacentHTML("beforeend",
      `<div class="ai-msg ai pending" id="aiPending_${sym}"><div class="ai-who">AI</div>` +
      `<div class="ai-text"><span class="spinner"></span> Đang trả lời… (có thể 20–40 giây)</div></div>`);
    log.scrollTop = log.scrollHeight;
  }

  try {
    const st = await api(`/api/symbol/${encodeURIComponent(sym)}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    if (st.status !== "ready") throw new Error(st.message || "AI chưa trả lời được");
    aiPush(sym, "ai", st.answer);
  } catch (e) {
    if (aiSym === sym) toast(e.message || "Lỗi AI", "err");
  } finally {
    aiBusySyms.delete(sym);
    const pend = document.getElementById(`aiPending_${sym}`);
    if (pend) pend.remove();
    if (aiSym === sym) {
      aiRenderLog();
      if (send) send.disabled = false;
    }
  }
}

function aiInit() {
  const fab = aiEl("aiFab");
  const panel = aiEl("aiPanel");
  if (!fab || !panel) return;

  fab.onclick = () => aiOpen(panel.hidden, true);
  aiEl("aiClose").onclick = () => aiOpen(false);
  aiEl("aiClear").onclick = () => {
    if (!aiSym) return;
    try { localStorage.removeItem(aiKey(aiSym)); } catch (e) {}
    aiRenderLog();
  };
  aiEl("aiForm").onsubmit = (ev) => { ev.preventDefault(); aiSubmit(); };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) aiOpen(false);
  });

  aiSyncHead();
  aiRenderChips();
  aiRenderLog();

  let wasOpen = false;
  try { wasOpen = localStorage.getItem("ck_ai_open") === "1"; } catch (e) {}
  if (wasOpen) aiOpen(true, false);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", aiInit);
} else {
  aiInit();
}
