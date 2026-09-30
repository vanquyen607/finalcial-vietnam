"""Xuất toàn bộ thiết kế từ một project Stitch (MCP remote) về thư mục local.

Usage:
    python stitch_export.py [project_id] [out_dir]

Đọc API key từ opencode.json (mcp.stitch.headers.X-Goog-Api-Key) hoặc env STITCH_API_KEY.
Mặc định: project "Realtime Gold Tracker iOS" -> thư mục <repo>/stitch/
"""
import json
import os
import re
import sys
import time
import urllib.request

MCP_URL = "https://stitch.googleapis.com/mcp"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_key():
    if os.environ.get("STITCH_API_KEY"):
        return os.environ["STITCH_API_KEY"]
    cfg = json.load(open(os.path.join(REPO, "opencode.json"), encoding="utf-8"))
    return cfg["mcp"]["stitch"]["headers"]["X-Goog-Api-Key"]


KEY = load_key()


def call(tool, args, retries=3):
    body = json.dumps({
        "jsonrpc": "2.0", "id": int(time.time() * 1000) % 100000,
        "method": "tools/call",
        "params": {"name": tool, "arguments": args},
    }).encode("utf-8")
    req = urllib.request.Request(MCP_URL, data=body, headers={
        "X-Goog-Api-Key": KEY,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read().decode("utf-8")
            break
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    else:
        raise last
    if raw.startswith("event:"):
        raw = "".join(l[5:].strip() for l in raw.splitlines() if l.startswith("data:"))
    msg = json.loads(raw)
    if "error" in msg:
        raise RuntimeError(msg["error"])
    res = msg["result"]
    text = "\n".join(c.get("text", "") for c in res.get("content", []))
    if res.get("isError"):
        raise RuntimeError(text)
    try:
        return json.loads(text)
    except Exception:
        return text


def fetch(url, dest, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def slug(title):
    s = re.sub(r"[^0-9A-Za-zÀ-ỹ]+", "-", title).strip("-")
    return s[:60] or "screen"


def main():
    project_id = sys.argv[1] if len(sys.argv) > 1 else "325718162326198286"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "stitch")
    os.makedirs(os.path.join(out, "screens"), exist_ok=True)

    project = call("get_project", {"name": f"projects/{project_id}"})
    json.dump(project, open(os.path.join(out, "project.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("project:", project.get("title"))

    screens = call("list_screens", {"projectId": project_id})["screens"]
    print("screens:", len(screens))

    rows, used = [], set()
    for s in screens:
        title = s["title"]
        slug_name = slug(title)
        n = 1
        while slug_name in used:
            slug_name, n = f"{slug_name}-{n}", n + 1
        used.add(slug_name)
        kind, url, size = "", "", 0
        html = s.get("htmlCode") or {}
        if html.get("downloadUrl"):
            ext = "html" if "html" in (html.get("mimeType") or "") else "txt"
            dest = os.path.join(out, "screens", f"{slug_name}.{ext}")
            size = fetch(html["downloadUrl"], dest)
            kind, url = f"{slug_name}.{ext}", f"screens/{slug_name}.{ext}"
        shot = s.get("screenshot") or {}
        if shot.get("downloadUrl"):
            dest = os.path.join(out, "screens", f"{slug_name}.png")
            try:
                fetch(shot["downloadUrl"], dest)
            except Exception as e:
                print("  shot fail", slug_name, e)
        rows.append({"title": title, "device": s.get("deviceType"),
                     "size": f'{s.get("width")}x{s.get("height")}', "file": url, "kb": size // 1024})
        print("  -", title, "->", url)

    ds = call("list_design_systems", {"projectId": project_id})["designSystems"]
    if ds:
        d = ds[0]["designSystem"]
        md = d.get("designMd") or (d.get("theme") or {}).get("designMd") or ""
        head = f'# Design System — {d.get("displayName")}\n\n'
        head += f'`colorMode={d["theme"].get("colorMode")}` · `font={d["theme"].get("font")}` · `primary={d["theme"].get("customColor")}`\n\n'
        head += "> Nguồn: Stitch project `"
        head += project.get("title", "")
        head += "` · export " + time.strftime("%Y-%m-%d %H:%M") + "\n\n"
        head += "## Style guidelines\n\n" + (d.get("styleGuidelines") or "") + "\n\n---\n\n"
        with open(os.path.join(out, "DESIGN.md"), "w", encoding="utf-8") as f:
            f.write(head + md)
        json.dump(ds, open(os.path.join(out, "design_system.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print("design system:", d.get("displayName"))

    with open(os.path.join(out, "screens.md"), "w", encoding="utf-8") as f:
        f.write(f'# Screens — {project.get("title")}\n\n')
        f.write("| # | Tên màn hình | Thiết bị | Kích thước | File |\n|---:|---|---|---|---|\n")
        for i, r in enumerate(rows, 1):
            link = f'[`{r["file"]}`]({r["file"]})' if r["file"] else "—"
            f.write(f'| {i} | {r["title"]} | {r["device"]} | {r["size"]} | {link} |\n')

    print("saved ->", out)


if __name__ == "__main__":
    main()
