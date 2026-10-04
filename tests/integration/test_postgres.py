"""Real-Postgres checks for the shared database (Supabase). Skipped unless TEST_DATABASE_URL is set.

    TEST_DATABASE_URL=postgresql://... .venv/Scripts/python -m pytest tests/integration -q

Everything runs inside a throwaway schema (dropped afterwards), so it never touches the
pipeline's real tables even when pointed at the production project.
"""
import json
import os
import uuid
from dataclasses import replace
from datetime import timedelta

import pytest

from pipeline.ingest.ingest import ingest, ingest_window, load_raw
from pipeline.store.db import DbError, check_db, migrate, open_db, schema_version
from tests.unit.test_ingest import REG, THU, FakeGmail, _tldr_triple, eml

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def pg():
    schema = f"test_{uuid.uuid4().hex[:10]}"
    db = open_db(URL)
    db.execute(f"CREATE SCHEMA {schema}")
    db.execute(f"SET search_path TO {schema}")
    try:
        yield db
    finally:
        db.execute(f"DROP SCHEMA {schema} CASCADE")
        db.close()


def test_migrate_and_types(pg):
    assert migrate(pg) == ["001_content_store"] and migrate(pg) == [] and schema_version(pg) == 1
    rls = pg.all("SELECT relname, relrowsecurity FROM pg_class WHERE relnamespace = current_schema()::regnamespace "
                 "AND relkind = 'r'")
    assert rls and all(r["relrowsecurity"] for r in rls)


def test_full_ingest_round_trip(pg, settings):
    g = FakeGmail()
    _tldr_triple(g, THU - timedelta(hours=6))
    raw = eml("Axios Markets <markets@axios.com>", "Rates \U0001F4C8", msgid="<ax@x>")
    g.add("ax", raw, THU - timedelta(hours=2), labels=("SPAM", "INBOX"))
    migrate(pg)
    rep = ingest(settings, REG, "tech", g, pg, now=THU)
    rep2 = ingest(settings, REG, "finance", g, pg, now=THU)
    # FakeGmail ignores the query, so the Tech run already stores the Axios email too
    assert (rep.new, rep.duplicates, rep2.new, rep2.known) == (2, 2, 0, 4)
    row = pg.one("SELECT * FROM documents WHERE id = 'ax'")
    assert row["received_at"] == "2026-10-01T14:00:00Z" and row["received_day_et"] == "2026-10-01"
    assert row["in_spam"] is True and json.loads(row["label_ids"]) == ["SPAM", "INBOX"]
    assert load_raw(pg, "ax") == raw
    assert json.loads(pg.scalar("SELECT stats FROM ingest_runs WHERE id = ?", (rep.run_id,)))["new"] == 2
    # idempotent, and the watermark comes back as the same ISO string
    assert ingest(settings, REG, "tech", g, pg, now=THU).new == 0
    assert ingest_window(REG, "tech", pg, THU + timedelta(hours=1))[0] == THU - timedelta(minutes=10)


def test_second_ingest_is_locked_out(pg, settings):
    migrate(pg)
    other = open_db(URL)
    try:
        assert other.scalar("SELECT pg_try_advisory_lock(hashtext(?)) AS ok", ("pipeline:ingest",))
        with pytest.raises(DbError, match="already running"):
            ingest(settings, REG, "tech", FakeGmail(), pg, now=THU)
    finally:
        other.close()


def test_doctor_check():
    ok, detail = check_db(URL)
    assert ok and "PostgreSQL" in detail and "schema v" in detail


def test_story_cards_view_and_vector_search(pg, settings):
    """Pranav's story-card shape and pgvector similarity, on real Postgres."""
    g = FakeGmail()
    g.add("v1", eml("TLDR <dan@tldrnewsletter.com>", "Chips", msgid="<v1@x>"), THU - timedelta(hours=2))
    migrate(pg)
    ingest(settings, REG, "tech", g, pg, now=THU)
    with pg.transaction():
        ids = [pg.scalar("INSERT INTO items (document_id, source_id, seq, headline, summary, why_it_matters, "
                         "extractor, created_at) VALUES ('v1', 'tldr', ?, ?, 's', 'w', 'rule:test', now()) RETURNING id",
                         (n, h)) for n, h in enumerate(["Nvidia chips", "Bakery opens"])]
        pg.execute("INSERT INTO item_facts (item_id, seq, kind, claim, evidence) VALUES (?, 0, 'claim', 'c1', 'e')",
                   (ids[0],))
        pg.execute("INSERT INTO links (document_id, item_id, seq, anchor, raw_url, canonical_url) "
                   "VALUES ('v1', ?, 0, 'read', ?, ?)", (ids[0], "https://x.test/a?utm_source=t", "https://x.test/a"))
        for i, vec in zip(ids, ([1.0] + [0.0] * 767, [0.0, 1.0] + [0.0] * 766)):
            pg.execute("INSERT INTO item_embeddings VALUES (?, 'test', ?::extensions.halfvec, now())", (i, str(vec)))
    card = pg.one("SELECT * FROM story_cards WHERE card_id = ?", (str(ids[0]),))
    assert card["gmail_id"] == "v1" and card["what"] == "s" and card["why"] == "w"
    assert json.loads(card["facts_json"]) == ["c1"]
    assert json.loads(card["links_json"]) == [{"anchor": "read", "url": "https://x.test/a"}]
    probe = str([0.9, 0.1] + [0.0] * 766)
    nearest = pg.scalar("SELECT item_id FROM item_embeddings ORDER BY embedding OPERATOR(extensions.<=>) "
                        "?::extensions.halfvec LIMIT 1", (probe,))
    assert nearest == ids[0]


def test_public_api_roles_cannot_read(pg, settings):
    """Supabase's public API runs as anon/authenticated: they must see no rows (RLS, no policies),
    including through the story_cards view (security_invoker). Grants mirror Supabase's public schema."""
    g = FakeGmail()
    g.add("r1", eml("TLDR <dan@tldrnewsletter.com>", "Secret", msgid="<r1@x>"), THU - timedelta(hours=2))
    migrate(pg)
    ingest(settings, REG, "tech", g, pg, now=THU)
    schema = pg.scalar("SELECT current_schema() AS s")
    for role in ("anon", "authenticated"):
        if not pg.scalar("SELECT 1 AS ok FROM pg_roles WHERE rolname = ?", (role,)):
            continue
        pg.execute(f"GRANT USAGE ON SCHEMA {schema} TO {role}")
        pg.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {role}")
        with pg.transaction():
            pg.execute(f"SET LOCAL ROLE {role}")
            assert pg.all("SELECT * FROM documents") == []
            assert pg.all("SELECT * FROM document_raw") == []
            assert pg.all("SELECT * FROM story_cards") == []
