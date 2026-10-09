"""Tin co phieu theo ma - CafeF API cong khai."""
import json
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
NEWS_DIR = ROOT / "data" / "news"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

TTL = 3600
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def _ms(s: str) -> str:
    try:
        ms = int(s.replace("/Date(", "").replace(")/", ""))
        return datetime.fromtimestamp(ms / 1000).strftime("%d/%m/%Y")
    except Exception:
        return ""


def get_news(sym: str, refresh: bool = False) -> dict:
    sym = sym.upper().strip()
    path = NEWS_DIR / f"{sym}.json"
    if not refresh and path.exists():
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - obj.get("fetched_at", 0) < TTL:
                return {"status": "ready", "items": obj["items"], "cached": True}
        except Exception:
            pass
    try:
        url = f"https://cafef.vn/du-lieu/Ajax/PageNew/News.ashx?symbol={sym.lower()}&NewsType=0"
        r = requests.get(url, headers=UA, timeout=15)
        r.raise_for_status()
        payload = r.json()
        items = []
        for it in (payload.get("Data") or [])[:15]:
            link = (it.get("LinkDetail") or "").split("?")[0]
            if link.startswith("/"):
                link = "https://cafef.vn" + link
            items.append({
                "title": (it.get("Title") or "").strip(),
                "sub": (it.get("SubTitle") or "").strip(),
                "date": _ms(it.get("DeployDate") or ""),
                "url": link,
            })
        items = [i for i in items if i["title"]]
        obj = {"fetched_at": time.time(), "items": items}
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return {"status": "ready", "items": items}
    except Exception as e:
        if path.exists():
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
                return {"status": "ready", "items": obj["items"], "stale": True}
            except Exception:
                pass
        return {"status": "error", "message": str(e)}
