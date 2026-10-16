# -*- coding: utf-8 -*-
"""Test Nhom 1: a11y, ngay dd/mm/yyyy, sort/filter persist, so tin, loi than thien, notice dong, font size."""
import re, sys
from playwright.sync_api import sync_playwright
from pathlib import Path
SHOTS = Path(__file__).resolve().parent.parent / "_shots"
SHOTS.mkdir(exist_ok=True)

BASE = "http://127.0.0.1:8100"
fails = []

def check(name, cond, extra=""):
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name}" + (f" — {extra}" if extra else ""))
    if not cond:
        fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE, wait_until="domcontentloaded")

    # 1. a11y cơ bản
    check("skip-link tồn tại", pg.locator("a.skip[href='#main']").count() == 1)
    check("main có id=main", pg.locator("main#main").count() == 1)

    # 2. notice động (chờ overview xong)
    pg.wait_for_selector("#cards .card .big", timeout=30000)
    pg.wait_for_timeout(500)
    nt = pg.locator("#noticeText").inner_text()
    check("noticeText động", nt.startswith("Thị trường") and "giải ngân từng phần" in nt, nt[:70])
    check("câu rate-limit vẫn còn", "20 req/phút" in pg.locator("#notice .n-txt").inner_text())

    # 3. ngày dd/mm/yyyy ở card
    label = pg.locator("#cards .card .label").first.inner_text()
    check("card date dd/mm/yyyy", bool(re.search(r"phiên \d{2}/\d{2}/\d{4}", label, re.I)), label)

    # 4. sort/filter persist: chọn Giá + Tránh → reload → giữ nguyên
    pg.click("#sortChips .chip-btn[data-sort='close']")
    pg.click("#filterChips .chip-btn[data-filter='bad']")
    pg.wait_for_timeout(300)
    pg.reload(wait_until="domcontentloaded")
    pg.wait_for_selector("#screenBody tr[data-sym]", timeout=30000)
    sort_on = pg.locator("#sortChips .chip-btn.on").get_attribute("data-sort")
    arr_txt = pg.locator("#sortChips .chip-btn.on .arr").inner_text()
    filt_on = pg.locator("#filterChips .chip-btn.on").get_attribute("data-filter")
    check("sort Giữ sau F5", sort_on == "close" and arr_txt == "▼", f"{sort_on} {arr_txt}")
    check("filter Tránh giữ sau F5", filt_on == "bad", str(filt_on))
    th_sort = pg.locator("th[data-sort='close']").get_attribute("aria-sort")
    check("header aria-sort đồng bộ", th_sort == "descending", str(th_sort))
    # giá trị cột giá phải tăng dần (sort asc? dir=-1 desc → giá giảm dần). Kiểm tra bất kỳ thứ tự hợp lệ
    vals = pg.locator("#screenBody tr td:nth-child(3)").all_inner_texts()
    nums = [float(v.replace(".", "").replace(",", ".")) for v in vals[:10]]
    check("bảng sort đúng (desc)", nums == sorted(nums, reverse=True), str(nums[:5]))
    # reset về mặc định cho các test sau
    pg.click("#filterChips .chip-btn[data-filter='all']")
    pg.click("#sortChips .chip-btn[data-sort='score']")
    pg.wait_for_timeout(200)

    # 5. mở mã: ngày detail, aria-selected, số tin, aria-expanded, font size
    pg.fill("#symInput", "HPG")
    pg.press("#symInput", "Enter")
    pg.wait_for_selector(".d-head .name", timeout=60000)
    ddate = pg.locator(".d-head .date").inner_text()
    check("detail date dd/mm/yyyy", bool(re.search(r"phiên \d{2}/\d{2}/\d{4}", ddate)), ddate)
    sel = pg.locator("#screenBody tr[data-sym='HPG']").first
    check("aria-selected=true", sel.get_attribute("aria-selected") == "true")
    pg.wait_for_selector("#news h4", timeout=30000)
    nh = pg.locator("#news h4").inner_text()
    check("tiêu đề tin có số lượng", bool(re.search(r"·\s*\d+\s*tin", nh, re.I)), nh)
    if pg.locator(".news-more").count():
        check("aria-expanded trên nút tin",
              pg.locator(".news-more").get_attribute("aria-expanded") in ("false", "true"))
    else:
        # news chưa xong render → chờ lại
        pg.wait_for_selector(".news-more", timeout=15000)
        check("aria-expanded trên nút tin",
              pg.locator(".news-more").get_attribute("aria-expanded") == "false")
    ksize = pg.evaluate("getComputedStyle(document.querySelector('.metric .k')).fontSize")
    check(".metric .k = 11px", ksize == "11px", ksize)
    klabel = pg.evaluate("getComputedStyle(document.querySelector('.plan .k-label')).fontSize")
    check(".plan .k-label = 11px", klabel == "11px", klabel)
    tagsz = pg.evaluate("getComputedStyle(document.querySelector('.verdict-line .big-tag')).fontSize")
    # .tag dùng cho bảng; test trực tiếp .tag trong bảng
    rowsz = pg.evaluate("getComputedStyle(document.querySelector('#screenBody .tag')).fontSize")
    check(".tag = 11px", rowsz == "11px", rowsz)

    # 6. lỗi API thân thiện (abort → mất kết nối)
    pg.route("**/api/session", lambda r: r.abort())
    msg = pg.evaluate("async () => { try { await api('/api/session'); return 'OK'; } catch(e){ return e.message; } }")
    pg.unroute("**/api/session")
    check("abort → 'Mất kết nối máy chủ'", msg == "Mất kết nối máy chủ", msg)
    # 500 → thân thiện (route fulfill 500)
    pg.route("**/api/session", lambda r: r.fulfill(status=500, body="{}"))
    msg2 = pg.evaluate("async () => { try { await api('/api/session'); return 'OK'; } catch(e){ return e.message; } }")
    pg.unroute("**/api/session")
    check("500 → 'Máy chủ đang bận'", "Máy chủ đang bận" in msg2, msg2)

    # 7. không lỗi JS
    check("không có pageerror", len(errs) == 0, "; ".join(errs[:3]))

    pg.screenshot(path=str(SHOTS / "g1_desktop.png"), full_page=False)
    b.close()

print("\n===> KET QUA:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
sys.exit(1 if fails else 0)
