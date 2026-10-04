import json
from datetime import datetime, timedelta, timezone

import pytest

from pipeline.config.registry import load_registry
from pipeline.ingest.gmail import GmailApiError, GmailAuthError, RawMessage
from pipeline.ingest.ingest import (build_query, find_duplicate, format_report, ingest, ingest_window,
                                    iso, load_raw, parse_headers)
from pipeline.store.db import check_db, migrate, open_db, schema_version

REG = load_registry()
# Thursday 2026-10-01 16:00 UTC (12:00 ET); a Friday for the weekly-lookback test.
THU = datetime(2026, 10, 1, 16, 0, tzinfo=timezone.utc)
FRI = datetime(2026, 10, 2, 16, 0, tzinfo=timezone.utc)


def eml(from_: str, subject: str, *, to: str = "notifyy1008@gmail.com", msgid: str = "",
        body_kb: int = 60) -> bytes:
    head = (f"From: {from_}\r\nTo: {to}\r\nSubject: {subject}\r\nDate: Thu, 01 Oct 2026 10:39:18 +0000\r\n"
            + (f"Message-ID: {msgid}\r\n" if msgid else "") + "Content-Type: text/plain; charset=utf-8\r\n\r\n")
    return head.encode() + b"x" * (body_kb * 1024)


class FakeGmail:
    """Messages keyed by Gmail id; list_ids returns newest first like Gmail."""

    def __init__(self):
        self.msgs: dict[str, RawMessage] = {}
        self.queries: list[str] = []
        self.fetched: list[str] = []
        self.fail: dict[str, Exception] = {}

    def add(self, gid: str, raw: bytes, at: datetime, labels=("INBOX",)) -> "FakeGmail":
        self.msgs[gid] = RawMessage(gid, "t" + gid, tuple(labels), int(at.timestamp() * 1000), len(raw), raw)
        return self

    def list_ids(self, query: str):
        self.queries.append(query)
        yield from sorted(self.msgs, key=lambda g: self.msgs[g].internal_date_ms, reverse=True)

    def get_raw(self, gid: str) -> RawMessage:
        self.fetched.append(gid)
        if gid in self.fail:
            raise self.fail.pop(gid)
        return self.msgs[gid]


@pytest.fixture
def conn(settings):
    c = open_db(settings.database_url)
    migrate(c)
    yield c
    c.close()


def _tldr_triple(g: FakeGmail, base: datetime, subject="Gemini 4 \U0001F916, Apple smart home"):
    # Real shape (2026-10-01): three +alias copies, distinct Message-IDs, 17 min apart, sizes ~0.1% apart.
    g.add("a1", eml("TLDR <dan@tldrnewsletter.com>", subject, msgid="<m1@ses>"), base)
    g.add("a2", eml("TLDR <dan@tldrnewsletter.com>", subject, to="notifyy1008+techai@gmail.com",
                    msgid="<m2@ses>") + b"yy", base + timedelta(minutes=7))
    g.add("a3", eml("TLDR <dan@tldrnewsletter.com>", subject, to="notifyy1008+github@gmail.com",
                    msgid="<m3@ses>") + b"zzz", base + timedelta(minutes=17))


# ------------------------------------------------------------------ schema
def test_migrate_is_idempotent(settings):
    with open_db(settings.database_url) as c:
        assert migrate(c) == ["001_content_store"] and migrate(c) == [] and schema_version(c) == 1
    ok, detail = check_db(settings.database_url)
    assert ok and "schema v1" in detail


def test_check_db_does_not_create_schema(settings):
    ok, detail = check_db(settings.database_url)
    assert ok and "schema v0" in detail
    with open_db(settings.database_url) as c:
        assert c.one("SELECT name FROM sqlite_master WHERE name='schema_migrations'") is None


# ------------------------------------------------------------------ window
def test_first_run_window_and_query(conn):
    start, end = ingest_window(REG, "tech", conn, THU)
    assert end - start == timedelta(hours=24)
    q = build_query(REG, "tech", start)
    assert q.startswith("from:(") and "dan@tldrnewsletter.com" in q and f"after:{int(start.timestamp())}" in q
    assert "markets@axios.com" not in q             # finance-only address stays out of Tech


