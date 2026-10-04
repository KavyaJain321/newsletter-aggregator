import re

import pytest

from pipeline.store.db import MIGRATIONS_DIR, Db, DbError, _scrub, migrate, open_db, schema_version
from pipeline.store.raw import pack, sha256, unpack


def _tables(sql: str) -> dict[str, list[str]]:
    """{table: [column, ...]} from CREATE TABLE statements. A column line is `name TYPE ...`;
    constraint lines (PRIMARY KEY / UNIQUE / ...) and wrapped CHECK lists are ignored."""
    out = {}
    for name, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\)", sql, flags=re.S):
        cols = []
        for line in body.splitlines():
            m = re.match(r"^\s*([a-z_][a-z0-9_]*)\s+[A-Za-z]", line)
            if m and m.group(1).upper() not in {"PRIMARY", "UNIQUE", "CHECK", "FOREIGN", "CONSTRAINT"}:
                cols.append(m.group(1))
        out[name] = cols
    return out


def test_sqlite_test_double_matches_postgres_schema():
    pg = sorted((MIGRATIONS_DIR / "postgres").glob("*.sql"))
    lite = sorted((MIGRATIONS_DIR / "sqlite").glob("*.sql"))
    assert [p.name for p in pg] == [p.name for p in lite]
    for a, b in zip(pg, lite):
        ta, tb = _tables(a.read_text(encoding="utf-8")), _tables(b.read_text(encoding="utf-8"))
        assert ta == tb, f"{a.name}: postgres and sqlite schemas differ"
        assert ta, f"{a.name}: no tables parsed"


def test_postgres_migrations_lock_down_the_public_api():
    sql = "\n".join(p.read_text(encoding="utf-8") for p in (MIGRATIONS_DIR / "postgres").glob("*.sql"))
    for table in [*_tables(sql), "schema_migrations"]:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql, f"RLS missing on {table}"
    assert "CREATE POLICY" not in sql   # no policies: Supabase anon/authenticated keys see nothing


def test_placeholders_and_percent_are_translated_for_postgres():
    db = Db.__new__(Db)
    db.dialect = "postgres"
    assert db._sql("SELECT a FROM t WHERE b = ? AND c LIKE 'x%'") == "SELECT a FROM t WHERE b = %s AND c LIKE 'x%%'"
    db.dialect = "sqlite"
    assert db._sql("WHERE b = ?") == "WHERE b = ?"


def test_password_is_scrubbed_from_errors():
    url = "postgresql://postgres.ref:pa55-word@host:5432/postgres"
    assert _scrub("auth failed for pa55-word at host", url) == "auth failed for *** at host"


def test_transaction_rolls_back_on_error(settings):
    with open_db(settings.database_url) as db:
        migrate(db)
        with pytest.raises(RuntimeError):
            with db.transaction():
                db.execute("INSERT INTO ingest_runs (channel, scope, window_start, window_end, query, status, started_at) "
                           "VALUES ('email', 'tech', 'a', 'b', 'q', 'running', 'x')")
                raise RuntimeError("boom")
        assert db.scalar("SELECT COUNT(*) AS n FROM ingest_runs") == 0
        with pytest.raises(DbError, match="nested"):
            with db.transaction():
                with db.transaction():
                    pass


def test_bad_sql_raises_db_error(settings):
    with open_db(settings.database_url) as db:
        with pytest.raises(DbError, match="no such table"):
            db.execute("SELECT * FROM nope")


def test_migration_numbering_is_enforced(tmp_path, settings):
    (tmp_path / "001_a.sql").write_text("CREATE TABLE a (x INTEGER)", encoding="utf-8")
    (tmp_path / "003_c.sql").write_text("CREATE TABLE c (x INTEGER)", encoding="utf-8")
    with open_db(settings.database_url) as db:
        with pytest.raises(ValueError, match="without gaps"):
            migrate(db, tmp_path)
        assert schema_version(db) == 0


def test_failed_migration_applies_nothing(tmp_path, settings):
    (tmp_path / "001_bad.sql").write_text("CREATE TABLE ok_t (x INTEGER);\nCREATE TABLE broken (", encoding="utf-8")
    with open_db(settings.database_url) as db:
        with pytest.raises(Exception):
            migrate(db, tmp_path)
        assert schema_version(db) == 0
        assert db.one("SELECT name FROM sqlite_master WHERE name = 'ok_t'") is None


def test_raw_pack_is_deterministic_and_verified():
    raw = b"From: a@b.com\r\n\r\n" + b"<p>hello</p>" * 500
    assert pack(raw) == pack(raw) and len(pack(raw)) < len(raw) / 10
    assert unpack(pack(raw), sha256(raw)) == raw
    with pytest.raises(ValueError, match="sha256"):
        unpack(pack(raw), sha256(b"other"))


# A made-up password with the characters that broke the real one (unencoded '@' and '#').
_BAD = "postgresql://postgres:Hello@1234#@db.example.supabase.co:5432/postgres"


def test_raw_password_from_the_dashboard_is_encoded_automatically():
    from pipeline.store.db import normalize_db_url
    fixed = normalize_db_url(_BAD)
    assert fixed == "postgresql://postgres:Hello%401234%23@db.example.supabase.co:5432/postgres"
    assert normalize_db_url(fixed) == fixed                       # already encoded: untouched
    plain = "postgresql://postgres:abc123@h:5432/postgres"
    assert normalize_db_url(plain) == plain


def test_mask_and_scrub_hide_every_fragment_of_the_password():
    from pipeline.config.settings import mask_db_url
    assert mask_db_url(_BAD) == "postgresql://postgres:***@db.example.supabase.co:5432/postgres"
    msg = "failed to resolve host '1234#@db.example.supabase.co' for Hello"
    assert "1234" not in _scrub(msg, _BAD) and "Hello" not in _scrub(msg, _BAD)
    good = "postgresql://postgres:Hello%401234%23@db.example.supabase.co:5432/postgres"
    assert mask_db_url(good) == "postgresql://postgres:***@db.example.supabase.co:5432/postgres"
    assert "Hello@1234#" not in _scrub("auth failed: Hello@1234#", good)
