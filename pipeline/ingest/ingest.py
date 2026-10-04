"""Step 1: Ingest. Fetch every new email for an edition's sources, losslessly and exactly once.

    report = ingest(settings, registry, "tech", gmail, conn)

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
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from email import policy
from email.message import Message
from email.parser import BytesHeaderParser
from zoneinfo import ZoneInfo

from ..config.registry import Registry
from ..config.settings import Settings
from ..store.archive import eml_relpath, write_eml
from .gmail import GmailApiError, GmailClient, RawMessage

OVERLAP = timedelta(minutes=10)
DUP_WINDOW = timedelta(hours=3)
DUP_SIZE_TOLERANCE = 0.10
_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


# ------------------------------------------------------------------ window
def last_ok_window_end(conn: sqlite3.Connection, edition: str) -> datetime | None:
    row = conn.execute("SELECT MAX(window_end) FROM ingest_runs WHERE edition = ? AND status = 'ok'",
                       (edition,)).fetchone()
    return parse_iso(row[0]) if row and row[0] else None


def unfinished_window_start(conn: sqlite3.Connection, edition: str) -> datetime | None:
    """Earliest window_start of any run after the last OK one that did not finish OK
    (partial, failed, or 'running' after a crash). The next window must cover it."""
    row = conn.execute(
        "SELECT MIN(window_start) FROM ingest_runs WHERE edition = ? AND status != 'ok' AND id > "
        "COALESCE((SELECT MAX(id) FROM ingest_runs WHERE edition = ? AND status = 'ok'), 0)",
        (edition, edition)).fetchone()
    return parse_iso(row[0]) if row and row[0] else None


def ingest_window(reg: Registry, edition: str, conn: sqlite3.Connection, now: datetime,
                  since: datetime | None = None) -> tuple[datetime, datetime]:
    w = reg.editions[edition].window
    last = last_ok_window_end(conn, edition)
    start = last - OVERLAP if last else now - timedelta(hours=w.first_run_hours)
    pending = unfinished_window_start(conn, edition)
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
        d = asdict(self)
        return json.dumps(d, ensure_ascii=False, sort_keys=True)


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
def find_duplicate(conn: sqlite3.Connection, source_id: str, h: Headers, received: datetime,
                   size: int) -> tuple[str, str] | None:
    """(canonical msg_id, reason) if this is another copy of a stored email, else None."""
    if h.message_id:
        row = conn.execute("SELECT msg_id FROM emails WHERE rfc_message_id = ? LIMIT 1",
                           (h.message_id,)).fetchone()
        if row:
            return row[0], "message-id"
    if not h.subject:
        return None  # never collapse on an empty subject
    rows = conn.execute(
        "SELECT msg_id, size_bytes FROM emails WHERE source_id = ? AND subject = ? "
        "AND received_at BETWEEN ? AND ? ORDER BY received_at",
        (source_id, h.subject, iso(received - DUP_WINDOW), iso(received + DUP_WINDOW))).fetchall()
    for msg_id, other in rows:
        if abs(size - other) <= DUP_SIZE_TOLERANCE * max(size, other, 1):
            return msg_id, "alias-copy"
    return None


# ------------------------------------------------------------------ ingest
def _known_ids(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT msg_id FROM emails UNION SELECT msg_id FROM email_duplicates").fetchall()
    return {r[0] for r in rows}


def ingest(settings: Settings, reg: Registry, edition: str, gmail: GmailClient, conn: sqlite3.Connection,
           now: datetime | None = None, since: datetime | None = None) -> IngestReport:
    if edition not in reg.editions:
        raise ValueError(f"unknown edition {edition!r}")
    now = now or datetime.now(timezone.utc)
    start, end = ingest_window(reg, edition, conn, now, since)
    query = build_query(reg, edition, start)
    rep = IngestReport(edition=edition, window_start=iso(start), window_end=iso(end), query=query)
    cur = conn.execute("INSERT INTO ingest_runs (edition, window_start, window_end, query, status, started_at) "
                       "VALUES (?, ?, ?, ?, 'running', ?)", (edition, rep.window_start, rep.window_end, query, iso(now)))
    rep.run_id = cur.lastrowid
    try:
        _run(settings, reg, gmail, conn, rep)
        rep.status = "partial" if rep.errors else "ok"
    except BaseException as e:
        rep.status = "failed"
        rep.errors.append(f"run: {e.__class__.__name__}: {e}")
        raise
    finally:
        edition_sources = [s.id for s in reg.sources_for(edition)]
        rep.silent_sources = [sid for sid in edition_sources if rep.count(sid).listed == 0]
        rep.per_source = {k: rep.per_source[k] for k in sorted(rep.per_source)}
        conn.execute("UPDATE ingest_runs SET status = ?, finished_at = ?, stats = ? WHERE id = ?",
                     (rep.status, iso(datetime.now(timezone.utc)), rep.to_json(), rep.run_id))
    return rep


def _run(settings: Settings, reg: Registry, gmail: GmailClient, conn: sqlite3.Connection,
         rep: IngestReport) -> None:
    tz = ZoneInfo(reg.timezone)
    known = _known_ids(conn)
    ids = list(gmail.list_ids(rep.query))
    rep.listed = len(ids)
    for msg_id in reversed(ids):  # Gmail lists newest first: oldest copy becomes canonical
        if msg_id in known:
            rep.known += 1
            src = conn.execute("SELECT source_id FROM emails WHERE msg_id = ? UNION ALL "
                               "SELECT e.source_id FROM email_duplicates d JOIN emails e "
                               "ON e.msg_id = d.canonical_msg_id WHERE d.msg_id = ?", (msg_id, msg_id)).fetchone()
            if src:
                c = rep.count(src[0])
                c.listed += 1
                c.known += 1
            continue
        try:
            msg = gmail.get_raw(msg_id)
            _ingest_one(settings, reg, conn, rep, msg, tz)
        except (GmailApiError, OSError, sqlite3.Error, ValueError) as e:
            rep.errors.append(f"{msg_id}: {e.__class__.__name__}: {str(e)[:200]}")
            continue
        known.add(msg_id)


def _ingest_one(settings: Settings, reg: Registry, conn: sqlite3.Connection, rep: IngestReport,
                msg: RawMessage, tz: ZoneInfo) -> None:
    if "DRAFT" in msg.label_ids:
        rep.drafts += 1
        return
    h = parse_headers(msg.raw)
    received = datetime.fromtimestamp(msg.internal_date_ms / 1000, tz=timezone.utc)
    hit = reg.match_sender(h.from_)  # ValueError if ambiguous: config bug, reported per message
    if hit is None:
        rep.unmatched.append(h.from_)
        conn.execute(
            "INSERT INTO ingest_skips (msg_id, reason, from_header, subject, received_at, last_seen_run_id) "
            "VALUES (?, 'unmatched', ?, ?, ?, ?) ON CONFLICT (msg_id) DO UPDATE SET "
            "last_seen_run_id = excluded.last_seen_run_id",
            (msg.id, h.from_, h.subject, iso(received), rep.run_id))
        return
    source, matcher = hit
    c = rep.count(source.id)
    c.listed += 1
    in_spam, in_trash = "SPAM" in msg.label_ids, "TRASH" in msg.label_ids
    size = len(msg.raw)
    dup = find_duplicate(conn, source.id, h, received, size)
    if dup:
        conn.execute(
            "INSERT OR IGNORE INTO email_duplicates (msg_id, canonical_msg_id, reason, to_header, received_at, "
            "ingest_run_id, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (msg.id, dup[0], dup[1], h.to, iso(received), rep.run_id, iso(datetime.now(timezone.utc))))
        conn.execute("DELETE FROM ingest_skips WHERE msg_id = ?", (msg.id,))
        c.duplicate += 1
        rep.duplicates += 1
        return

    relpath = eml_relpath(received.astimezone(tz).date(), source.id, msg.id)
    digest = write_eml(settings.archive_dir, relpath, msg.raw)  # before the row: a row always has its file
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO emails (msg_id, thread_id, source_id, series, rfc_message_id, from_header, "
            "to_header, subject, date_header, received_at, label_ids, in_spam, in_trash, size_bytes, sha256, "
            "eml_path, ingest_run_id, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (msg.id, msg.thread_id, source.id, matcher.series, h.message_id or None, h.from_, h.to, h.subject,
             h.date, iso(received), json.dumps(list(msg.label_ids)), int(in_spam), int(in_trash), size, digest,
             relpath, rep.run_id, iso(datetime.now(timezone.utc))))
        conn.execute("DELETE FROM ingest_skips WHERE msg_id = ?", (msg.id,))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    if cur.rowcount == 0:  # a concurrent run stored it first
        c.known += 1
        rep.known += 1
        return
    c.new += 1
    rep.new += 1
    if in_spam:
        c.spam += 1
        rep.spam.append(f"{source.id}: {h.subject[:80]}")
    if in_trash:
        rep.trash.append(f"{source.id}: {h.subject[:80]}")


def format_report(rep: IngestReport, reg: Registry) -> str:
    lines = [f"ingest {rep.edition}  run #{rep.run_id}  status={rep.status.upper()}",
             f"window {rep.window_start} -> {rep.window_end}",
             f"listed {rep.listed} | new {rep.new} | duplicates {rep.duplicates} | already stored {rep.known}"
             + (f" | drafts {rep.drafts}" if rep.drafts else ""), ""]
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
