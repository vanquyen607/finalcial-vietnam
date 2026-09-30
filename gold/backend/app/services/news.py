from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx

from ..db import db

log = logging.getLogger("aurum.news")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# Điều kiện GET theo feed để tiết kiệm băng thông (giữ RAM, mất khi restart).
_COND: dict[str, dict[str, str]] = {}

FEEDS: list[tuple[str, str]] = [
    ("VnExpress", "https://vnexpress.net/rss/kinh-doanh.rss"),
    ("CafeF", "https://cafef.vn/thi-truong-chung-khoan.rss"),
    ("VietnamNet", "https://vietnamnet.vn/rss/kinh-doanh.rss"),
    ("VTV", "https://vtv.vn/rss/kinh-te.rss"),
]

# Chỉ giữ tin liên quan vàng/kim loại quý.
GOLD_RE = re.compile(r"vàng|gold|xau|sjc|doji|pnj|ounce|kim loại quý|lượng vàng", re.I)
IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)
WS_RE = re.compile(r"\s+")


def _text(item: ET.Element, tag: str) -> str:
    return (item.findtext(tag) or "").strip()


def _image(item: ET.Element, description: str) -> str:
    enc = item.find("enclosure")
    if enc is not None and (enc.get("type") or "").startswith("image"):
        return enc.get("url") or ""
    for tag in ("{http://search.yahoo.com/mrss/}content", "{http://search.yahoo.com/mrss/}thumbnail"):
        media = item.find(tag)
        if media is not None and media.get("url"):
            return media.get("url") or ""
    m = IMG_RE.search(description or "")
    return m.group(1) if m else ""


def _published(raw: str) -> int:
    try:
        dt = parsedate_to_datetime(raw.strip())
    except (TypeError, ValueError):
        return 0
    try:
        return int(dt.timestamp())
    except (OverflowError, OSError, ValueError):
        return 0


def parse_feed(xml: str, source: str, limit: int = 40) -> list[dict]:
    """Parse RSS -> tin vàng [{link,title,source,published,image}]. Ném exception nếu XML hỏng."""
    root = ET.fromstring(xml)
    out: list[dict] = []
    for item in root.findall(".//item")[:limit]:
        title = WS_RE.sub(" ", _text(item, "title")).strip()
        link = _text(item, "link")
        if not title or not link:
            continue
        desc = _text(item, "description")
        if not GOLD_RE.search(f"{title} {desc}"):
            continue
        out.append({
            "link": link,
            "title": title,
            "source": source,
            "published": _published(_text(item, "pubDate")),
            "image": _image(item, desc),
        })
    # dedupe theo link, giữ bản mới nhất
    seen: dict[str, dict] = {}
    for row in out:
        prev = seen.get(row["link"])
        if prev is None or row["published"] > prev["published"]:
            seen[row["link"]] = row
    return sorted(seen.values(), key=lambda r: r["published"], reverse=True)


async def fetch_news(client: httpx.AsyncClient) -> list[dict]:
    """Kéo toàn bộ feed, trả về tin vàng đã dedupe + sắp xếp mới nhất trước."""
    merged: dict[str, dict] = {}
    for source, url in FEEDS:
        try:
            headers = dict(HEADERS)
            cond = _COND.get(url)
            if cond:
                if cond.get("etag"):
                    headers["If-None-Match"] = cond["etag"]
                if cond.get("modified"):
                    headers["If-Modified-Since"] = cond["modified"]
            resp = await client.get(url, headers=headers, timeout=15.0)
            if resp.status_code == 304:
                continue  # feed không đổi
            resp.raise_for_status()
            _COND[url] = {
                "etag": resp.headers.get("etag", ""),
                "modified": resp.headers.get("last-modified", ""),
            }
            rows = parse_feed(resp.text, source)
        except Exception as exc:  # noqa: BLE001 - feed lỗi là bình thường
            log.debug("feed %s lỗi: %s", source, exc)
            continue
        for row in rows:
            prev = merged.get(row["link"])
            if prev is None or row["published"] > prev["published"]:
                merged[row["link"]] = row
    return sorted(merged.values(), key=lambda r: r["published"], reverse=True)


async def refresh_news(client: httpx.AsyncClient) -> int:
    """Kéo feed -> lưu DB -> prune tin cũ. Trả về số tin mới/giữ lại."""
    rows = await fetch_news(client)
    now = int(time.time())
    db.upsert_news([{**r, "fetched_at": now} for r in rows])
    db.prune_news(now - 7 * 86_400)
    return len(rows)
