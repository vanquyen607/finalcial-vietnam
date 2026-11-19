# -*- coding: utf-8 -*-
"""Bao ve endpoint ton quota / thay doi du lieu bang token tuy chon.

Neu bien moi truong ADMIN_TOKEN duoc dat, cac endpoint nhay cam (chay man loc,
them/xoa danh muc, quy tac alert) yeu cau header `X-Admin-Token` (hoac `?token=`)
khop. Neu ADMIN_TOKEN khong dat (dev/local) -> mo hoan toan (tuong thich nguoc).
"""
from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, Request

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "").strip()


def admin_guard(request: Request) -> None:
    """FastAPI dependency: chan 401 neu token khong khop (khi ADMIN_TOKEN duoc dat)."""
    if not ADMIN_TOKEN:
        return
    tok = request.headers.get("x-admin-token") or request.query_params.get("token") or ""
    # so sanh hang so thoi gian — tranh timing attack
    if not secrets.compare_digest(tok, ADMIN_TOKEN):
        raise HTTPException(
            status_code=401,
            detail="Cần token quản trị (X-Admin-Token)",
            headers={"WWW-Authenticate": "X-Admin-Token"},
        )


def is_locked() -> bool:
    """True neu he thong dang yeu cau token (ADMIN_TOKEN da dat)."""
    return bool(ADMIN_TOKEN)
