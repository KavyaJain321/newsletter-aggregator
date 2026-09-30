"""SQLite store. Schema aligned with PHASE4_DESIGN.md (messages, sync_log)
plus `sources` and `story_cards` for the pipeline. Idempotent on gmail_id.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  source_id     TEXT PRIMARY KEY,
  name          TEXT,
  segment       TEXT,
  publisher     TEXT,
  sender_domain TEXT
);

CREATE TABLE IF NOT EXISTS messages (
  gmail_id        TEXT PRIMARY KEY,
  thread_id       TEXT,
  segment         TEXT,
  newsletter      TEXT,
  source_id       TEXT,
  sender_name     TEXT,
  sender_email    TEXT,
  subject         TEXT,
  sent_date       TEXT,
  internal_ts     INTEGER,
  is_issue        INTEGER DEFAULT 1,
  issue_reason    TEXT,
  labels          TEXT,
  raw_eml_path    TEXT,
  clean_text_path TEXT,
  word_count      INTEGER,
  reading_minutes REAL,
  content_hash    TEXT,
  ingested_at     TEXT,
  enrich_status   TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS story_cards (
  card_id        TEXT PRIMARY KEY,
  gmail_id       TEXT,
  source_id      TEXT,
  segment        TEXT,
  seq            INTEGER,
  headline       TEXT,
  what           TEXT,
  why            TEXT,
  facts_json     TEXT,
  links_json     TEXT,
  extractor      TEXT,
  prompt_version TEXT,
  created_at     TEXT,
  FOREIGN KEY (gmail_id) REFERENCES messages(gmail_id)
);

CREATE TABLE IF NOT EXISTS sync_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at TEXT, segment TEXT, window TEXT,
  scanned INTEGER, new_added INTEGER, duplicates INTEGER,
  status TEXT, notes TEXT
);
"""


def connect(db_path: Path = config.DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_source(conn, source_id, name, segment, publisher="", domain="") -> None:
    conn.execute(
        "INSERT INTO sources(source_id,name,segment,publisher,sender_domain) "
        "VALUES(?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET name=excluded.name",
        (source_id, name, segment, publisher, domain),
    )


def message_exists(conn, gmail_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM messages WHERE gmail_id=?", (gmail_id,)
    ).fetchone() is not None


def insert_message(conn, row: dict) -> None:
    cols = ", ".join(row.keys())
    ph = ", ".join("?" for _ in row)
    conn.execute(
        f"INSERT OR IGNORE INTO messages ({cols}) VALUES ({ph})", tuple(row.values())
    )


def replace_cards(conn, gmail_id: str, cards: list[dict]) -> None:
    """Re-extraction replaces this issue's cards (idempotent per issue)."""
    conn.execute("DELETE FROM story_cards WHERE gmail_id=?", (gmail_id,))
    for c in cards:
        cols = ", ".join(c.keys())
        ph = ", ".join("?" for _ in c)
        conn.execute(f"INSERT INTO story_cards ({cols}) VALUES ({ph})", tuple(c.values()))


def log_sync(conn, **kw) -> None:
    conn.execute(
        "INSERT INTO sync_log(run_at,segment,window,scanned,new_added,duplicates,status,notes)"
        " VALUES(:run_at,:segment,:window,:scanned,:new_added,:duplicates,:status,:notes)", kw,
    )


def counts(conn) -> dict:
    q = lambda s: conn.execute(s).fetchone()[0]
    return {
        "messages": q("SELECT COUNT(*) FROM messages"),
        "sources": q("SELECT COUNT(*) FROM sources"),
        "cards": q("SELECT COUNT(*) FROM story_cards"),
    }
