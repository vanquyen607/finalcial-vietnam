from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from .config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    ts         INTEGER NOT NULL,
    code       TEXT    NOT NULL,
    name       TEXT    NOT NULL,
    buy        REAL    NOT NULL,
    sell       REAL    NOT NULL,
    change_buy REAL    NOT NULL,
    change_sell REAL   NOT NULL,
    unit       TEXT    NOT NULL,
    per        TEXT    NOT NULL,
    source     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quotes_code_ts ON quotes(code, ts);

CREATE TABLE IF NOT EXISTS daily (
    code             TEXT    NOT NULL,
    date             TEXT    NOT NULL,
    buy              REAL    NOT NULL,
    sell             REAL    NOT NULL,
    day_change_buy   REAL    NOT NULL DEFAULT 0,
    day_change_sell  REAL    NOT NULL DEFAULT 0,
    updates          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (code, date)
);

CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL,
    direction   TEXT    NOT NULL,   -- 'up' | 'down'
    threshold   REAL    NOT NULL,   -- % thay đổi tuyệt đối trong ngày
    note        TEXT    NOT NULL DEFAULT '',
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  INTEGER NOT NULL,
    triggered_at INTEGER
);

CREATE TABLE IF NOT EXISTS fx (
    ts       INTEGER NOT NULL,
    usd_vnd  REAL    NOT NULL,
    source   TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS news (
    link       TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT '',
    published  INTEGER NOT NULL DEFAULT 0,
    image      TEXT NOT NULL DEFAULT '',
    fetched_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_published ON news(published DESC);
"""


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # WAL: đọc/ghi đồng thời tốt hơn, chống corrupt khi process chết giữa chừng.
        try:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
        except sqlite3.Error:
            pass
        with self._conn:
            self._conn.executescript(_SCHEMA)

    # --- quotes ---
    def insert_quotes(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._lock, self._conn:
            self._conn.executemany(
                "INSERT INTO quotes(ts,code,name,buy,sell,change_buy,change_sell,unit,per,source)"
                " VALUES(:ts,:code,:name,:buy,:sell,:change_buy,:change_sell,:unit,:per,:source)",
                rows,
            )

    def latest_quotes(self) -> dict[str, dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT code, name, buy, sell, change_buy, change_sell, unit, per, source,"
                " MAX(ts) AS ts FROM quotes GROUP BY code"
            )
            return {r["code"]: dict(r) for r in cur.fetchall()}

    def series(self, code: str, since_ts: int) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT ts, buy, sell FROM quotes WHERE code=? AND ts>=? ORDER BY ts",
                (code, since_ts),
            )
            return [dict(r) for r in cur.fetchall()]

    def prune_quotes(self, older_than_ts: int) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM quotes WHERE ts<?", (older_than_ts,))
            return cur.rowcount

    # --- daily history ---
    def upsert_daily(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._lock, self._conn:
            self._conn.executemany(
                "INSERT INTO daily(code,date,buy,sell,day_change_buy,day_change_sell,updates)"
                " VALUES(:code,:date,:buy,:sell,:day_change_buy,:day_change_sell,:updates)"
                " ON CONFLICT(code,date) DO UPDATE SET buy=excluded.buy, sell=excluded.sell,"
                " day_change_buy=excluded.day_change_buy, day_change_sell=excluded.day_change_sell,"
                " updates=excluded.updates",
                rows,
            )

    def daily(self, code: str, days: int) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT date, buy, sell, day_change_buy, day_change_sell, updates FROM daily"
                " WHERE code=? ORDER BY date DESC LIMIT ?", (code, days),
            )
            return [dict(r) for r in cur.fetchall()][::-1]

    # --- alerts ---
    def add_alert(self, code: str, direction: str, threshold: float, note: str) -> dict:
        now = int(time.time())
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO alerts(code,direction,threshold,note,created_at) VALUES(?,?,?,?,?)",
                (code, direction, threshold, note, now),
            )
            alert_id = cur.lastrowid
        return {"id": alert_id, "code": code, "direction": direction, "threshold": threshold,
                "note": note, "active": 1, "created_at": now, "triggered_at": None}

    def list_alerts(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM alerts ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]

    def delete_alert(self, alert_id: int) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
            return cur.rowcount > 0

    def set_alert_active(self, alert_id: int, active: bool) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("UPDATE alerts SET active=? WHERE id=?",
                                      (1 if active else 0, alert_id))
            return cur.rowcount > 0

    def mark_triggered(self, alert_id: int) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE alerts SET triggered_at=? WHERE id=?",
                               (int(time.time()), alert_id))

    def active_alerts(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM alerts WHERE active=1")
            return [dict(r) for r in cur.fetchall()]

    # --- fx ---
    def insert_fx(self, usd_vnd: float, source: str = "") -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO fx(ts,usd_vnd,source) VALUES(?,?,?)",
                               (int(time.time()), usd_vnd, source))

    def latest_fx(self) -> dict | None:
        with self._lock:
            cur = self._conn.execute("SELECT ts, usd_vnd, source FROM fx ORDER BY ts DESC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None

    def prune_fx(self, older_than_ts: int) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM fx WHERE ts<?", (older_than_ts,))
            return cur.rowcount

    # --- news ---
    def upsert_news(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._lock, self._conn:
            self._conn.executemany(
                "INSERT INTO news(link,title,source,published,image,fetched_at)"
                " VALUES(:link,:title,:source,:published,:image,:fetched_at)"
                " ON CONFLICT(link) DO UPDATE SET title=excluded.title,"
                " source=excluded.source, published=excluded.published,"
                " image=excluded.image, fetched_at=excluded.fetched_at",
                rows,
            )

    def list_news(self, limit: int = 30) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT link, title, source, published, image FROM news"
                " ORDER BY published DESC, fetched_at DESC LIMIT ?", (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    def prune_news(self, older_than_ts: int) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM news WHERE fetched_at<?", (older_than_ts,))
            return cur.rowcount

    def close(self) -> None:
        with self._lock:
            self._conn.close()


db = Database(settings.ensure_dirs)
