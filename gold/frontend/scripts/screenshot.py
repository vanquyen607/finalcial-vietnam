"""Chụp screenshot web UI bằng Edge (Playwright channel=msedge, không cần tải browser)."""
import os
import sys

from playwright.sync_api import sync_playwright

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "_shots"
)
BASE = "http://127.0.0.1:8000"
PAGES = [("home", "/"), ("chart", "/chart"), ("detail", "/detail/sjc"), ("alerts", "/alerts")]
VIEWPORTS = [("desktop", 1440, 900), ("laptop", 1280, 800), ("mobile", 390, 844)]


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        for vp_name, w, h in VIEWPORTS:
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
            for name, path in PAGES:
                page.goto(BASE + path, wait_until="networkidle")
                page.wait_for_timeout(2500)
                shot = os.path.join(OUT, f"{name}_{vp_name}.png")
                page.screenshot(path=shot, full_page=(vp_name != "mobile"))
                print("wrote", shot)
            ctx.close()
        browser.close()

    if errors:
        print("\n--- JS errors ---")
        for e in dict.fromkeys(errors):
            print(e)
    else:
        print("\nno JS/console errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
