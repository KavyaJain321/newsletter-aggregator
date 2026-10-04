"""SQLite access. The schema (instruction.md §3) is created in Step 4."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def check_writable(path: Path) -> tuple[bool, str]:
    """Prove we can write to the DB file without leaving anything behind."""
    try:
        conn = connect(path)
        try:
            conn.execute("BEGIN")
            conn.execute("CREATE TABLE _doctor_probe (x INTEGER)")
            conn.execute("INSERT INTO _doctor_probe VALUES (1)")
            conn.execute("ROLLBACK")
        finally:
            conn.close()
    except (sqlite3.Error, OSError) as e:
        return False, f"{path}: {e}"
    return True, f"{path} (SQLite {sqlite3.sqlite_version})"
