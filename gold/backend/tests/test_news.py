from __future__ import annotations

import asyncio

import httpx
import pytest

from app.db import Database
from app.services import news as news_svc
from app.services.news import fetch_news, parse_feed

SAMPLE_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel><title>Test</title>
<item>
  <title>Giá vàng hôm nay tăng mạnh</title>
  <link>https://ex.com/vang-1</link>
  <description><![CDATA[<img src="https://ex.com/a.jpg"/> Vàng tăng]]></description>
  <pubDate>Wed, 30 Sep 2026 13:15:00 +0700</pubDate>
  <enclosure url="https://ex.com/b.jpg" type="image/jpeg"/>
</item>
<item>
  <title>Chứng khoán xanh điểm</title>
  <link>https://ex.com/ck-1</link>
  <description>Không liên quan</description>
  <pubDate>Wed, 30 Sep 2026 12:00:00 +0700</pubDate>
</item>
<item>
  <title>Gold price hits record</title>
  <link>https://ex.com/vang-1</link>
  <description>gold up</description>
  <pubDate>Wed, 30 Sep 2026 14:00:00 +0700</pubDate>
</item>
</channel></rss>"""


def test_parse_feed_filters_gold_and_dedupes():
    rows = parse_feed(SAMPLE_RSS, "TestSrc")
    # tin chứng khoán bị loại; 2 tin cùng link dedupe giữ bản mới nhất
    assert len(rows) == 1
    row = rows[0]
    assert row["link"] == "https://ex.com/vang-1"
    assert row["title"] == "Gold price hits record"
    assert row["published"] > 0
    assert row["source"] == "TestSrc"


def test_parse_feed_image_priority():
    rss = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel><title>T</title>
<item><title>Vàng A</title><link>https://ex.com/a</link>
<description><![CDATA[<img src="https://ex.com/desc.jpg"/>x]]></description>
<enclosure url="https://ex.com/enc.jpg" type="image/jpeg"/>
<pubDate>Wed, 30 Sep 2026 13:00:00 +0700</pubDate></item>
<item><title>Vàng B</title><link>https://ex.com/b</link>
<description>gold</description>
<media:content url="https://ex.com/media.jpg"/>
<pubDate>Wed, 30 Sep 2026 12:00:00 +0700</pubDate></item>
<item><title>Vàng C</title><link>https://ex.com/c</link>
<description><![CDATA[<img src="https://ex.com/desc2.jpg"/>gold]]></description>
<pubDate>Wed, 30 Sep 2026 11:00:00 +0700</pubDate></item>
</channel></rss>"""
    rows = parse_feed(rss, "T")
    by_link = {r["link"]: r["image"] for r in rows}
    assert by_link == {
        "https://ex.com/a": "https://ex.com/enc.jpg",
        "https://ex.com/b": "https://ex.com/media.jpg",
        "https://ex.com/c": "https://ex.com/desc2.jpg",
    }


def test_parse_feed_rejects_broken_xml():
    with pytest.raises(Exception):
        parse_feed("<rss><bad", "T")


def test_fetch_news_merges_feeds_and_skips_errors():
    async def go():
        def handler(request: httpx.Request) -> httpx.Response:
            if "vnexpress" in str(request.url):
                return httpx.Response(200, text=SAMPLE_RSS)
            return httpx.Response(500)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            return await fetch_news(client)
        finally:
            await client.aclose()

    rows = asyncio.run(go())
    assert len(rows) == 1
    assert rows[0]["source"] == "VnExpress"


def test_news_db_roundtrip(tmp_path, monkeypatch):
    db = Database(tmp_path / "news.db")
    monkeypatch.setattr(news_svc, "db", db)
    try:
        rows = parse_feed(SAMPLE_RSS, "T")
        db.upsert_news([{**r, "fetched_at": 123} for r in rows])
        listed = db.list_news(10)
        assert len(listed) == 1
        assert listed[0]["title"] == "Gold price hits record"
        # upsert lại cùng link: không trùng
        db.upsert_news([{**r, "fetched_at": 124} for r in rows])
        assert len(db.list_news(10)) == 1
        # prune theo fetched_at
        assert db.prune_news(125) == 1
        assert db.list_news(10) == []
    finally:
        db.close()


def test_fetch_news_uses_conditional_get():
    news_svc._COND.clear()
    calls: list[dict] = []

    async def go():
        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(dict(request.headers))
            if "if-none-match" in request.headers:
                return httpx.Response(304)
            return httpx.Response(
                200, text=SAMPLE_RSS,
                headers={"ETag": '"abc"',
                         "Last-Modified": "Wed, 30 Sep 2026 13:00:00 +0700"},
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            first = await fetch_news(client)
            second = await fetch_news(client)
            return first, second
        finally:
            await client.aclose()

    try:
        first, second = asyncio.run(go())
        assert len(first) == 1  # 4 feed cùng link -> dedupe còn 1
        assert second == []  # lần 2 toàn 304
        assert len(calls) == 8
        assert calls[4].get("if-none-match") == '"abc"'
        assert "if-modified-since" in calls[4]
        assert len(news_svc._COND) == 4
    finally:
        news_svc._COND.clear()