def test_window_continues_from_last_ok_run_with_overlap(settings, conn):
    g = FakeGmail()
    ingest(settings, REG, "tech", g, conn, now=THU)
    start, _ = ingest_window(REG, "tech", conn, THU + timedelta(hours=6))   # still Thursday
    assert start == THU - timedelta(minutes=10)


def test_friday_tech_looks_back_a_week(conn):
    start, _ = ingest_window(REG, "tech", conn, FRI)
    assert FRI - start == timedelta(days=7)
    fstart, _ = ingest_window(REG, "finance", conn, FRI)
    assert FRI - fstart == timedelta(hours=24)


def test_since_only_widens(settings, conn):
    ingest(settings, REG, "finance", FakeGmail(), conn, now=THU)
    later = THU + timedelta(hours=30)
    start, _ = ingest_window(REG, "finance", conn, later, since=later - timedelta(hours=1))
    assert start == THU - timedelta(minutes=10)     # a later --since cannot open a gap
    start, _ = ingest_window(REG, "finance", conn, later, since=THU - timedelta(days=30))
    assert start == THU - timedelta(days=30)


# ------------------------------------------------------------------ ingest
def test_ingest_archives_and_records(settings, conn):
    g = FakeGmail()
    raw = eml("TLDR Dev <dan@tldrnewsletter.com>", "Pi 1.0 \U0001F916", msgid="<d1@ses>")
    g.add("d1", raw, THU - timedelta(hours=5))
    rep = ingest(settings, REG, "tech", g, conn, now=THU)
    assert rep.status == "ok" and rep.new == 1
    row = conn.one("SELECT * FROM documents WHERE id='d1'")
    assert row["source_id"] == "tldr_dev" and row["kind"] == "unknown" and row["title"] == "Pi 1.0 \U0001F916"
    assert row["received_day_et"] == "2026-10-01" and row["received_at"] == "2026-10-01T11:00:00Z"
    assert load_raw(conn, "d1") == raw                                    # byte-exact, sha-checked
    assert conn.scalar("SELECT LENGTH(data) AS n FROM document_raw") < len(raw) / 5   # gzip
    stats = json.loads(conn.scalar("SELECT stats FROM ingest_runs"))
    assert stats["per_source"]["tldr_dev"]["new"] == 1 and "superhuman" in stats["silent_sources"]


def test_rerun_same_window_inserts_nothing_and_fetches_nothing(settings, conn):
    g = FakeGmail()
    _tldr_triple(g, THU - timedelta(hours=6))
    ingest(settings, REG, "tech", g, conn, now=THU)
    fetched = len(g.fetched)
    rep = ingest(settings, REG, "tech", g, conn, now=THU, since=THU - timedelta(days=1))
    assert rep.new == 0 and rep.duplicates == 0 and rep.known == 3 and len(g.fetched) == fetched
    assert conn.scalar("SELECT COUNT(*) FROM documents") == 1


def test_tldr_alias_copies_collapse_to_one(settings, conn):
    g = FakeGmail()
    _tldr_triple(g, THU - timedelta(hours=6))
    rep = ingest(settings, REG, "tech", g, conn, now=THU)
    assert rep.new == 1 and rep.duplicates == 2
    assert conn.scalar("SELECT id FROM documents") == "a1"    # oldest copy is canonical
    dups = conn.all("SELECT external_id, canonical_document_id, reason FROM duplicates ORDER BY external_id")
    assert [tuple(d.values()) for d in dups] == [("a2", "a1", "alias-copy"), ("a3", "a1", "alias-copy")]
    assert conn.scalar("SELECT COUNT(*) AS n FROM document_raw") == 1         # copies are not stored


def test_same_message_id_is_a_duplicate(settings, conn):
    g = FakeGmail()
    g.add("x1", eml("Axios Markets <markets@axios.com>", "A", msgid="<same@x>"), THU - timedelta(hours=3))
    g.add("x2", eml("Axios Markets <markets@axios.com>", "B", msgid="<same@x>"), THU - timedelta(hours=2))
    rep = ingest(settings, REG, "finance", g, conn, now=THU)
    assert rep.new == 1 and conn.scalar("SELECT reason FROM duplicates") == "message-id"


