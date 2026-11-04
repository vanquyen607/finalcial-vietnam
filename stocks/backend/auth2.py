# -*- coding: utf-8 -*-
"""
Hệ thống xác thực người dùng — dùng PostgreSQL (Neon) qua db.py

Tables:
  users    (username PK, email, role, salt, pw_hash, active, created_at)
  sessions (token PK, uid FK, role, expires)

Password: SHA-256 với per-user salt (16 bytes hex)
Session : random 64-char hex token, TTL 7 ngày
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import time
from pathlib import Path

from fastapi import HTTPException, Request

from backend.db import get_conn, init_schema

SESSION_TTL = 60 * 60 * 24 * 7  # 7 ngày
_USERS_JSON = Path(__file__).resolve().parent.parent / "data" / "users.json"
log = logging.getLogger("vnstock.auth2")


# ── Khởi tạo schema + admin mặc định ──────────────────────────────────────
def _hash_pw(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def _bootstrap() -> None:
    """Gọi 1 lần khi startup: tạo schema + migrate users.json + admin mặc định."""
    try:
        init_schema()
        _migrate_users_json()
        _ensure_default_admin()
    except Exception as e:
        log.warning(f"Bootstrap lỗi (DATABASE_URL chưa set?): {e}")


def _migrate_users_json() -> None:
    """Import data/users.json sang Postgres 1 lần (idempotent), rồi đổi tên .bak.

    Giữ nguyên salt + pw_hash → mật khẩu cũ vẫn đăng nhập được.
    """
    if not _USERS_JSON.exists():
        return
    try:
        data = json.loads(_USERS_JSON.read_text("utf-8"))
    except Exception as e:
        log.warning(f"users.json hỏng, bỏ qua migrate: {e}")
        return
    if not isinstance(data, dict) or not data:
        _USERS_JSON.rename(_USERS_JSON.with_suffix(".json.bak"))
        return

    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if n == 0:
            for u in data.values():
                conn.execute(
                    """INSERT INTO users (username, email, role, salt, pw_hash, active, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (username) DO NOTHING""",
                    (
                        str(u.get("username", "")).lower().strip(),
                        str(u.get("email", "")).lower().strip(),
                        u.get("role", "user"),
                        u.get("salt", ""),
                        u.get("pw_hash", ""),
                        bool(u.get("active", True)),
                        float(u.get("created_at") or time.time()),
                    ),
                )
            conn.commit()
            log.info(f"Đã migrate {len(data)} user từ users.json sang Postgres")
        # bảng đã có dữ liệu → không import lại, chỉ dọn file cũ
    _USERS_JSON.rename(_USERS_JSON.with_suffix(".json.bak"))


def _ensure_default_admin() -> None:
    default_pw = os.environ.get("ADMIN_DEFAULT_PW", "admin123")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()
        if row:
            return
        salt = secrets.token_hex(16)
        conn.execute(
            """INSERT INTO users (username, email, role, salt, pw_hash, active, created_at)
               VALUES (%s, %s, 'admin', %s, %s, TRUE, %s)
               ON CONFLICT (username) DO NOTHING""",
            ("admin", "admin@vnstock.local", salt, _hash_pw(default_pw, salt), time.time()),
        )
        conn.commit()


# ── Public API ─────────────────────────────────────────────────────────────
def register(username: str, email: str, password: str) -> dict:
    if len(username) < 3 or len(username) > 32:
        raise ValueError("Tên đăng nhập phải từ 3–32 ký tự")
    if not email or "@" not in email:
        raise ValueError("Email không hợp lệ")
    if len(password) < 6:
        raise ValueError("Mật khẩu phải ít nhất 6 ký tự")
    username = username.lower().strip()

    with get_conn() as conn:
        # check duplicate username
        if conn.execute("SELECT 1 FROM users WHERE username=%s", (username,)).fetchone():
            raise ValueError("Tên đăng nhập đã tồn tại")
        # check duplicate email
        if conn.execute("SELECT 1 FROM users WHERE lower(email)=lower(%s)", (email,)).fetchone():
            raise ValueError("Email đã được đăng ký")

        salt = secrets.token_hex(16)
        conn.execute(
            """INSERT INTO users (username, email, role, salt, pw_hash, active, created_at)
               VALUES (%s, %s, 'user', %s, %s, TRUE, %s)""",
            (username, email.lower(), salt, _hash_pw(password, salt), time.time()),
        )
        conn.commit()

    return {"username": username, "role": "user"}


def login(username: str, password: str) -> dict:
    username = username.lower().strip()

    with get_conn() as conn:
        row = conn.execute(
            "SELECT salt, pw_hash, role, active FROM users WHERE username=%s",
            (username,),
        ).fetchone()

        if not row or not row[3]:  # not found or inactive
            raise ValueError("Tên đăng nhập hoặc mật khẩu không đúng")

        salt, pw_hash, role, active = row
        if not secrets.compare_digest(_hash_pw(password, salt), pw_hash):
            raise ValueError("Tên đăng nhập hoặc mật khẩu không đúng")

        # xóa session cũ quá hạn của user này
        conn.execute(
            "DELETE FROM sessions WHERE uid=%s AND expires < %s",
            (username, time.time()),
        )

        token = secrets.token_hex(32)
        expires = time.time() + SESSION_TTL
        conn.execute(
            "INSERT INTO sessions (token, uid, role, expires) VALUES (%s, %s, %s, %s)",
            (token, username, role, expires),
        )
        conn.commit()

    return {"token": token, "username": username, "role": role, "expires": int(expires)}


def logout(token: str) -> None:
    if not token:
        return
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token=%s", (token,))
        conn.commit()


def get_session(token: str) -> dict | None:
    if not token:
        return None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT uid, role, expires FROM sessions WHERE token=%s",
            (token,),
        ).fetchone()
        if not row:
            return None
        uid, role, expires = row
        if expires < time.time():
            conn.execute("DELETE FROM sessions WHERE token=%s", (token,))
            conn.commit()
            return None
        return {"uid": uid, "role": role, "expires": int(expires)}


def require_session(request: Request) -> dict:
    token = (
        request.headers.get("x-session-token")
        or request.cookies.get("ck_session")
        or request.query_params.get("session_token")
        or ""
    )
    s = get_session(token)
    if not s:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    return s


def require_admin(request: Request) -> dict:
    s = require_session(request)
    if s.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới được truy cập")
    return s


# ── Admin actions ──────────────────────────────────────────────────────────
def list_users() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT username, email, role, active, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [
        {
            "username": r[0],
            "email": r[1],
            "role": r[2],
            "active": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]


def set_user_active(username: str, active: bool) -> None:
    with get_conn() as conn:
        n = conn.execute(
            "UPDATE users SET active=%s WHERE username=%s",
            (active, username),
        ).rowcount
        if not n:
            raise ValueError("Không tìm thấy user")
        conn.commit()


def set_user_role(username: str, role: str) -> None:
    if role not in ("admin", "user"):
        raise ValueError("Role không hợp lệ")
    with get_conn() as conn:
        n = conn.execute(
            "UPDATE users SET role=%s WHERE username=%s",
            (role, username),
        ).rowcount
        if not n:
            raise ValueError("Không tìm thấy user")
        conn.commit()


def delete_user(username: str) -> None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT role FROM users WHERE username=%s", (username,)
        ).fetchone()
        if not row:
            raise ValueError("Không tìm thấy user")
        if row[0] == "admin":
            count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role='admin'"
            ).fetchone()[0]
            if count <= 1:
                raise ValueError("Không thể xóa admin cuối cùng")
        # sessions bị xóa cascade
        conn.execute("DELETE FROM users WHERE username=%s", (username,))
        conn.commit()
