from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

log = logging.getLogger("aurum.dbpg")


def _resolve_url(url: str | None = None) -> str:
    if url:
        return url
    u = os.environ.get("DATABASE_URL", "").strip()
    if u:
        return u
    try:
        root = __import__("pathlib").Path(__file__).resolve().parents[3]
        for line in (root / ".env.local").read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("DATABASE_URL="):
                return s.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:  # noqa: BLE001
        pass
    return ""


class PostgresDatabase:
    """Backend PostgreSQL (Neon) cho gold, cùng interface với SQLite Database."""

    def __init__(self, url: str | None = None) -> None:
        self._url = _resolve_url(url)
        if not self._url:
            raise RuntimeError("DATABASE_URL chưa được cấu hình")
        self._pool = ConnectionPool(
            conninfo=self._url, min_size=1, max_size=5, open=True,
            kwargs={"autocommit": False, "row_factory": dict_row},
        )
        self._lock = threading.Lock()
        self._init_schema()
        log.info("PostgresDatabase khởi tạo thành công")

    @contextmanager
    def _conn(self) -> Generator[psycopg.Connection, None, None]:
        with self._pool.connection() as conn:
            yield conn

    def _init_schema(self) -> None:
        stmts = [
            """CREATE TABLE IF NOT EXISTS quotes (
                ts BIGINT NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                buy DOUBLE PRECISION NOT NULL,
                sell DOUBLE PRECISION NOT NULL,
                change_buy DOUBLE PRECISION NOT NULL,
                change_sell DOUBLE PRECISION NOT NULL,
                unit TEXT NOT NULL,
                per TEXT NOT NULL,
                source TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_quotes_code_ts ON quotes(code, ts)",
            """CREATE UNIQUE INDEX IF NOT EXISTS uq_quotes_code_ts ON quotes(code, ts)""",
            """CREATE TABLE IF NOT EXISTS daily (
                code TEXT NOT NULL,
                date TEXT NOT NULL,
                buy DOUBLE PRECISION NOT NULL,
                sell DOUBLE PRECISION NOT NULL,
                day_change_buy DOUBLE PRECISION NOT NULL DEFAULT 0,
                day_change_sell DOUBLE PRECISION NOT NULL DEFAULT 0,
                updates INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (code, date)
            )""",
            """CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                code TEXT NOT NULL,
                direction TEXT NOT NULL,
                threshold DOUBLE PRECISION NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at BIGINT NOT NULL,
                triggered_at BIGINT,
                target_price DOUBLE PRECISION
            )""",
            """CREATE TABLE IF NOT EXISTS fx (
                ts BIGINT NOT NULL,
                usd_vnd DOUBLE PRECISION NOT NULL,
                source TEXT NOT NULL DEFAULT ''
            )""",
            """CREATE TABLE IF NOT EXISTS news (
                link TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT '',
                published BIGINT NOT NULL DEFAULT 0,
                image TEXT NOT NULL DEFAULT '',
                fetched_at BIGINT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_news_published ON news(published DESC)",
        ]
        with self._conn() as conn:
            for s in stmts:
                conn.execute(s)
            conn.commit()
            # migration: target_price
            conn.execute(
                "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS target_price DOUBLE PRECISION"
            )
            conn.commit()

    # --- quotes ---
    def insert_quotes(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._lock, self._conn() as conn:
            conn.executemany(
                """INSERT INTO quotes(ts,code,name,buy,sell,change_buy,change_sell,unit,per,source)
                   VALUES(%(ts)s,%(code)s,%(name)s,%(buy)s,%(sell)s,%(change_buy)s,
                          %(change_sell)s,%(unit)s,%(per)s,%(source)s)
                   ON CONFLICT (code, ts) DO NOTHING""",
                rows,
            )
            conn.commit()

    def latest_quotes(self) -> dict[str, dict]:
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                """SELECT DISTINCT ON (code) code, name, buy, sell, change_buy, change_sell,
                          unit, per, source, ts
                   FROM quotes ORDER BY code, ts DESC"""
            )
            return {r["code"]: dict(r) for r in cur.fetchall()}

    def series(self, code: str, since_ts: int) -> list[dict]:
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                "SELECT ts, buy, sell FROM quotes WHERE code=%s AND ts>=%s ORDER BY ts",
                (code, since_ts),
            )
            return [dict(r) for r in cur.fetchall()]

    def sparklines(self, since_ts: int, codes: list[str], max_points: int = 60) -> dict[str, list[dict]]:
        if not codes:
            return {}
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                """
                SELECT code, ts, buy FROM (
                    SELECT code, ts, buy,
                           ROW_NUMBER() OVER (PARTITION BY code ORDER BY ts) - 1 AS rn,
                           COUNT(*) OVER (PARTITION BY code) AS cnt
                    FROM quotes
                    WHERE ts >= %s AND code = ANY(%s)
                ) sub
                WHERE rn %% GREATEST(1, cnt / %s) = 0
                ORDER BY code, ts
                """,
                (since_ts, codes, max_points),
            )
            out: dict[str, list[dict]] = {}
            for row in cur.fetchall():
                out.setdefault(row["code"], []).append({"ts": row["ts"], "buy": row["buy"]})
            return out

    def prune_quotes(self, older_than_ts: int) -> int:
        with self._lock, self._conn() as conn:
            cur = conn.execute("DELETE FROM quotes WHERE ts<%s", (older_than_ts,))
            conn.commit()
            return cur.rowcount

    # --- daily ---
    def upsert_daily(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._lock, self._conn() as conn:
            conn.executemany(
                """INSERT INTO daily(code,date,buy,sell,day_change_buy,day_change_sell,updates)
                   VALUES(%(code)s,%(date)s,%(buy)s,%(sell)s,%(day_change_buy)s,
                          %(day_change_sell)s,%(updates)s)
                   ON CONFLICT (code, date) DO UPDATE SET
                     buy=excluded.buy, sell=excluded.sell,
                     day_change_buy=excluded.day_change_buy,
                     day_change_sell=excluded.day_change_sell,
                     updates=excluded.updates""",
                rows,
            )
            conn.commit()

    def daily(self, code: str, days: int) -> list[dict]:
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                """SELECT date, buy, sell, day_change_buy, day_change_sell, updates
                   FROM daily WHERE code=%s ORDER BY date DESC LIMIT %s""",
                (code, days),
            )
            return [dict(r) for r in cur.fetchall()][::-1]

    def upsert_daily_snapshot(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._lock, self._conn() as conn:
            conn.executemany(
                """INSERT INTO daily(code,date,buy,sell,day_change_buy,day_change_sell,updates)
                   VALUES(%(code)s,%(date)s,%(buy)s,%(sell)s,%(day_change_buy)s,
                          %(day_change_sell)s,0)
                   ON CONFLICT (code, date) DO UPDATE SET
                     buy=excluded.buy, sell=excluded.sell,
                     day_change_buy=excluded.day_change_buy,
                     day_change_sell=excluded.day_change_sell""",
                rows,
            )
            conn.commit()

    # --- alerts ---
    def add_alert(self, code: str, direction: str, threshold: float, note: str,
                  target_price: float | None = None) -> dict:
        now = int(time.time())
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO alerts(code,direction,threshold,note,created_at,target_price)
                   VALUES(%s,%s,%s,%s,%s,%s) RETURNING id""",
                (code, direction, threshold, note, now, target_price),
            )
            alert_id = cur.fetchone()["id"]
            conn.commit()
        return {"id": alert_id, "code": code, "direction": direction, "threshold": threshold,
                "note": note, "active": True, "created_at": now, "triggered_at": None,
                "target_price": target_price}

    def list_alerts(self) -> list[dict]:
        with self._lock, self._conn() as conn:
            cur = conn.execute("SELECT * FROM alerts ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]

    def delete_alert(self, alert_id: int) -> bool:
        with self._lock, self._conn() as conn:
            cur = conn.execute("DELETE FROM alerts WHERE id=%s", (alert_id,))
            conn.commit()
            return cur.rowcount > 0

    def set_alert_active(self, alert_id: int, active: bool) -> bool:
        with self._lock, self._conn() as conn:
            cur = conn.execute("UPDATE alerts SET active=%s WHERE id=%s",
                               (active, alert_id))
            conn.commit()
            return cur.rowcount > 0

    def mark_triggered(self, alert_id: int) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("UPDATE alerts SET triggered_at=%s WHERE id=%s",
                         (int(time.time()), alert_id))
            conn.commit()

    def active_alerts(self) -> list[dict]:
        with self._lock, self._conn() as conn:
            cur = conn.execute("SELECT * FROM alerts WHERE active=TRUE")
            return [dict(r) for r in cur.fetchall()]

    # --- fx ---
    def insert_fx(self, usd_vnd: float, source: str = "") -> None:
        with self._lock, self._conn() as conn:
            conn.execute("INSERT INTO fx(ts,usd_vnd,source) VALUES(%s,%s,%s)",
                         (int(time.time()), usd_vnd, source))
            conn.commit()

    def latest_fx(self) -> dict | None:
        with self._lock, self._conn() as conn:
            cur = conn.execute("SELECT ts, usd_vnd, source FROM fx ORDER BY ts DESC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None

    def prune_fx(self, older_than_ts: int) -> int:
        with self._lock, self._conn() as conn:
            cur = conn.execute("DELETE FROM fx WHERE ts<%s", (older_than_ts,))
            conn.commit()
            return cur.rowcount

    # --- news ---
    def upsert_news(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._lock, self._conn() as conn:
            conn.executemany(
                """INSERT INTO news(link,title,source,published,image,fetched_at)
                   VALUES(%(link)s,%(title)s,%(source)s,%(published)s,%(image)s,%(fetched_at)s)
                   ON CONFLICT (link) DO UPDATE SET title=excluded.title,
                     source=excluded.source, published=excluded.published,
                     image=excluded.image, fetched_at=excluded.fetched_at""",
                rows,
            )
            conn.commit()

    def list_news(self, limit: int = 30) -> list[dict]:
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                """SELECT link, title, source, published, image FROM news
                   ORDER BY published DESC, fetched_at DESC LIMIT %s""", (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    def prune_news(self, older_than_ts: int) -> int:
        with self._lock, self._conn() as conn:
            cur = conn.execute("DELETE FROM news WHERE fetched_at<%s", (older_than_ts,))
            conn.commit()
            return cur.rowcount

    def close(self) -> None:
        try:
            self._pool.close()
        except Exception:  # noqa: BLE001
            pass