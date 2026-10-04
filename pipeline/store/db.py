"""SQLite access and schema migrations (instruction.md §3).

Migrations are numbered SQL files in store/migrations/ (`NNN_name.sql`), applied in order,
each in its own transaction, and recorded in `schema_migrations`. Never edit an applied
migration: add the next number instead.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_NAME_RE = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)  # autocommit; transactions are explicit
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def _migrations(directory: Path) -> list[tuple[int, str, Path]]:
    found = []
    for p in sorted(directory.glob("*.sql")):
        m = _NAME_RE.match(p.name)
        if not m:
            raise ValueError(f"bad migration file name: {p.name} (want NNN_name.sql)")
        found.append((int(m.group(1)), m.group(2), p))
    versions = [v for v, _, _ in found]
    if versions != list(range(1, len(versions) + 1)):
        raise ValueError(f"migrations must be numbered 001, 002, ... without gaps: {versions}")
    return found


def schema_version(conn: sqlite3.Connection) -> int:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations "
                 "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
    row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return row[0] or 0


def _statements(sql: str) -> list[str]:
    """Split a migration into statements (executescript would commit mid-migration).
    Migrations must not put ';' inside string literals or comments."""
    lines = [ln.split("--", 1)[0] for ln in sql.splitlines()]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def migrate(conn: sqlite3.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations, each atomically. Returns the names applied."""
    current = schema_version(conn)
    applied = []
    for version, name, path in _migrations(directory):
        if version <= current:
            continue
        conn.execute("BEGIN IMMEDIATE")
        try:
            for stmt in _statements(path.read_text(encoding="utf-8")):
                conn.execute(stmt)
            conn.execute("INSERT INTO schema_migrations VALUES (?, ?, ?)",
                         (version, name, datetime.now(timezone.utc).isoformat(timespec="seconds")))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        applied.append(f"{version:03d}_{name}")
    return applied


def check_writable(path: Path) -> tuple[bool, str]:
    """Prove we can write to the DB file without leaving anything behind."""
    try:
        conn = connect(path)
        try:
            conn.execute("BEGIN")
            conn.execute("CREATE TABLE _doctor_probe (x INTEGER)")
            conn.execute("INSERT INTO _doctor_probe VALUES (1)")
            conn.execute("ROLLBACK")
            tracked = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' "
                                   "AND name = 'schema_migrations'").fetchone()
            version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] if tracked else 0
        finally:
            conn.close()
    except (sqlite3.Error, OSError) as e:
        return False, f"{path}: {e}"
    return True, f"{path} (SQLite {sqlite3.sqlite_version}, schema v{version or 0})"
