"""Step 1: Ingest. Fetch every new email for an edition's sources, losslessly and exactly once.

    with open_db(settings.database_url) as db:
        report = ingest(settings, registry, "tech", gmail, db)

Storage: the shared Supabase Postgres (layer 1 of the content store, see
store/migrations/postgres/001_content_store.sql). Each email is one `documents` row
(channel 'email') plus its byte-exact original (gzip) in `document_raw`, written in ONE
transaction. Nothing is stored locally.

Window: from the edition's last successful ingest (minus a 10-minute overlap for Gmail's
indexing delay) to now. First run: `first_run_hours` back. On weekly-lookback days (Tech on
Fridays) the window reaches back `weekly_lookback_days`. An explicit `since` can only widen
the window (backfill), never open a gap.

Exactly once:
  - a Gmail id already stored (as an email or a duplicate) is never fetched again, so
    re-running the same window inserts 0 rows and makes 0 raw fetches;
  - the same issue delivered more than once is collapsed. TLDR arrives once per +alias, each
    copy with its OWN Message-ID, up to ~20 min apart (seen 2026-10-01/02). So a copy is a
    duplicate if it has the same Message-ID, or the same source + identical subject within
    3 h and a size within 10%.
A run with any per-message error is `partial`: its rows are kept, but the watermark does not
advance, so the next run covers the window again (idempotently) and retries the failures.
Only one ingest runs at a time across the whole team (database advisory lock).
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from email import policy
from email.message import Message
from email.parser import BytesHeaderParser
from email.utils import parseaddr, parsedate_to_datetime
from zoneinfo import ZoneInfo

from ..config.registry import Registry
from ..config.settings import Settings
from ..store.catalog import sync_sources
from ..store.db import Db, DbError
from ..store.raw import pack, sha256
from .gmail import GmailApiError, GmailClient, RawMessage

OVERLAP = timedelta(minutes=10)
DUP_WINDOW = timedelta(hours=3)
DUP_SIZE_TOLERANCE = 0.10
_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _now() -> str:
    return iso(datetime.now(timezone.utc))


# ------------------------------------------------------------------ window
def last_ok_window_end(db: Db, edition: str) -> datetime | None:
    v = db.scalar("SELECT MAX(window_end) AS v FROM ingest_runs WHERE channel = 'email' AND scope = ? "
                  "AND status = 'ok'", (edition,))
    return parse_iso(v) if v else None


def unfinished_window_start(db: Db, edition: str) -> datetime | None:
    """Earliest window_start of any run after the last OK one that did not finish OK
    (partial, failed, or 'running' after a crash). The next window must cover it."""
    v = db.scalar(
        "SELECT MIN(window_start) AS v FROM ingest_runs WHERE channel = 'email' AND scope = ? "
        "AND status != 'ok' AND id > COALESCE((SELECT MAX(id) FROM ingest_runs WHERE channel = 'email' "
        "AND scope = ? AND status = 'ok'), 0)",
        (edition, edition))
    return parse_iso(v) if v else None


def ingest_window(reg: Registry, edition: str, db: Db, now: datetime,
                  since: datetime | None = None) -> tuple[datetime, datetime]:
    w = reg.editions[edition].window
    last = last_ok_window_end(db, edition)
    start = last - OVERLAP if last else now - timedelta(hours=w.first_run_hours)
    pending = unfinished_window_start(db, edition)
    if pending is not None:
        start = min(start, pending)  # never leave the window of an unfinished run uncovered
    local_day = _WEEKDAYS[now.astimezone(ZoneInfo(reg.timezone)).weekday()]
    if w.weekly_lookback_days and local_day in w.weekly_lookback_weekdays:
        start = min(start, now - timedelta(days=w.weekly_lookback_days))
    if since is not None:
        start = min(start, since)  # backfill only widens; it can never skip mail
    return start, now


def build_query(reg: Registry, edition: str, start: datetime) -> str:
    addresses = sorted({m.address for s in reg.sources_for(edition) for m in s.match})
    return f"from:({' OR '.join(addresses)}) after:{int(start.timestamp())}"


# ------------------------------------------------------------------ report
@dataclass
class SourceCount:
    listed: int = 0
    new: int = 0
    duplicate: int = 0
    known: int = 0
    spam: int = 0


@dataclass
class IngestReport:
    edition: str
    window_start: str
    window_end: str
    query: str
    run_id: int | None = None
    status: str = "running"
    listed: int = 0
    known: int = 0
    new: int = 0
    duplicates: int = 0
    stored_bytes: int = 0                                  # compressed raw bytes written
    per_source: dict[str, SourceCount] = field(default_factory=dict)
    silent_sources: list[str] = field(default_factory=list)
    spam: list[str] = field(default_factory=list)          # "source: subject"
    trash: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)     # From headers no matcher accepted
    drafts: int = 0
    errors: list[str] = field(default_factory=list)        # "msg_id: error" (no message text)

    def count(self, source_id: str) -> SourceCount:
        return self.per_source.setdefault(source_id, SourceCount())

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


# ------------------------------------------------------------------ headers
_HDR = BytesHeaderParser(policy=policy.default)


def _header(msg: Message, name: str) -> str:
    try:
        value = msg.get(name)
    except Exception:  # noqa: BLE001 - a malformed header must not lose the email: use it undecoded
        value = next((v for k, v in msg.raw_items() if k.lower() == name.lower()), "")
    return re.sub(r"\s+", " ", str(value or "")).strip()


@dataclass(frozen=True)
class Headers:
    from_: str
    to: str
    subject: str
    date: str
    message_id: str


def parse_headers(raw: bytes) -> Headers:
    msg = _HDR.parsebytes(raw)
    return Headers(from_=_header(msg, "From"), to=_header(msg, "To"), subject=_header(msg, "Subject"),
                   date=_header(msg, "Date"), message_id=_header(msg, "Message-ID"))


# ------------------------------------------------------------------ dedupe
def find_duplicate(db: Db, source_id: str, h: Headers, received: datetime,
                   size: int) -> tuple[str, str] | None:
    """(canonical msg_id, reason) if this is another copy of a stored email, else None."""
    if h.message_id:
        v = db.scalar("SELECT id FROM documents WHERE rfc_message_id = ? LIMIT 1", (h.message_id,))
        if v:
            return v, "message-id"
    if not h.subject:
        return None  # never collapse on an empty subject
    rows = db.all(
        "SELECT id, size_bytes FROM documents WHERE source_id = ? AND title = ? "
        "AND received_at BETWEEN ? AND ? ORDER BY received_at",
        (source_id, h.subject, iso(received - DUP_WINDOW), iso(received + DUP_WINDOW)))
    for r in rows:
        if abs(size - r["size_bytes"]) <= DUP_SIZE_TOLERANCE * max(size, r["size_bytes"], 1):
            return r["id"], "alias-copy"
    return None


# ------------------------------------------------------------------ ingest
def _known(db: Db) -> dict[str, str]:
    """Every stored Gmail id (documents + duplicates) -> its source_id."""
    rows = db.all("SELECT external_id AS gid, source_id FROM documents WHERE channel = 'email' UNION ALL "
                  "SELECT u.external_id, d.source_id FROM duplicates u "
                  "JOIN documents d ON d.id = u.canonical_document_id WHERE u.channel = 'email'")
    return {r["gid"]: r["source_id"] for r in rows}


def ingest(settings: Settings, reg: Registry, edition: str, gmail: GmailClient, db: Db,
           now: datetime | None = None, since: datetime | None = None) -> IngestReport:
    if edition not in reg.editions:
        raise ValueError(f"unknown edition {edition!r}")
    with db.exclusive("pipeline:ingest"):  # one ingest at a time across the whole team
        sync_sources(db, reg)
        now = now or datetime.now(timezone.utc)
        start, end = ingest_window(reg, edition, db, now, since)
        query = build_query(reg, edition, start)
        rep = IngestReport(edition=edition, window_start=iso(start), window_end=iso(end), query=query)
        rep.run_id = db.scalar(
            "INSERT INTO ingest_runs (channel, scope, window_start, window_end, query, status, started_at) "
            "VALUES ('email', ?, ?, ?, ?, 'running', ?) RETURNING id",
            (edition, rep.window_start, rep.window_end, query, iso(now)))
        try:
            _run(reg, gmail, db, rep)
            rep.status = "partial" if rep.errors else "ok"
        except BaseException as e:
            rep.status = "failed"
            rep.errors.append(f"run: {e.__class__.__name__}: {e}")
            raise
        finally:
            rep.silent_sources = [s.id for s in reg.sources_for(edition) if rep.count(s.id).listed == 0]
            rep.per_source = {k: rep.per_source[k] for k in sorted(rep.per_source)}
            db.execute("UPDATE ingest_runs SET status = ?, finished_at = ?, stats = ? WHERE id = ?",
                       (rep.status, _now(), rep.to_json(), rep.run_id))
    return rep


def _run(reg: Registry, gmail: GmailClient, db: Db, rep: IngestReport) -> None:
    tz = ZoneInfo(reg.timezone)
    known = _known(db)
    ids = list(gmail.list_ids(rep.query))
    rep.listed = len(ids)
    for msg_id in reversed(ids):  # Gmail lists newest first: oldest copy becomes canonical
        if msg_id in known:
            rep.known += 1
            c = rep.count(known[msg_id])
            c.listed += 1
            c.known += 1
            continue
        try:
            msg = gmail.get_raw(msg_id)
            source_id = _ingest_one(reg, db, rep, msg, tz)
        except (GmailApiError, DbError, OSError, ValueError) as e:
            rep.errors.append(f"{msg_id}: {e.__class__.__name__}: {str(e)[:200]}")
            continue
        if source_id:
            known[msg_id] = source_id


def _ingest_one(reg: Registry, db: Db, rep: IngestReport, msg: RawMessage, tz: ZoneInfo) -> str | None:
    """Store one fetched message. Returns its source_id if stored or collapsed, else None."""
    if "DRAFT" in msg.label_ids:
        rep.drafts += 1
        return None
    h = parse_headers(msg.raw)
    received = datetime.fromtimestamp(msg.internal_date_ms / 1000, tz=timezone.utc)
    hit = reg.match_sender(h.from_)  # ValueError if ambiguous: config bug, reported per message
    if hit is None:
        rep.unmatched.append(h.from_)
        db.execute(
            "INSERT INTO ingest_skips (channel, external_id, reason, from_header, title, received_at, "
            "last_seen_run_id) VALUES ('email', ?, 'unmatched', ?, ?, ?, ?) ON CONFLICT (channel, external_id) "
            "DO UPDATE SET last_seen_run_id = excluded.last_seen_run_id",
            (msg.id, h.from_, h.subject, iso(received), rep.run_id))
        return None
    source, matcher = hit
    c = rep.count(source.id)
    c.listed += 1
    in_spam, in_trash = "SPAM" in msg.label_ids, "TRASH" in msg.label_ids
    size = len(msg.raw)
    dup = find_duplicate(db, source.id, h, received, size)
    if dup:
        with db.transaction():
            db.execute(
                "INSERT INTO duplicates (channel, external_id, canonical_document_id, reason, recipient, "
                "received_at, ingest_run_id, ingested_at) VALUES ('email', ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (channel, external_id) DO NOTHING",
                (msg.id, dup[0], dup[1], h.to, iso(received), rep.run_id, _now()))
            db.execute("DELETE FROM ingest_skips WHERE channel = 'email' AND external_id = ?", (msg.id,))
        c.duplicate += 1
        rep.duplicates += 1
        return source.id

    blob = pack(msg.raw)
    with db.transaction():  # the row and its raw copy land together or not at all
        cur = db.execute(
            "INSERT INTO documents (id, channel, external_id, source_id, series, title, author, published_at, "
            "received_at, received_day_et, rfc_message_id, thread_id, from_header, to_header, label_ids, in_spam, "
            "in_trash, size_bytes, sha256, ingest_run_id, ingested_at) "
            "VALUES (?, 'email', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (id) DO NOTHING",
            (msg.id, msg.id, source.id, matcher.series, h.subject, parseaddr(h.from_)[0] or None,
             _date_header(h.date), iso(received), received.astimezone(tz).date().isoformat(),
             h.message_id or None, msg.thread_id, h.from_, h.to, json.dumps(list(msg.label_ids)),
             in_spam, in_trash, size, sha256(msg.raw), rep.run_id, _now()))
        inserted = cur.rowcount == 1
        if inserted:
            db.execute("INSERT INTO document_raw (document_id, content_type, encoding, data) "
                       "VALUES (?, 'message/rfc822', 'gzip', ?)", (msg.id, blob))
        db.execute("DELETE FROM ingest_skips WHERE channel = 'email' AND external_id = ?", (msg.id,))
    if not inserted:  # a concurrent run stored it first
        c.known += 1
        rep.known += 1
        return source.id
    c.new += 1
    rep.new += 1
    rep.stored_bytes += len(blob)
    if in_spam:
        c.spam += 1
        rep.spam.append(f"{source.id}: {h.subject[:80]}")
    if in_trash:
        rep.trash.append(f"{source.id}: {h.subject[:80]}")
    return source.id


def load_raw(db: Db, document_id: str) -> bytes:
    """The byte-exact original, integrity-checked against its stored sha256."""
    from ..store.raw import unpack
    row = db.one("SELECT r.data, d.sha256 FROM document_raw r JOIN documents d ON d.id = r.document_id "
                 "WHERE r.document_id = ?", (document_id,))
    if row is None:
        raise KeyError(document_id)
    return unpack(row["data"], row["sha256"])


def _date_header(value: str) -> str | None:
    """RFC 2822 Date header -> ISO UTC, or None if missing/unparseable (received_at still holds)."""
    try:
        dt = parsedate_to_datetime(value) if value else None
    except (TypeError, ValueError, IndexError):
        return None
    if dt is None:
        return None
    return iso(dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc))


def format_report(rep: IngestReport, reg: Registry) -> str:
    lines = [f"ingest {rep.edition}  run #{rep.run_id}  status={rep.status.upper()}",
             f"window {rep.window_start} -> {rep.window_end}",
             f"listed {rep.listed} | new {rep.new} | duplicates {rep.duplicates} | already stored {rep.known}"
             + (f" | drafts {rep.drafts}" if rep.drafts else "")
             + (f" | {rep.stored_bytes / 1024:.0f} KB stored (gzip)" if rep.stored_bytes else ""), ""]
    width = max([len(s.id) for s in reg.sources] + [6])
    lines.append(f"  {'source':<{width}}  listed  new  dup  known  spam")
    for sid, c in rep.per_source.items():
        lines.append(f"  {sid:<{width}}  {c.listed:>6}  {c.new:>3}  {c.duplicate:>3}  {c.known:>5}  {c.spam:>4}")
    if rep.silent_sources:
        lines.append(f"\n  no mail in window: {', '.join(rep.silent_sources)}")
    if rep.spam:
        lines.append("\n  WARNING landed in Spam (ingested; fix with a Gmail filter / 'Not spam'):")
        lines += [f"    - {x}" for x in rep.spam]
    if rep.trash:
        lines.append("\n  NOTE in Trash (ingested): " + "; ".join(rep.trash))
    if rep.unmatched:
        lines.append("\n  UNMATCHED senders (registered address, no matcher; add to sources.yaml if wanted):")
        lines += [f"    - {x}" for x in sorted(set(rep.unmatched))]
    if rep.errors:
        lines.append("\n  ERRORS (watermark not advanced; next run retries):")
        lines += [f"    - {x}" for x in rep.errors]
    return "\n".join(lines)
