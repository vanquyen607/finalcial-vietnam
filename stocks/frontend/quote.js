/* Giá gần realtime từ bảng giá VCI (miễn phí, không cần API key).
   Poll 5s trong phiên, 15s ngoài phiên, 60s khi tab ẩn. Chỉ cập nhật DOM,
   không đụng dữ liệu EOD (screenRows/lastDetail giữ nguyên để tính chỉ báo). */
window.QUOTES = window.QUOTES || {};

const QUOTE_MS_IN = 5000;
const QUOTE_MS_OUT = 15000;
const QUOTE_MS_HIDDEN = 60000;
let quoteTimer = null;
let quoteBusy = false;
let quoteMeta = { in_session: false, ts: 0, error: null };

function quoteSyms() {
  const set = new Set();
  if (selectedSym) set.add(selectedSym);
  (screenRows || []).forEach((r) => r && r.symbol && set.add(r.symbol));
  (watchList || []).forEach((s) => set.add(s));
  return [...set].filter((s) => /^[A-Z0-9]{2,6}$/.test(s)).slice(0, 60);
}

function quoteDelay() {
  if (document.hidden) return QUOTE_MS_HIDDEN;
  if (inSession && liveOn) return QUOTE_MS_IN;
  return QUOTE_MS_OUT;
}

function quoteFlash(el, q) {
  if (!el || !q || !q.price) return;
  const key = "qPrev";
  const prev = el.dataset[key] ? Number(el.dataset[key]) : null;
  el.dataset[key] = String(q.price);
  if (prev == null || prev === q.price) return;
  el.classList.remove("flash-up", "flash-down");
  void el.offsetWidth;
  el.classList.add(q.price > prev ? "flash-up" : "flash-down");
  setTimeout(() => el.classList.remove("flash-up", "flash-down"), 900);
}

function applyQuotes() {
  document.querySelectorAll("#screenBody tr[data-sym]").forEach((tr) => {
    const q = QUOTES[tr.dataset.sym];
    if (!q || !q.price) return;
    const cell = tr.querySelector("td.qp");
    if (!cell) return;
    if (cell.dataset.price !== String(q.price)) {
      cell.dataset.price = String(q.price);
      const chg = q.chg_pct == null
        ? ""
        : `<span class="q-chg ${cls(q.chg_pct)}">${sign(q.chg_pct, 1)}%</span>`;
      cell.innerHTML = fmt(q.price / 1000, q.price < 50000 ? 1 : 0) + chg;
      cell.title = q.chg_pct == null
        ? "Giá khớp VCI"
        : `Hôm nay ${sign(q.chg_pct, 1)}% (tham chiếu ${fmt(q.ref / 1000, 1)}) - nguồn VCI`;
    }
  });

  if (!lastDetail) return;
  const q = QUOTES[lastDetail.symbol];
  if (!q || !q.price) return;
  const px = document.querySelector("#detail [data-q-price]");
  if (px) {
    const txt = fmt(q.price / 1000, q.price < 50000 ? 1 : 0);
    if (px.textContent !== txt) {
      quoteFlash(px, q);
      px.textContent = txt;
    }
  }
  const day = document.querySelector("#detail [data-q-day]");
  if (day) {
    if (q.chg_pct == null) {
      day.textContent = "";
      day.className = "dchg q-day";
    } else {
      day.textContent = `hôm nay ${sign(q.chg_pct, 1)}%`;
      day.className = `dchg q-day ${cls(q.chg_pct)}`;
      day.title = `Giá khớp ${fmt(q.price / 1000, 1)} - tham chiếu ${fmt(q.ref / 1000, 1)} (VCI)`;
    }
  }
}

function quoteNext() {
  clearTimeout(quoteTimer);
  quoteTimer = setTimeout(loadQuotes, quoteDelay());
}

async function loadQuotes() {
  const syms = quoteSyms();
  if (!syms.length || quoteBusy) return quoteNext();
  quoteBusy = true;
  try {
    const r = await api("/api/quote?symbols=" + encodeURIComponent(syms.join(",")));
    if (r && Array.isArray(r.data)) {
      r.data.forEach((q) => { if (q && q.symbol) QUOTES[q.symbol] = q; });
      quoteMeta = { in_session: !!r.in_session, ts: r.ts || Date.now(), error: r.error || null };
      applyQuotes();
    }
  } catch (e) {
    quoteMeta.error = e.message;
  } finally {
    quoteBusy = false;
  }
  quoteNext();
}

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) loadQuotes();
});

loadQuotes();
