# -*- coding: utf-8 -*-
"""
Hệ thống xác thực người dùng cho VN·STOCK Terminal.
- Lưu users vào users.json (relative to ROOT)
- Password hashing với hashlib + salt
- Session token (random, lưu trong memory + file)
- Role: admin | user
"""
from __future__ import annotations
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from fastapi import HTTPException, Request

ROOT = Path(__file__).resolve().parent.parent
USERS_FILE = ROOT / "data" / "users.json"
SESSIONS_FILE = ROOT / "data" / "sessions.json"

# Ensure data dir exists
(ROOT / "data").mkdir(exist_ok=True)

# In-memory session cache: token -> {uid, expires}
_sessions: dict[str, dict] = {}

SESSION_TTL = 60 * 60 * 24 * 7  # 7 ngày


# ---------------------------------------------------------------- helpers
def _hash_pw(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def _load_users() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {}


def _save_users(users: dict) -> None:
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), "utf-8")


def _load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        try:
            data = json.loads(SESSIONS_FILE.read_text("utf-8"))
            # purge expired
            now = time.time()
            data = {k: v for k, v in data.items() if v.get("expires", 0) > now}
            return data
        except Exception:
            pass
    return {}


def _save_sessions(sessions: dict) -> None:
    SESSIONS_FILE.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), "utf-8")


def _init_sessions() -> None:
    global _sessions
    _sessions = _load_sessions()


_init_sessions()


# ---------------------------------------------------------------- ensure default admin
def ensure_default_admin():
    """Tạo admin mặc định nếu chưa có."""
    users = _load_users()
    if not any(u.get("role") == "admin" for u in users.values()):
        default_pw = os.environ.get("ADMIN_DEFAULT_PW", "admin123")
        salt = secrets.token_hex(16)
        users["admin"] = {
            "username": "admin",
            "email": "admin@vnstock.local",
            "role": "admin",
            "salt": salt,
            "pw_hash": _hash_pw(default_pw, salt),
            "created_at": time.time(),
            "active": True,
        }
        _save_users(users)


ensure_default_admin()


# ---------------------------------------------------------------- public API
def register(username: str, email: str, password: str) -> dict:
    if len(username) < 3 or len(username) > 32:
        raise ValueError("Tên đăng nhập phải từ 3–32 ký tự")
    if len(password) < 6:
        raise ValueError("Mật khẩu phải ít nhất 6 ký tự")
    username = username.lower().strip()
    users = _load_users()
    if username in users:
        raise ValueError("Tên đăng nhập đã tồn tại")
    if any(u.get("email", "").lower() == email.lower() for u in users.values()):
        raise ValueError("Email đã được đăng ký")
    salt = secrets.token_hex(16)
    users[username] = {
        "username": username,
        "email": email.lower(),
        "role": "user",
        "salt": salt,
        "pw_hash": _hash_pw(password, salt),
        "created_at": time.time(),
        "active": True,
    }
    _save_users(users)
    return {"username": username, "role": "user"}


def login(username: str, password: str) -> dict:
    username = username.lower().strip()
    users = _load_users()
    user = users.get(username)
    if not user or not user.get("active"):
        raise ValueError("Tên đăng nhập hoặc mật khẩu không đúng")
    expected = _hash_pw(password, user["salt"])
    if not secrets.compare_digest(expected, user["pw_hash"]):
        raise ValueError("Tên đăng nhập hoặc mật khẩu không đúng")
    # create session
    token = secrets.token_hex(32)
    expires = time.time() + SESSION_TTL
    _sessions[token] = {"uid": username, "role": user["role"], "expires": expires}
    _save_sessions(_sessions)
    return {"token": token, "username": username, "role": user["role"], "expires": int(expires)}


def logout(token: str) -> None:
    _sessions.pop(token, None)
    _save_sessions(_sessions)


def get_session(token: str) -> dict | None:
    """Trả về session dict hoặc None nếu không hợp lệ."""
    s = _sessions.get(token)
    if not s:
        # try reload from file
        _init_sessions()
        s = _sessions.get(token)
    if not s:
        return None
    if s.get("expires", 0) < time.time():
        _sessions.pop(token, None)
        return None
    return s


def require_session(request: Request) -> dict:
    """FastAPI dependency: trả về session hoặc 401."""
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
    """FastAPI dependency: chỉ cho admin."""
    s = require_session(request)
    if s.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới được truy cập")
    return s


# ---------------------------------------------------------------- admin actions
def list_users() -> list:
    users = _load_users()
    return [
        {
            "username": u["username"],
            "email": u.get("email", ""),
            "role": u.get("role", "user"),
            "active": u.get("active", True),
            "created_at": u.get("created_at", 0),
        }
        for u in users.values()
    ]


def set_user_active(username: str, active: bool) -> None:
    users = _load_users()
    if username not in users:
        raise ValueError("Không tìm thấy user")
    users[username]["active"] = active
    _save_users(users)


def set_user_role(username: str, role: str) -> None:
    if role not in ("admin", "user"):
        raise ValueError("Role không hợp lệ")
    users = _load_users()
    if username not in users:
        raise ValueError("Không tìm thấy user")
    users[username]["role"] = role
    _save_users(users)


def delete_user(username: str) -> None:
    users = _load_users()
    if username not in users:
        raise ValueError("Không tìm thấy user")
    if users[username].get("role") == "admin":
        admins = [u for u in users.values() if u.get("role") == "admin"]
        if len(admins) <= 1:
            raise ValueError("Không thể xóa admin cuối cùng")
    del users[username]
    _save_users(users)
    # revoke sessions
    global _sessions
    _sessions = {k: v for k, v in _sessions.items() if v.get("uid") != username}
    _save_sessions(_sessions)
