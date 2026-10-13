/* Phan Tich Co Phieu VN — screen.js (tach tu app.js) */
/* ---------------- screen ---------------- */
async function loadScreen() {
  try {
    const st = await api("/api/screen");
    const auto = st.auto ? `auto · vòng #${st.cycles}` : "chạy 1 lần";
    if (st.status === "running" || st.running) {
      const pct = st.total ? Math.round((st.done / st.total) * 100) : 0;
      $("#screenBar").style.width = pct + "%";
      $("#screenMeta").textContent = `${st.done}/${st.total} · hiện tại: ${st.current || "…"} · ${auto}`;
      renderScreen(st.results || []);
      clearTimeout(pollTimers.screen);
      pollTimers.screen = setTimeout(loadScreen, 3000);
      return;
    }
    $("#screenBar").style.width = "100%";
    if (st.results && st.results.length) {
      const t = st.generated_at ? new Date(st.generated_at * 1000) : null;
      const src = st.source === "seed" ? " · mẫu, bấm Chạy màn lọc" : "";
      const nxt = st.auto && st.next_in ? ` · quét lại sau ${st.next_in}s` : "";
      $("#screenMeta").textContent = `${st.results.length} mã · ${t ? "lúc " + t.toLocaleTimeString("vi-VN") : ""} · ${auto}${nxt}${src}`;
      renderScreen(st.results);
    } else {
      $("#screenMeta").textContent = "chưa có dữ liệu — bấm Chạy màn lọc";
      $("#screenBody").innerHTML = `<tr><td colspan="8" class="empty">Chưa có dữ liệu. Bấm <b>Chạy màn lọc 40 mã</b> (lần đầu ~6 phút).</td></tr>`;
    }
    clearTimeout(pollTimers.screen);
    pollTimers.screen = setTimeout(loadScreen, 8000);
  } catch (e) {
    $("#screenMeta").textContent = "lỗi: " + e.message;
    clearTimeout(pollTimers.screen);
    pollTimers.screen = setTimeout(loadScreen, 15000);
  }
}

function renderTicker() {
  const el = $("#tickerTrack");
  if (!el || !screenRows.length) return;
  const withR5 = screenRows.filter((r) => typeof r.r5 === "number");
  if (!withR5.length) return;
  const gain = withR5.slice().sort((a, b) => b.r5 - a.r5).slice(0, 8);
  const lose = withR5.slice().sort((a, b) => a.r5 - b.r5).slice(0, 8);
  const items = [...gain, ...lose];
  const html = items.map((r) => `
    <span class="tk" title="${r.symbol}: đổi ${sign(r.r5, 1)}% trong 5 phiên">
      <b>${r.symbol}</b><span class="tk-p">${fmt(r.close, r.close < 50 ? 1 : 0)}</span>
      <span class="tk-c ${r.r5 >= 0 ? "up" : "down"}">${sign(r.r5, 1)}%</span>
    </span>`).join("");
  el.innerHTML = html + html;
}

/* dòng đang hiển thị = filter + sort (dùng cho render, ↑↓, CSV) */
function visibleRows() {
  return screenRows
    .filter((r) =>
      filterBy === "all" ? true :
      filterBy === "mine" ? inWatch(r.symbol) :
      r.tone === filterBy)
    .slice()
    .sort((a, b) => {
      const x = a[sortBy] ?? -Infinity, y = b[sortBy] ?? -Infinity;
      return (x < y ? -1 : x > y ? 1 : 0) * sortDir;
    });
}

function renderScreen(rows) {
  screenRows = rows || [];
  renderTicker();
  const rows2 = visibleRows();

  const body = $("#screenBody");
  $("#rowCount").textContent = rows2.length !== screenRows.length
    ? `${rows2.length}/${screenRows.length} mã`
    : (screenRows.length ? screenRows.length + " mã" : "");

  if (!rows2.length) {
    body.innerHTML = `<tr><td colspan="8" class="empty">${screenRows.length ? "Không có mã nào khớp bộ lọc." : "Chưa có dữ liệu."}</td></tr>`;
    return;
  }
  body.innerHTML = rows2
    .map((r, i) => {
      const tone = r.tone || "neutral";
      return `<tr data-sym="${r.symbol}" tabindex="0" class="${r.symbol === selectedSym ? "sel" : ""}"
        aria-selected="${r.symbol === selectedSym}">
        <td class="rank">${i + 1}</td>
        <td><span class="sym">${inWatch(r.symbol) ? '<span class="star-inline" title="Trong ⭐ Của tôi">★</span>' : ""}${r.symbol}</span></td>
        <td>${fmt(r.close, r.close < 50 ? 1 : 0)}</td>
        <td class="${cls(r.r20)}">${sign(r.r20, 1)}%</td>
        <td class="${r.rsi > 70 ? "down" : r.rsi < 30 ? "up" : ""}">${fmt(r.rsi, 0)}</td>
        <td>${fmt(r.vol_ratio, 2)}×</td>
        <td><span class="score ${tone}">${r.score}</span></td>
        <td><span class="tag ${tone}">${r.verdict}</span></td>
      </tr>`;
    })
    .join("");
  body.querySelectorAll("tr[data-sym]").forEach((tr) => {
    tr.addEventListener("click", () => openSymbol(tr.dataset.sym));
    tr.addEventListener("keydown", (e) => { if (e.key === "Enter") openSymbol(tr.dataset.sym); });
  });
}

async function runScreen() {
  const btn = $("#btnRunScreen");
  btn.disabled = true;
  try {
    await api("/api/screen/run", { method: "POST" });
    toast("Đã bắt đầu quét 40 mã — lần đầu ~6 phút", "ok");
    clearTimeout(pollTimers.screen);
    loadScreen();
  } catch (e) {
    toast("Không khởi động được màn lọc: " + e.message, "err");
  } finally {
    setTimeout(() => { btn.disabled = false; }, 1500);
  }
}

