# -*- coding: utf-8 -*-
"""
Kết nối PostgreSQL (Neon) qua psycopg3 connection pool.
Ưu tiên env DATABASE_URL (Render Dashboard); nếu chưa set thì đọc .env.local
tại thư mục gốc repo (local dev), ví dụ:
  postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
"""
from __future__ import annotations

import os
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import psycopg
from psycopg_pool import ConnectionPool

log = logging.getLogger("vnstock.db")

_ROOT = Path(__file__).resolve().parent.parent.parent  # finan/


def _resolve_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    try:
        for line in (_ROOT / ".env.local").read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("DATABASE_URL="):
                return s.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


DATABASE_URL = _resolve_url()

_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL chưa được cấu hình. "
                "Thêm biến môi trường DATABASE_URL vào Render Dashboard."
            )
        _pool = ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1,
            max_size=5,
            open=True,
            kwargs={"autocommit": False},
        )
        log.info("DB pool khởi tạo thành công")
    return _pool


@contextmanager
def get_conn() -> Generator[psycopg.Connection, None, None]:
    """Context manager trả về connection từ pool."""
    pool = _get_pool()
    with pool.connection() as conn:
        yield conn


def init_schema() -> None:
    """Tạo bảng nếu chưa tồn tại (idempotent)."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username    TEXT PRIMARY KEY,
                email       TEXT UNIQUE NOT NULL,
                role        TEXT NOT NULL DEFAULT 'user',
                salt        TEXT NOT NULL,
                pw_hash     TEXT NOT NULL,
                active      BOOLEAN NOT NULL DEFAULT TRUE,
                created_at  DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token       TEXT PRIMARY KEY,
                uid         TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                role        TEXT NOT NULL,
                expires     DOUBLE PRECISION NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS sessions_uid_idx ON sessions(uid)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS sessions_expires_idx ON sessions(expires)
        """)
        conn.commit()
    log.info("Schema đã sẵn sàng")

