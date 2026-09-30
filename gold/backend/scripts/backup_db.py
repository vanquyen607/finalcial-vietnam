"""Backup online SQLite bằng backup API (an toàn khi backend đang chạy).

Dùng:
    python scripts/backup_db.py                # backup DB mặc định, giữ 7 bản mới nhất
    python scripts/backup_db.py --keep 14      # giữ 14 bản
    GOLD_DB_PATH=/app/data/gold.db python scripts/backup_db.py

Lên lịch:
    Windows: schtasks /create /tn "AurumBackup" /tr "python D:\\Desktop\\finan\\gold\\backend\\scripts\\backup_db.py"
             /sc daily /st 02:00
    Linux/cron: 0 2 * * * /app/backend/.venv/bin/python /app/backend/scripts/backup_db.py
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import GOLD_DIR, settings  # noqa: E402


def backup(db_path: Path, out_dir: Path, keep: int) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dest = out_dir / f"gold_{stamp}.db"
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    # Giữ N bản mới nhất.
    snaps = sorted(out_dir.glob("gold_*.db"), key=lambda p: p.name)
    for old in snaps[: max(0, len(snaps) - keep)]:
        old.unlink()
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=int, default=7)
    ap.add_argument("--out", type=str, default=str(GOLD_DIR / "backups"))
    args = ap.parse_args()

    db_path = Path(settings.db_path)
    if not db_path.is_file():
        print(f"Không thấy DB: {db_path}")
        return 1
    dest = backup(db_path, Path(args.out), args.keep)
    print(f"Backup OK: {dest} ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