@pytest.mark.parametrize("gap,extra_kb,dup", [
    (timedelta(minutes=17), 0, True),
    (timedelta(hours=2, minutes=59), 0, True),
    (timedelta(hours=3, minutes=1), 0, False),     # e.g. a PM edition with a reused subject
    (timedelta(minutes=5), 20, False),             # same subject, clearly different body
])
def test_alias_copy_rule_limits(settings, conn, gap, extra_kb, dup):
    g = FakeGmail()
    g.add("p", eml("TLDR <dan@tldrnewsletter.com>", "Same", msgid="<p@x>"), THU - timedelta(hours=8))
    g.add("q", eml("TLDR <dan@tldrnewsletter.com>", "Same", msgid="<q@x>", body_kb=60 + extra_kb),
          THU - timedelta(hours=8) + gap)
    rep = ingest(settings, REG, "tech", g, conn, now=THU)
    assert (rep.duplicates == 1) is dup and rep.new == (1 if dup else 2)


def test_empty_subject_never_collapses(settings, conn):
    g = FakeGmail()
    g.add("e1", eml("TLDR <dan@tldrnewsletter.com>", "", msgid="<e1@x>"), THU - timedelta(hours=3))
    g.add("e2", eml("TLDR <dan@tldrnewsletter.com>", "", msgid="<e2@x>"), THU - timedelta(hours=2))
    assert ingest(settings, REG, "tech", g, conn, now=THU).new == 2


def test_shared_address_routes_by_display_name(settings, conn):
    g = FakeGmail()
    g.add("t1", eml("TLDR <dan@tldrnewsletter.com>", "a", msgid="<t1@x>"), THU - timedelta(hours=3))
    g.add("t2", eml("TLDR Dev <dan@tldrnewsletter.com>", "b", msgid="<t2@x>"), THU - timedelta(hours=2))
    g.add("t3", eml("TLDR AI <dan@tldrnewsletter.com>", "c", msgid="<t3@x>"), THU - timedelta(hours=1))
    rep = ingest(settings, REG, "tech", g, conn, now=THU)
    rows = {r["id"]: r["source_id"] for r in conn.all("SELECT id, source_id FROM documents")}
    assert rows == {"t1": "tldr", "t2": "tldr_dev"}
    assert rep.unmatched == ["TLDR AI <dan@tldrnewsletter.com>"] and rep.status == "ok"
    assert conn.scalar("SELECT reason FROM ingest_skips WHERE external_id='t3'") == "unmatched"


def test_pragmatic_series_recorded(settings, conn):
    g = FakeGmail()
    g.add("s1", eml("The Pragmatic Engineer <pragmaticengineer+the-pulse@substack.com>", "The Pulse", msgid="<s1@x>"),
          THU - timedelta(hours=2))
    ingest(settings, REG, "tech", g, conn, now=THU)
    assert tuple(conn.one("SELECT source_id, series FROM documents").values()) == ("pragmatic_engineer", "pulse")


def test_spam_is_ingested_and_flagged_drafts_skipped(settings, conn):
    g = FakeGmail()
    g.add("sp", eml("Axios Markets <markets@axios.com>", "Spammy", msgid="<sp@x>"), THU - timedelta(hours=2),
          labels=("SPAM",))
    g.add("dr", eml("Axios Markets <markets@axios.com>", "Draft", msgid="<dr@x>"), THU - timedelta(hours=1),
          labels=("DRAFT",))
    rep = ingest(settings, REG, "finance", g, conn, now=THU)
    assert rep.new == 1 and rep.drafts == 1 and rep.spam == ["axios_markets: Spammy"]
    assert conn.scalar("SELECT in_spam FROM documents") == 1
    assert "WARNING landed in Spam" in format_report(rep, REG)


def test_message_error_makes_run_partial_and_is_retried(settings, conn):
    g = FakeGmail()
    g.add("ok", eml("Axios Markets <markets@axios.com>", "One", msgid="<1@x>"), THU - timedelta(hours=3))
    g.add("bad", eml("Axios Markets <markets@axios.com>", "Two", msgid="<2@x>"), THU - timedelta(hours=2))
    g.fail["bad"] = GmailApiError("Gmail API /messages/bad: HTTP 500")
    rep = ingest(settings, REG, "finance", g, conn, now=THU)
    assert rep.status == "partial" and rep.new == 1 and "bad: GmailApiError" in rep.errors[0]
    # watermark did not advance: the next run covers the same window and picks up the failure
    start, _ = ingest_window(REG, "finance", conn, THU + timedelta(hours=1))
    assert start == THU - timedelta(hours=24)            # the partial run's own window start
    rep2 = ingest(settings, REG, "finance", g, conn, now=THU + timedelta(hours=1))
    assert rep2.status == "ok" and rep2.new == 1 and rep2.known == 1


