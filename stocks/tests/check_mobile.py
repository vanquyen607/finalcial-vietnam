# -*- coding: utf-8 -*-
"""Test mobile 390x844: khong trang ngang, toolbar/bang/detail OK, anh chi tiet."""
import sys
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
    pg = b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE, wait_until="domcontentloaded")
    pg.wait_for_selector("#cards .card .big", timeout=30000)

    # khong trang ngang (body)
    sw = pg.evaluate("document.documentElement.scrollWidth")
    check("không tràn ngang trang", sw <= 395, f"scrollWidth={sw}")

    # toolbar vẫn thấy chip
    check("toolbar thấy chip sort", pg.locator("#sortChips .chip-btn").first.is_visible())
    check("toolbar thấy chip lọc", pg.locator("#filterChips .chip-btn").first.is_visible())

    # bảng: cột phụ (20 phiên, KL/20) ẩn trên mobile cho gọn; cột chính vẫn thấy
    hidden = pg.evaluate(
        "() => [...document.querySelectorAll('table.tbl thead th')]"
        ".filter(th => getComputedStyle(th).display === 'none').map(th => th.textContent.trim())"
    )
    check("ẩn cột phụ (20 phiên, KL/20) trên mobile", set(hidden) == {"20 phiên", "KL/20"}, str(hidden))
    check("cột Tín hiệu vẫn hiển thị", pg.locator("table.tbl thead th").last.is_visible())

    # mở mã bằng ô search (dùng JS vì nút có thể need scroll)
    pg.fill("#symInput", "HPG")
    pg.press("#symInput", "Enter")
    pg.wait_for_selector(".d-head .name", timeout=60000)
    check("detail hiện HPG", pg.locator(".d-head .name").inner_text() == "HPG")

    # plan grid 2 cột trên mobile
    cols = pg.evaluate("getComputedStyle(document.querySelector('.plan')).gridTemplateColumns")
    check(".plan 2 cột", len(cols.split()) == 2, cols)

    # #detail không cuộn lồng (max-height none)
    mh = pg.evaluate("getComputedStyle(document.querySelector('#detail')).maxHeight")
    check("#detail max-height none (cuộn trang tự nhiên)", mh == "none", mh)

    # topbar: clock ẩn, nút chính vẫn thấy
    check("clock ẩn trên mobile", not pg.locator("#clock").is_visible())
    check("nút Chạy màn lọc vẫn thấy", pg.locator("#btnRunScreen").is_visible())

    # không tràn sau khi có detail
    sw2 = pg.evaluate("document.documentElement.scrollWidth")
    check("không tràn sau khi mở mã", sw2 <= 395, f"scrollWidth={sw2}")

    check("không pageerror", len(errs) == 0, "; ".join(errs[:3]))

    pg.screenshot(path=str(SHOTS / "m1_mobile_top.png"), full_page=False)
    pg.evaluate("window.scrollTo(0, 700)")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(SHOTS / "m2_mobile_detail.png"), full_page=False)
    b.close()

print("\n===> KET QUA:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
sys.exit(1 if fails else 0)
