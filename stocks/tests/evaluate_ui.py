# -*- coding: utf-8 -*-
import sys
import os
import time
import threading
from pathlib import Path

# Add stocks to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import uvicorn
from backend.main import app
from playwright.sync_api import sync_playwright

SHOTS_DIR = ROOT / "_shots" / "ui_eval"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)

class ServerThread(threading.Thread):
    def __init__(self, host="127.0.0.1", port=8188):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        config = uvicorn.Config(app=app, host=self.host, port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True

def main():
    port = 8188
    base_url = f"http://127.0.0.1:{port}"
    server_thread = ServerThread(port=port)
    server_thread.start()
    
    # Wait for server
    import urllib.request
    started = False
    for i in range(30):
        try:
            with urllib.request.urlopen(f"{base_url}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    started = True
                    break
        except Exception:
            time.sleep(0.3)
            
    if not started:
        print("[ERROR] Could not start backend server")
        server_thread.stop()
        sys.exit(1)
        
    print(f"[INFO] Server is healthy at {base_url}")
    
    results = {
        "console_errors": [],
        "page_errors": [],
        "checks": [],
        "metrics": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch()
        
        # ----------------- 1. DESKTOP DARK (1440x900) -----------------
        print("--- Testing Desktop Dark (1440x900) ---")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: results["page_errors"].append(f"[Desktop Dark] {e}"))
        page.on("console", lambda msg: results["console_errors"].append(f"[Desktop Dark] [{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
        
        page.goto(base_url, wait_until="domcontentloaded")
        page.wait_for_selector("#sec-overview .card", timeout=20000)
        page.wait_for_selector("#screenBody tr[data-sym]", timeout=20000)
        
        # Check initial overview
        card_count = page.locator("#sec-overview .card").count()
        results["checks"].append(("Desktop: Overview card count >= 4", card_count >= 4, f"count={card_count}"))
        
        # Check regime banner
        regime_visible = page.locator("#regimeBanner").is_visible()
        regime_text = page.locator("#regimeBanner").inner_text() if regime_visible else "Hidden"
        results["checks"].append(("Desktop: Regime banner visible", regime_visible, regime_text))
        
        # Check notice text
        notice_txt = page.locator("#noticeText").inner_text()
        results["checks"].append(("Desktop: Notice dynamic text", len(notice_txt) > 10, notice_txt[:60]))
        
        # Check table row count
        row_count = page.locator("#screenBody tr[data-sym]").count()
        results["checks"].append(("Desktop: Screen rows >= 30", row_count >= 30, f"rows={row_count}"))
        
        # Screenshot desktop overview
        page.screenshot(path=str(SHOTS_DIR / "desktop_dark_overview.png"), full_page=False)
        
        # Search and open HPG detail
        page.fill("#symInput", "HPG")
        page.press("#symInput", "Enter")
        page.wait_for_selector(".d-head .price", timeout=30000)
        page.wait_for_timeout(1000)
        
        # Check detail elements
        hpg_price = page.locator(".d-head .price").inner_text()
        has_chart = page.locator("#chart").is_visible()
        has_fund = page.locator(".fund .metric").count() >= 6
        has_plan = page.locator(".plan").is_visible()
        has_news = page.locator("#news").is_visible()
        
        results["checks"].append(("Desktop: HPG detail price loaded", bool(hpg_price), f"price={hpg_price}"))
        results["checks"].append(("Desktop: Chart container rendered", has_chart, ""))
        results["checks"].append(("Desktop: Fundamentals >= 6 metrics", has_fund, f"metrics={page.locator('.fund .metric').count()}"))
        results["checks"].append(("Desktop: Trading plan box visible", has_plan, ""))
        results["checks"].append(("Desktop: News box visible", has_news, ""))
        
        page.screenshot(path=str(SHOTS_DIR / "desktop_dark_detail_HPG.png"), full_page=False)
        
        # Test sidebar collapse
        page.click("#btnCollapseSide")
        page.wait_for_timeout(300)
        is_collapsed = page.locator("#sidebar").evaluate("el => el.classList.contains('collapsed')")
        results["checks"].append(("Desktop: Sidebar collapse works", is_collapsed, ""))
        page.click("#btnCollapseSide")
        page.wait_for_timeout(300)
        
        # Test Panels: Brief, Alerts, AI
        page.click("#btnBrief")
        page.wait_for_selector("#briefPanel:not([hidden])", timeout=5000)
        page.screenshot(path=str(SHOTS_DIR / "desktop_brief_panel.png"), full_page=False)
        page.click("#btnCloseBrief")
        
        page.click("#btnAlerts")
        page.wait_for_selector("#alertPanel:not([hidden])", timeout=5000)
        page.screenshot(path=str(SHOTS_DIR / "desktop_alerts_panel.png"), full_page=False)
        page.click("#btnCloseAlerts")
        
        page.click("#aiFab")
        page.wait_for_selector("#aiPanel:not([hidden])", timeout=5000)
        page.screenshot(path=str(SHOTS_DIR / "desktop_ai_panel.png"), full_page=False)
        page.click("#aiClose")
        
        # ----------------- 2. DESKTOP THEME TOGGLE -----------------
        print("--- Testing Desktop Theme Toggle ---", flush=True)
        t_before = page.locator("html").get_attribute("data-theme")
        page.click("#btnTheme")
        page.wait_for_timeout(400)
        t_after = page.locator("html").get_attribute("data-theme")
        theme_toggled = (t_before != t_after) and (t_after in ("light", "dark"))
        results["checks"].append(("Theme toggle switches between light and dark", theme_toggled, f"{t_before} -> {t_after}"))
        page.screenshot(path=str(SHOTS_DIR / "desktop_toggled_theme_HPG.png"), full_page=False)
        page.close()
        
        # ----------------- 3. MOBILE (390x844 iPhone 12) -----------------
        print("--- Testing Mobile Dark (390x844) ---")
        mpage = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mpage.on("pageerror", lambda e: results["page_errors"].append(f"[Mobile] {e}"))
        mpage.on("console", lambda msg: results["console_errors"].append(f"[Mobile] [{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
        
        mpage.goto(base_url, wait_until="domcontentloaded")
        mpage.wait_for_selector("#sec-overview .card", timeout=20000)
        mpage.wait_for_selector("#screenBody tr[data-sym]", timeout=20000)
        
        # Check horizontal overflow
        scroll_width = mpage.evaluate("document.documentElement.scrollWidth")
        results["checks"].append(("Mobile: No horizontal scroll (< 395px)", scroll_width <= 395, f"scrollWidth={scroll_width}"))
        
        mpage.screenshot(path=str(SHOTS_DIR / "mobile_dark_top.png"), full_page=False)
        
        # Open mobile sidebar drawer
        mpage.click("#btnSidebar")
        mpage.wait_for_timeout(300)
        sb_open = mpage.locator("#sidebar").evaluate("el => el.classList.contains('open')")
        results["checks"].append(("Mobile: Sidebar drawer opens", sb_open, ""))
        mpage.screenshot(path=str(SHOTS_DIR / "mobile_sidebar_drawer.png"), full_page=False)
        # Click on right side of screen outside 240px drawer to dismiss
        mpage.mouse.click(320, 300)
        mpage.wait_for_timeout(300)
        sb_closed = not mpage.locator("#sidebar").evaluate("el => el.classList.contains('open')")
        results["checks"].append(("Mobile: Sidebar drawer closes on tap outside", sb_closed, ""))
        
        # Open HPG on mobile
        mpage.fill("#symInput", "HPG")
        mpage.press("#symInput", "Enter")
        mpage.wait_for_selector(".d-head .price", timeout=30000)
        mpage.wait_for_timeout(500)
        
        scroll_width_detail = mpage.evaluate("document.documentElement.scrollWidth")
        results["checks"].append(("Mobile: No horizontal scroll with detail", scroll_width_detail <= 395, f"scrollWidth={scroll_width_detail}"))
        
        mpage.screenshot(path=str(SHOTS_DIR / "mobile_detail_hpg.png"), full_page=False)
        
        # Scroll down to chart and plan
        mpage.evaluate("window.scrollTo(0, 500)")
        mpage.wait_for_timeout(300)
        mpage.screenshot(path=str(SHOTS_DIR / "mobile_detail_chart_plan.png"), full_page=False)
        
        mpage.close()
        browser.close()

    import json
    eval_report_path = SHOTS_DIR / "report.json"
    with open(eval_report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Report written to {eval_report_path}", flush=True)
    server_thread.stop()
    
    print("\n================ EVALUATION SUMMARY ================")
    pass_count = sum(1 for _, ok, _ in results["checks"] if ok)
    fail_count = len(results["checks"]) - pass_count
    print(f"Total Checks: {len(results['checks'])} | Passed: {pass_count} | Failed: {fail_count}")
    for name, ok, extra in results["checks"]:
        clean_extra = extra.encode('ascii', errors='replace').decode('ascii')
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} {('('+clean_extra+')') if extra else ''}")
        
    print(f"\nPage Errors: {len(results['page_errors'])}")
    for pe in results["page_errors"]:
        print(f"  - {pe}")
        
    print(f"\nConsole Errors & Warnings: {len(results['console_errors'])}")
    for ce in results["console_errors"][:15]:
        clean_ce = ce.encode('ascii', errors='replace').decode('ascii')
        print(f"  - {clean_ce}")
        
    print(f"\nScreenshots saved to: {SHOTS_DIR}")

if __name__ == "__main__":
    main()