def test_failed_backfill_is_retried_even_without_since(settings, conn):
    # Live bug 2026-10-04: a --since backfill run ended partial; the next plain run used the
    # 24 h default, finished OK and would have skipped the failed messages forever.
    g = FakeGmail()
    old = THU - timedelta(days=6)
    g.add("old", eml("Axios Markets <markets@axios.com>", "Old", msgid="<o@x>"), old)
    g.fail["old"] = GmailApiError("HTTP 403 (userRateLimitExceeded)")
    rep = ingest(settings, REG, "finance", g, conn, now=THU, since=THU - timedelta(days=7))
    assert rep.status == "partial"
    start, _ = ingest_window(REG, "finance", conn, THU + timedelta(hours=1))
    assert start == THU - timedelta(days=7)
    rep2 = ingest(settings, REG, "finance", g, conn, now=THU + timedelta(hours=1))
    assert rep2.status == "ok" and rep2.new == 1
    # once covered, the normal watermark applies again
    assert ingest_window(REG, "finance", conn, THU + timedelta(hours=2))[0] == THU + timedelta(minutes=50)


def test_crashed_running_run_is_covered(settings, conn):
    conn.execute("INSERT INTO ingest_runs (channel, scope, window_start, window_end, query, status, started_at) "
                 "VALUES ('email', 'tech', '2026-09-20T00:00:00Z', '2026-10-01T00:00:00Z', 'q', 'running', 'x')")
    assert ingest_window(REG, "tech", conn, THU)[0] == datetime(2026, 9, 20, tzinfo=timezone.utc)


def test_auth_failure_marks_run_failed(settings, conn):
    class Broken(FakeGmail):
        def list_ids(self, query):
            raise GmailAuthError("refresh token expired or revoked (invalid_grant)")
    with pytest.raises(GmailAuthError):
        ingest(settings, REG, "tech", Broken(), conn, now=THU)
    assert conn.scalar("SELECT status FROM ingest_runs") == "failed"
    assert ingest_window(REG, "tech", conn, THU)[0] == THU - timedelta(hours=24)


def test_email_shared_by_two_editions_is_stored_once(settings, conn):
    g = FakeGmail()
    g.add("sb", eml("Semafor Business <business@semafor.com>", "Biz", msgid="<sb@x>"), THU - timedelta(hours=2))
    ingest(settings, REG, "tech", g, conn, now=THU)
    rep = ingest(settings, REG, "finance", g, conn, now=THU)
    assert rep.new == 0 and rep.known == 1 and rep.per_source["semafor_business"].known == 1
    assert conn.scalar("SELECT COUNT(*) FROM documents") == 1


def test_malformed_header_does_not_lose_the_email():
    raw = b"From: TLDR <dan@tldrnewsletter.com>\r\nSubject: =?utf-8?q?broken?=?=\r\nMessage-ID: <z@x>\r\n\r\nbody"
    h = parse_headers(raw)
    assert h.from_ == "TLDR <dan@tldrnewsletter.com>" and h.message_id == "<z@x>" and h.subject


def test_find_duplicate_needs_same_source(settings, conn):
    g = FakeGmail()
    g.add("f1", eml("TLDR <dan@tldrnewsletter.com>", "Same", msgid="<f1@x>"), THU - timedelta(hours=2))
    ingest(settings, REG, "tech", g, conn, now=THU)
    h = parse_headers(eml("TLDR Dev <dan@tldrnewsletter.com>", "Same", msgid="<f2@x>"))
    assert find_duplicate(conn, "tldr_dev", h, THU - timedelta(hours=2), 60 * 1024) is None
    assert iso(THU) == "2026-10-01T16:00:00Z"


# ------------------------------------------------------------------ content store
def test_sources_are_mirrored_from_the_registry(settings, conn):
    ingest(settings, REG, "tech", FakeGmail(), conn, now=THU)
    row = conn.one("SELECT * FROM sources WHERE id = 'semafor_business'")
    assert row["kind"] == "newsletter" and set(json.loads(row["editions"])) == {"tech", "finance"}
    assert json.loads(row["config"])["match"] == [{"address": "business@semafor.com"}]
    assert conn.scalar("SELECT COUNT(*) AS n FROM sources") == len(REG.sources)


