# -*- coding: utf-8 -*-
"""Check nhanh CSV header sau sua."""
import sys
from playwright.sync_api import sync_playwright
from pathlib import Path
SHOTS = Path(__file__).resolve().parent.parent / "_shots"
SHOTS.mkdir(exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:8100", wait_until="networkidle")
    pg.wait_for_selector("#screenBody tr[data-sym]", timeout=30000)
    with pg.expect_download() as dl:
        pg.click("#btnCsv")
    f = dl.value
    first = open(f.path(), encoding="utf-8-sig").read().splitlines()[0]
    ok = first.startswith('"#"') and '"Tin hieu"' in first
    print(f"[{'PASS' if ok else 'FAIL'}] CSV header quoted — {first}")
    print(f"[{'PASS' if not errs else 'FAIL'}] no pageerror — {errs[:2]}")
    b.close()
    sys.exit(0 if ok and not errs else 1)
