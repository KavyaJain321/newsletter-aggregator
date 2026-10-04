-- Step 1 (ingest). Columns filled by later steps (kind, preheader, html/md paths, paywall)
-- are created now with neutral defaults so the emails table matches instruction.md section 3.

CREATE TABLE ingest_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    edition       TEXT NOT NULL,
    window_start  TEXT NOT NULL,                 -- UTC ISO-8601
    window_end    TEXT NOT NULL,                 -- UTC ISO-8601; the next run starts here (minus overlap)
    query         TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('running', 'ok', 'partial', 'failed')),
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    stats         TEXT                           -- JSON report
);
CREATE INDEX ingest_runs_edition_status ON ingest_runs (edition, status, window_end);

CREATE TABLE emails (
    msg_id          TEXT PRIMARY KEY,            -- Gmail message id
    thread_id       TEXT,
    source_id       TEXT NOT NULL,
    series          TEXT,                        -- matcher series (e.g. pragmatic deepdive/pulse/podcast)
    rfc_message_id  TEXT,                        -- RFC 822 Message-ID header
    from_header     TEXT NOT NULL,
    to_header       TEXT,
    subject         TEXT NOT NULL DEFAULT '',
    date_header     TEXT,
    received_at     TEXT NOT NULL,               -- UTC ISO-8601 from Gmail internalDate
    label_ids       TEXT NOT NULL DEFAULT '[]',  -- JSON
    in_spam         INTEGER NOT NULL DEFAULT 0,
    in_trash        INTEGER NOT NULL DEFAULT 0,
    size_bytes      INTEGER NOT NULL,
    sha256          TEXT NOT NULL,               -- of the .eml bytes
    eml_path        TEXT NOT NULL,               -- relative to the archive dir
    kind            TEXT NOT NULL DEFAULT 'unknown',
    preheader       TEXT,
    html_path       TEXT,
    md_path         TEXT,
    is_preview      INTEGER NOT NULL DEFAULT 0,
    paywall_cut_at  INTEGER,
    ingest_run_id   INTEGER REFERENCES ingest_runs (id),
    ingested_at     TEXT NOT NULL
);
CREATE INDEX emails_source_received ON emails (source_id, received_at);
CREATE INDEX emails_rfc_message_id ON emails (rfc_message_id);

-- The same issue delivered more than once (e.g. TLDR to three +aliases, each with its own
-- Message-ID). Kept for audit; only the canonical copy is archived and processed.
CREATE TABLE email_duplicates (
    msg_id            TEXT PRIMARY KEY,
    canonical_msg_id  TEXT NOT NULL REFERENCES emails (msg_id),
    reason            TEXT NOT NULL,             -- message-id | alias-copy
    to_header         TEXT,
    received_at       TEXT NOT NULL,
    ingest_run_id     INTEGER REFERENCES ingest_runs (id),
    ingested_at       TEXT NOT NULL
);

-- Mail from a registered address that no matcher accepted (e.g. a new list on a shared
-- address). Visible for config review; re-evaluated whenever it shows up in a window again.
CREATE TABLE ingest_skips (
    msg_id            TEXT PRIMARY KEY,
    reason            TEXT NOT NULL,
    from_header       TEXT,
    subject           TEXT,
    received_at       TEXT,
    last_seen_run_id  INTEGER REFERENCES ingest_runs (id)
);