def test_document_fields(settings, conn):
    g = FakeGmail()
    g.add("d2", eml("TLDR Dev <dan@tldrnewsletter.com>", "Hi", msgid="<d2@x>"), THU - timedelta(hours=5))
    ingest(settings, REG, "tech", g, conn, now=THU)
    d = conn.one("SELECT * FROM documents WHERE id = 'd2'")
    assert (d["channel"], d["external_id"], d["author"]) == ("email", "d2", "TLDR Dev")
    assert d["published_at"] == "2026-10-01T10:39:18Z"          # from the Date header
    assert conn.scalar("SELECT content_type FROM document_raw") == "message/rfc822"


def test_all_four_layers_link_up(settings, conn):
    """A story written through every layer stays joinable back to its newsletter email."""
    g = FakeGmail()
    g.add("L1", eml("TLDR <dan@tldrnewsletter.com>", "Starlink", msgid="<L1@x>"), THU - timedelta(hours=2))
    ingest(settings, REG, "tech", g, conn, now=THU)
    with conn.transaction():
        sec = conn.scalar("INSERT INTO blocks (document_id, seq, type, content) VALUES ('L1', 0, 'section', "
                          "'Big Tech') RETURNING id")
        conn.execute("INSERT INTO blocks (document_id, seq, parent_id, depth, type, content) "
                     "VALUES ('L1', 1, ?, 1, 'paragraph', 'Starlink hit 8M users.')", (sec,))
        item = conn.scalar("INSERT INTO items (document_id, source_id, seq, section, headline, summary, extractor, "
                           "created_at) VALUES ('L1', 'tldr', 0, 'Big Tech', 'Starlink tops 8M', 'Users grew.', "
                           "'rule:test', 'x') RETURNING id")
        conn.execute("INSERT INTO item_facts (item_id, seq, kind, claim, value, unit, evidence, verified) "
                     "VALUES (?, 0, 'number', 'Starlink has 8M users', 8000000, 'users', '8M users', 1)", (item,))
        ent = conn.scalar("INSERT INTO entities (kind, name, canonical_key) VALUES ('company', 'SpaceX', "
                          "'company:spacex') RETURNING id")
        conn.execute("INSERT INTO item_entities (item_id, entity_id, role) VALUES (?, ?, 'subject')", (item, ent))
        conn.execute("INSERT INTO topics (id, label) VALUES ('tech', 'Tech')")
        conn.execute("INSERT INTO topics (id, parent_id, label) VALUES ('tech.space', 'tech', 'Space')")
        conn.execute("INSERT INTO item_topics VALUES (?, 'tech.space', 0.9, 'rule:test')", (item,))
        story = conn.scalar("INSERT INTO stories (title, first_seen_at, last_seen_at, created_at, updated_at) "
                            "VALUES ('Starlink growth', 'a', 'b', 'c', 'd') RETURNING id")
        conn.execute("INSERT INTO story_items VALUES (?, ?, 1.0, 'url')", (story, item))
    row = conn.one(
        "SELECT d.source_id, d.title, i.headline, f.value, e.name, t.label, s.title AS story "
        "FROM story_items si JOIN stories s ON s.id = si.story_id JOIN items i ON i.id = si.item_id "
        "JOIN documents d ON d.id = i.document_id JOIN item_facts f ON f.item_id = i.id "
        "JOIN item_entities ie ON ie.item_id = i.id JOIN entities e ON e.id = ie.entity_id "
        "JOIN item_topics it ON it.item_id = i.id JOIN topics t ON t.id = it.topic_id")
    assert row == {"source_id": "tldr", "title": "Starlink", "headline": "Starlink tops 8M", "value": 8000000,
                   "name": "SpaceX", "label": "Space", "story": "Starlink growth"}
    with conn.transaction():
        conn.execute("DELETE FROM documents WHERE id = 'L1'")       # derived layers go with their document
    assert conn.scalar("SELECT COUNT(*) AS n FROM items") == 0 and conn.scalar("SELECT COUNT(*) AS n FROM blocks") == 0
