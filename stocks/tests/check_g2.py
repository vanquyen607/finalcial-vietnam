# -*- coding: utf-8 -*-
"""Test Nhom 2: watchlist, CSV, phim mui ten, bao gia, so sanh 2 ma."""
import json, sys
from playwright.sync_api import sync_playwright
from pathlib import Path
SHOTS = Path(__file__).resolve().parent.parent / "_shots"
SHOTS.mkdir(exist_ok=True)

BASE = "http://127.0.0.1:8100"
fails = []

def check(name, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {extra}" if extra else ""))
    if not cond:
        fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#screenBody tr[data-sym]", timeout=30000)

    # ---------- 1. WATCHLIST ----------
    pg.fill("#symInput", "HPG")
    pg.press("#symInput", "Enter")
    pg.wait_for_selector(".d-head .price", timeout=60000)
    star = pg.locator("[data-star]")
    check("star ban đầu off", star.get_attribute("aria-pressed") == "false")
    star.click()
    check("star sau click = true", star.get_attribute("aria-pressed") == "true")
    check("class .on bật", "on" in (star.get_attribute("class") or ""))
    wl = pg.evaluate("JSON.parse(localStorage.getItem('ck_watch'))")
    check("ck_watch = ['HPG']", wl == ["HPG"], json.dumps(wl))
    sym_cell = pg.locator("#screenBody tr[data-sym='HPG'] .sym").inner_text()
    check("★ hiện trong bảng", "★" in sym_cell, sym_cell)
    pg.click("#filterChips .chip-btn[data-filter='mine']")
    pg.wait_for_timeout(300)
    n = pg.locator("#screenBody tr[data-sym]").count()
    check("filter Của tôi → đúng 1 dòng", n == 1, str(n))
    cnt = pg.locator("#rowCount").inner_text()
    check("rowCount 1/40", "1/40" in cnt, cnt)

    # reload → giữ cả filter lẫn watchlist
    pg.reload(wait_until="networkidle")
    pg.wait_for_selector("#screenBody tr[data-sym]", timeout=30000)
    check("filter mine giữ sau F5", pg.locator("#filterChips .chip-btn.on").get_attribute("data-filter") == "mine")
    wl = pg.evaluate("JSON.parse(localStorage.getItem('ck_watch'))")
    check("watchlist giữ sau F5", wl == ["HPG"], json.dumps(wl))
    check("★ giữ sau F5", "★" in pg.locator("#screenBody tr .sym").first.inner_text())

    # bỏ star
    pg.fill("#symInput", "HPG")
    pg.press("#symInput", "Enter")
    pg.wait_for_selector("[data-star]", timeout=60000)
    pg.locator("[data-star]").click()
    wl = pg.evaluate("JSON.parse(localStorage.getItem('ck_watch'))")
    check("unstar → danh sách rỗng", wl == [], json.dumps(wl))
    empty = pg.locator("#screenBody .empty").count()
    check("filter mine rỗng → thông báo", empty == 1)
    pg.click("#filterChips .chip-btn[data-filter='all']")
    pg.wait_for_timeout(300)

    # ---------- 2. ALERT GIÁ ----------
    res = pg.evaluate("""() => {
      const d = Object.assign({}, lastDetail, { close: lastDetail.stop * 0.97 });
      const n0 = document.querySelectorAll('.toast').length;
      checkAlerts(d);
      const msgs = [...document.querySelectorAll('.toast')].slice(n0).map(t => t.textContent);
      checkAlerts(d);
      const n1 = document.querySelectorAll('.toast').length;
      return { msgs, extra: n1 - (n0 + msgs.length) };
    }""")
    check("alert cắt lỗ bắn toast", any("cắt lỗ" in m for m in res["msgs"]), "; ".join(res["msgs"])[:90])
    check("không lặp lần gọi thứ 2", res["extra"] == 0, str(res["extra"]))

    # ---------- 3. EXPORT CSV ----------
    syms_before = pg.locator("#screenBody tr[data-sym]").evaluate_all("els => els.map(e => e.dataset.sym)")
    with pg.expect_download() as dl:
        pg.click("#btnCsv")
    f = dl.value
    txt = open(f.path(), encoding="utf-8-sig").read()
    lines = [l for l in txt.splitlines() if l.strip()]
    check("CSV có header", lines[0].startswith('"#"'), lines[0][:50])
    check("CSV đủ số dòng = bảng", len(lines) - 1 == len(syms_before), f"{len(lines)-1} vs {len(syms_before)}")
    first_csv = lines[1].split(",")[1].strip('"')
    check("dòng 1 CSV = dòng 1 bảng", first_csv == syms_before[0], f"{first_csv} vs {syms_before[0]}")
    check("tên tệp man_loc_*.csv", f.suggested_filename.startswith("man_loc_") and f.suggested_filename.endswith(".csv"), f.suggested_filename)

    # ---------- 4. PHÍM ↑↓ ----------
    idx = syms_before.index("HPG") if "HPG" in syms_before else -1
    if idx == -1 or idx + 1 >= len(syms_before):
        check("HPG có hàng xóm để test ↑↓", False, "index không hợp lệ")
    else:
        pg.evaluate("document.activeElement && document.activeElement.blur()")
        pg.keyboard.press("ArrowDown")
        pg.wait_for_timeout(200)
        sel = pg.locator("#screenBody tr.sel").get_attribute("data-sym")
        check("ArrowDown → mã kế", sel == syms_before[idx + 1], f"{sel} vs {syms_before[idx+1]}")
        pg.keyboard.press("ArrowUp")
        pg.wait_for_timeout(200)
        sel = pg.locator("#screenBody tr.sel").get_attribute("data-sym")
        check("ArrowUp → quay lại HPG", sel == "HPG", str(sel))

    # ---------- 5. SO SÁNH 2 MÃ ----------
    pg.wait_for_selector(".d-head .price", timeout=60000)
    check("btnCompare enabled", not pg.locator("#btnCompare").is_disabled())
    pg.click("#btnCompare")
    ph = pg.get_attribute("#symInput", "placeholder") or ""
    check("placeholder đổi khi bật so sánh", "so sánh với HPG" in ph, ph)
    check("nút hiện 'Hủy so sánh'", "Hủy so sánh" in pg.locator("#btnCompare").inner_text())
    pg.fill("#symInput", "FPT")
    pg.press("#symInput", "Enter")
    pg.wait_for_selector(".cmp-tbl", timeout=90000)
    head = pg.locator(".cmp-tbl thead").inner_text()
    check("header 2 cột HPG vs FPT", "HPG" in head and "FPT" in head, head.replace("\n", " "))
    nrows = pg.locator(".cmp-tbl tbody tr").count()
    check("đủ 17 tiêu chí", nrows == 17, str(nrows))
    check("hash giữ nguyên #HPG", (pg.evaluate("location.hash") or "").upper() == "#HPG", pg.evaluate("location.hash"))
    check("selectedSym vẫn HPG", pg.evaluate("selectedSym") == "HPG")
    pg.evaluate("document.getElementById('symInput').focus()")
    pg.keyboard.press("Escape")
    pg.wait_for_selector(".d-head .price", timeout=15000)
    check("Esc → về detail thường", pg.locator(".cmp-tbl").count() == 0)
    check("base vẫn HPG", pg.locator(".d-head .name").inner_text() == "HPG")
    check("nút về '⊕ So sánh'", "So sánh" in pg.locator("#btnCompare").inner_text() and "Hủy" not in pg.locator("#btnCompare").inner_text())
    ph2 = pg.get_attribute("#symInput", "placeholder") or ""
    check("placeholder khôi phục", "Tìm mã" in ph2, ph2)

    check("không pageerror", len(errs) == 0, "; ".join(errs[:3]))
    pg.screenshot(path=str(SHOTS / "g2_features.png"), full_page=False)
    b.close()

print("\n===> KET QUA:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
sys.exit(1 if fails else 0)
