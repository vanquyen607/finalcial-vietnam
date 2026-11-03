import sys
import time
import threading
import urllib.request
from pathlib import Path

ROOT = Path(r"d:\Desktop\finan\gold")
sys.path.insert(0, str(ROOT / "backend"))

import uvicorn
from app.main import app
from playwright.sync_api import sync_playwright

SHOTS_DIR = ROOT / "_shots" / "ui_eval"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)

class ServerThread(threading.Thread):
    def __init__(self, host="127.0.0.1", port=8199):
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
    port = 8199
    base_url = f"http://127.0.0.1:{port}"
    server_thread = ServerThread(port=port)
    server_thread.start()

    started = False
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{base_url}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    started = True
                    break
        except Exception:
            time.sleep(0.3)

    if not started:
        print("[ERROR] Could not start gold backend server")
        server_thread.stop()
        sys.exit(1)

    print(f"[INFO] Server is healthy at {base_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Desktop
        print("--- Testing Gold Desktop (1440x900) ---")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base_url, wait_until="domcontentloaded")
        page.wait_for_selector(".topbar", timeout=15000)

        # Check initial theme
        t0 = page.locator("html").get_attribute("data-theme")
        print(f"Initial theme: {t0}")
        page.screenshot(path=str(SHOTS_DIR / "gold_desktop_dark.png"), full_page=False)

        # Toggle theme
        page.click(".btn-theme-toggle")
        page.wait_for_timeout(300)
        t1 = page.locator("html").get_attribute("data-theme")
        print(f"Theme after toggle: {t1}")
        assert t0 != t1, "Theme did not change!"
        page.screenshot(path=str(SHOTS_DIR / "gold_desktop_light.png"), full_page=False)

        # Mobile
        print("--- Testing Gold Mobile (390x844) ---")
        mpage = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mpage.goto(base_url, wait_until="domcontentloaded")
        mpage.wait_for_selector(".topbar", timeout=15000)

        sw = mpage.evaluate("document.documentElement.scrollWidth")
        print(f"Mobile scrollWidth: {sw}")
        assert sw <= 395, f"Mobile horizontal scroll overflow: {sw}px"

        mpage.screenshot(path=str(SHOTS_DIR / "gold_mobile_dark.png"), full_page=False)
        mpage.click(".btn-theme-toggle")
        mpage.wait_for_timeout(300)
        t_mobile = mpage.locator("html").get_attribute("data-theme")
        print(f"Mobile theme after toggle: {t_mobile}")
        mpage.screenshot(path=str(SHOTS_DIR / "gold_mobile_light.png"), full_page=False)

        # Settings page test
        print("--- Testing Settings Page ---")
        page.goto(f"{base_url}/settings", wait_until="domcontentloaded")
        page.wait_for_selector(".panel", timeout=15000)
        page.screenshot(path=str(SHOTS_DIR / "gold_settings.png"), full_page=False)

        browser.close()

    server_thread.stop()
    print("[SUCCESS] All Gold UI tests passed!")

if __name__ == "__main__":
    main()

