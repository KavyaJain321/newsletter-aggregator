"""Database access: the shared Supabase Postgres (production) or SQLite (offline unit tests only).

    db = open_db(settings.database_url)      # postgresql://... (Supabase session pooler) | sqlite:///path
    with db.transaction():
        db.execute("INSERT INTO t (a) VALUES (?)", (1,))
    row = db.one("SELECT a FROM t WHERE a = ?", (1,))   # dict or None

Pipeline SQL is written once in a portable subset: `?` placeholders, ON CONFLICT ... DO NOTHING,
RETURNING. Values ALWAYS go in as parameters - never put a literal '?' or
'%' inside SQL text (on Postgres every '?' is a placeholder). Rows come back as dicts. Timestamps are always ISO-8601 UTC strings
("2026-10-02T10:38:59Z") and JSON columns are strings on both backends, so callers never
see a dialect difference.

Schema migrations live in store/migrations/<dialect>/NNN_name.sql (Postgres is the source of
truth; the SQLite copy is the test double and a parity test keeps their tables/columns equal).
Each migration is applied atomically and recorded in `schema_migrations`. Never edit an applied
migration: add the next number.
"""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence
from urllib.parse import quote, unquote

from ..config.settings import mask_db_url, split_db_url

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_NAME_RE = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")


class DbError(RuntimeError):
    """A database failure, with any password scrubbed from the message."""


def _secret_fragments(url: str | None) -> list[str]:
    """The password plus every piece of it a driver might echo (e.g. the text after an unencoded '@')."""
    parts = split_db_url(url) if url else None
    if not parts or not parts[2]:
        return []
    pw = parts[2]
    frags = {pw, unquote(pw), quote(pw, safe=""), quote(unquote(pw), safe="")}
    for piece in re.split(r"[@#/?:]", pw) + re.split(r"[@#/?:]", unquote(pw)):
        if len(piece) >= 3:
            frags.add(piece)
    return sorted(frags, key=len, reverse=True)


def _scrub(msg: str, url: str | None) -> str:
    for frag in _secret_fragments(url):
        msg = msg.replace(frag, "***")
    return msg


def normalize_db_url(url: str) -> str:
    """Accept the address exactly as Supabase shows it, even with a raw password: if the
    password has characters a URL can't carry (@ # / ? space, or a stray %), percent-encode
    it. Already-encoded passwords are left alone."""
    parts = split_db_url(url)
    if not parts or not parts[2]:
        return url
    scheme, user, pw, rest = parts
    if re.search(r"[@#/? ]", pw) or re.search(r"%(?![0-9A-Fa-f]{2})", pw):
        pw = quote(pw, safe="")
    return f"{scheme}{user}:{pw}@{rest}"


