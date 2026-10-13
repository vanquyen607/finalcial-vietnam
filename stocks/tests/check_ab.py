# -*- coding: utf-8 -*-
"""Test A1 (Co ban) + cum B (UPCOM, breadth, dong tien ngoai)."""
import sys
from playwright.sync_api import sync_playwright
from pathlib import Path
SHOTS = Path(__file__).resolve().parent.parent / "_shots"
SHOTS.mkdir(exist_ok=True)

BASE = "http://127.0.0.1:8100"
fails = []

def check(name, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {extra}" if extra else ""), flush=True)
    if not cond:
        fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#screenBody tr[data-sym]", timeout=30000)

    # ---------- 1. OVERVIEW 3 CHI SO (gồm UPCOM) ----------
    pg.click("#btnRefreshOverview")
    try:
        pg.wait_for_function(
            "() => document.querySelectorAll('#cards .card').length >= 4"
            " && document.querySelector('#cards').innerText.includes('UPCOM')",
            timeout=120000)
        ok3 = True
    except Exception:
        ok3 = False
    cards = pg.locator("#cards .card").count()
    check("overview >= 4 the (3 chi so + meta)", cards >= 4, str(cards))
    ctxt = pg.locator("#cards").inner_text().lower()   # CSS text-transform -> innerText hoa
    check("co the UPCOM-Index", "upcom-index" in ctxt)
    check("MA200 UPCOM khong phai NaN", "nan" not in ctxt)

    # ---------- 2. BREADTH CARD ----------
    br = pg.locator("#breadthCard")
    hidden = br.get_attribute("hidden") is not None
    if hidden:
        bst = pg.evaluate("fetch('/api/breadth').then(r => r.json()).then(x => x.status)")
        check("breadth an truoc gio mo cua + status hop ly", bst in ("empty", "fetching", "ready", "error"), str(bst))
        print("[SKIP] breadth rows (ngoai gio giao dich)")
    else:
        rows = br.locator(".br-row").count()
        check("breadth hien >= 1 dong san", rows >= 1, str(rows))
        check("breadth co cot GTGD", "tỷ GTGD" in br.inner_text())

    # ---------- 3. FA (CHI SO CO BAN) TRONG DETAIL ----------
    pg.fill("#symInput", "HPG")
    pg.press("#symInput", "Enter")
    pg.wait_for_selector(".d-head .price", timeout=60000)
    pg.wait_for_selector(".fund .metric", timeout=45000)
    n = pg.locator(".fund .metric").count()
    check("fund >= 6 chi tieu", n >= 6, str(n))
    ftxt = pg.locator(".fund").inner_text().lower()
    for lab in ("p/e", "p/b", "eps ttm", "roe ttm", "beta"):
        check(f"fund co {lab}", lab in ftxt)
    check("fund khong NaN", "nan" not in ftxt)

    # fund khong block phan tich ky thuat
    check("detail van co plan vung lenh", pg.locator(".plan .cell.k").count() == 1)
    check("detail van co RSI", "RSI" in pg.locator(".metrics").first.inner_text())

    # fund cache sau khi doi ma (khong refetch)
    st1 = pg.evaluate("fetch('/api/symbol/VCB/fundamentals').then(r=>r.json()).then(x=>x.status)")
    check("fund VCB endpoint ready", st1 == "ready", str(st1))

    pg.fill("#symInput", "VCB")
    pg.press("#symInput", "Enter")
    pg.wait_for_selector(".fund .metric", timeout=45000)
    vtxt = pg.locator(".fund").inner_text()
    check("doi ma VCB → fund cung render", "p/e" in vtxt.lower(), vtxt[:80].replace("\n", " "))

    # ---------- 4. MOBILE (dong desktop truoc de khong tranh paced) ----------
    pg.screenshot(path=str(SHOTS / "ab_desktop.png"), full_page=False)
    pg.close()
    m = b.new_page(viewport={"width": 390, "height": 844})
    merrs = []
    m.on("pageerror", lambda e: merrs.append(str(e)))
    m.goto(BASE, wait_until="domcontentloaded")   # networkidle treo khi server dang ban paced
    m.wait_for_selector("#screenBody tr[data-sym]", timeout=30000)
    m.fill("#symInput", "FPT")
    m.press("#symInput", "Enter")
    m.wait_for_selector(".d-head .price", timeout=90000)
    try:
        m.wait_for_selector(".fund .metric", timeout=90000)
        mob_ok = True
    except Exception:
        mob_ok = False
    check("mobile: fund >= 6 chi tieu", mob_ok and m.locator(".fund .metric").count() >= 6)

    check("khong co pageerror (desktop)", len(errs) == 0, "; ".join(errs[:3]))
    check("khong co pageerror (mobile)", len(merrs) == 0, "; ".join(merrs[:3]))

    m.screenshot(path=str(SHOTS / "ab_mobile.png"), full_page=False)
    b.close()

print("ALL PASS" if not fails else ("FAILED: %d — %s" % (len(fails), fails)), flush=True)
sys.exit(1 if fails else 0)