class Db:
    dialect: str  # "postgres" | "sqlite"

    def __init__(self, url: str):
        self.url = url
        self.label = mask_db_url(url)
        self._in_tx = False
        if url.startswith("sqlite:///"):
            self.dialect = "sqlite"
            path = Path(url[len("sqlite:///"):])
            path.parent.mkdir(parents=True, exist_ok=True)
            self._conn: Any = sqlite3.connect(path, isolation_level=None)
            self._conn.row_factory = lambda cur, row: {d[0]: v for d, v in zip(cur.description, row)}
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA busy_timeout = 10000")
        elif re.match(r"^postgres(ql)?://", url):
            self.dialect = "postgres"
            self._conn = _pg_connect(url)
        else:
            raise DbError(f"unsupported DATABASE_URL scheme: {self.label}")

    # ------------------------------------------------------------ queries
    def _sql(self, sql: str) -> str:
        return sql if self.dialect == "sqlite" else sql.replace("%", "%%").replace("?", "%s")

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Any:
        try:
            return self._conn.execute(self._sql(sql), tuple(params))
        except Exception as e:  # noqa: BLE001 - re-raised with secrets scrubbed
            raise DbError(_scrub(f"{e.__class__.__name__}: {e}", self.url)) from None

    def one(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        return self.execute(sql, params).fetchone()

    def all(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        return self.execute(sql, params).fetchall()

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        row = self.one(sql, params)
        return None if row is None else next(iter(row.values()))

    @contextmanager
    def transaction(self) -> Iterator["Db"]:
        if self._in_tx:
            raise DbError("nested transactions are not supported")
        self._in_tx = True
        try:
            if self.dialect == "postgres":
                with self._conn.transaction():
                    yield self
            else:
                self._conn.execute("BEGIN IMMEDIATE")
                try:
                    yield self
                except BaseException:
                    self._conn.execute("ROLLBACK")
                    raise
                self._conn.execute("COMMIT")
        finally:
            self._in_tx = False

    @contextmanager
    def exclusive(self, name: str) -> Iterator[None]:
        """Cross-machine lock (Postgres advisory lock) so two teammates never run the same job at once."""
        if self.dialect != "postgres":
            yield
            return
        got = self.scalar("SELECT pg_try_advisory_lock(hashtext(?)) AS ok", (name,))
        if not got:
            raise DbError(f"'{name}' is already running elsewhere (database lock held) - try again later")
        try:
            yield
        finally:
            self.execute("SELECT pg_advisory_unlock(hashtext(?))", (name,))

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self) -> "Db":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def _pg_connect(url: str) -> Any:
    try:
        import psycopg
        from psycopg.rows import dict_row
        from psycopg.types.datetime import TimestamptzLoader
        from psycopg.types.string import TextLoader
    except ImportError as e:  # pragma: no cover
        raise DbError("psycopg is not installed: pip install -r pipeline/requirements.txt") from e

    class IsoUtcLoader(TimestamptzLoader):
        def load(self, data: Any) -> str:  # timestamptz -> "YYYY-MM-DDTHH:MM:SSZ" like SQLite
            return super().load(data).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        conn = psycopg.connect(url, autocommit=True, row_factory=dict_row, connect_timeout=15,
                               application_name="newsletter-pipeline")
    except Exception as e:  # noqa: BLE001
        raise DbError(_scrub(f"cannot connect to {mask_db_url(url)}: {e}", url)) from None
    conn.adapters.register_loader("timestamptz", IsoUtcLoader)
    conn.adapters.register_loader("jsonb", TextLoader)   # JSON stays a string, as in SQLite
    conn.adapters.register_loader("date", TextLoader)    # dates stay "YYYY-MM-DD" strings
    conn.execute("SET TIME ZONE 'UTC'")
    return conn


def open_db(url: str | None) -> Db:
    if not url:
        raise DbError("DATABASE_URL is not set - add the Supabase session-pooler connection string to .env")
    return Db(url if url.startswith("sqlite:") else normalize_db_url(url))


# ---------------------------------------------------------------- migrations
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


def _has_migrations_table(db: Db) -> bool:
    if db.dialect == "postgres":
        return bool(db.scalar("SELECT to_regclass('schema_migrations') IS NOT NULL AS ok"))
    return db.one("SELECT 1 AS ok FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'") is not None


def schema_version(db: Db) -> int:
    if not _has_migrations_table(db):
        return 0
    return db.scalar("SELECT MAX(version) AS v FROM schema_migrations") or 0


def _statements(sql: str) -> list[str]:
    """SQLite migrations only: split on ';' (no ';' inside literals or comments)."""
    lines = [ln.split("--", 1)[0] for ln in sql.splitlines()]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def migrate(db: Db, directory: Path | None = None) -> list[str]:
    """Apply pending migrations, each atomically. Returns the names applied."""
    directory = directory or (MIGRATIONS_DIR / db.dialect)
    with db.exclusive("pipeline:migrate"):
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations "
                   "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
        current = schema_version(db)
        applied = []
        for version, name, path in _migrations(directory):
            if version <= current:
                continue
            sql = path.read_text(encoding="utf-8")
            with db.transaction():
                if db.dialect == "postgres":
                    db._conn.execute(sql)   # whole script; no parameters
                else:
                    for stmt in _statements(sql):
                        db._conn.execute(stmt)
                db.execute("INSERT INTO schema_migrations VALUES (?, ?, ?)",
                           (version, name, datetime.now(timezone.utc).isoformat(timespec="seconds")))
            applied.append(f"{version:03d}_{name}")
    return applied


def check_db(url: str | None) -> tuple[bool, str]:
    """Doctor check: reachable, writable (rolled-back probe), schema version. Never mutates."""
    try:
        with open_db(url) as db:
            probe = "_doctor_probe"
            try:
                with db.transaction():
                    db.execute(f"CREATE TEMP TABLE {probe} (x INTEGER)")
                    db.execute(f"INSERT INTO {probe} VALUES (1)")
                    raise _Rollback
            except _Rollback:
                pass
            version = schema_version(db)
            server = db.scalar("SELECT version() AS v") if db.dialect == "postgres" else f"SQLite {sqlite3.sqlite_version}"
    except (DbError, OSError, sqlite3.Error) as e:
        return False, str(e)
    return True, f"{db.label} | {str(server).split(' on ')[0]} | schema v{version}"


class _Rollback(Exception):
    pass
