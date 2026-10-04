-- OFFLINE TEST DOUBLE of migrations/postgres/001_content_store.sql (the real schema).
-- Same tables and columns (enforced by tests/unit/test_db.py); SQLite types; no views/extensions.

CREATE TABLE sources (
    id          TEXT PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('newsletter', 'rss', 'api', 'web')),
    name        TEXT NOT NULL,
    brand       TEXT,
    editions    TEXT NOT NULL DEFAULT '[]',
    homepage    TEXT,
    config      TEXT NOT NULL DEFAULT '{}',
    active      INTEGER NOT NULL DEFAULT 1,
    updated_at  TEXT NOT NULL
);

CREATE TABLE ingest_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    channel       TEXT NOT NULL,
    scope         TEXT NOT NULL,
    window_start  TEXT NOT NULL,
    window_end    TEXT NOT NULL,
    query         TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('running', 'ok', 'partial', 'failed')),
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    stats         TEXT
);

CREATE TABLE documents (
    id               TEXT PRIMARY KEY,
    channel          TEXT NOT NULL CHECK (channel IN ('email', 'rss', 'web', 'api')),
    external_id      TEXT NOT NULL,
    source_id        TEXT NOT NULL REFERENCES sources (id),
    series           TEXT,
    kind             TEXT NOT NULL DEFAULT 'unknown',
    title            TEXT NOT NULL DEFAULT '',
    preheader        TEXT,
    author           TEXT,
    url              TEXT,
    url_key          TEXT,
    language         TEXT,
    published_at     TEXT,
    received_at      TEXT NOT NULL,
    received_day_et  TEXT NOT NULL,
    rfc_message_id   TEXT,
    thread_id        TEXT,
    from_header      TEXT,
    to_header        TEXT,
    label_ids        TEXT NOT NULL DEFAULT '[]',
    in_spam          INTEGER NOT NULL DEFAULT 0,
    in_trash         INTEGER NOT NULL DEFAULT 0,
    meta             TEXT NOT NULL DEFAULT '{}',
    size_bytes       INTEGER NOT NULL,
    sha256           TEXT NOT NULL,
    content_hash     TEXT,
    word_count       INTEGER,
    reading_minutes  REAL,
    is_preview       INTEGER NOT NULL DEFAULT 0,
    paywall_cut_at   INTEGER,
    classified_at    TEXT,
    structured_at    TEXT,
    structure_version TEXT,
    extracted_at     TEXT,
    extract_version  TEXT,
    ingest_run_id    INTEGER REFERENCES ingest_runs (id),
    ingested_at      TEXT NOT NULL,
    UNIQUE (channel, external_id)
);
CREATE INDEX documents_source_received ON documents (source_id, received_at);
CREATE INDEX documents_rfc_message_id ON documents (rfc_message_id);

CREATE TABLE document_raw (
    document_id   TEXT PRIMARY KEY REFERENCES documents (id) ON DELETE CASCADE,
    content_type  TEXT NOT NULL,
    encoding      TEXT NOT NULL DEFAULT 'gzip' CHECK (encoding IN ('gzip')),
    data          BLOB NOT NULL
);

CREATE TABLE duplicates (
    channel                TEXT NOT NULL,
    external_id            TEXT NOT NULL,
    canonical_document_id  TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    reason                 TEXT NOT NULL CHECK (reason IN ('message-id', 'alias-copy', 'same-url', 'same-content')),
    recipient              TEXT,
    received_at            TEXT NOT NULL,
    ingest_run_id          INTEGER REFERENCES ingest_runs (id),
    ingested_at            TEXT NOT NULL,
    PRIMARY KEY (channel, external_id)
);

CREATE TABLE ingest_skips (
    channel           TEXT NOT NULL,
    external_id       TEXT NOT NULL,
    reason            TEXT NOT NULL,
    from_header       TEXT,
    title             TEXT,
    received_at       TEXT,
    last_seen_run_id  INTEGER REFERENCES ingest_runs (id),
    PRIMARY KEY (channel, external_id)
);

CREATE TABLE blocks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id   TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,
    parent_id     INTEGER REFERENCES blocks (id) ON DELETE CASCADE,
    depth         INTEGER NOT NULL DEFAULT 0,
    type          TEXT NOT NULL,
    level         INTEGER,
    content       TEXT NOT NULL DEFAULT '',
    is_sponsored  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (document_id, seq)
);

CREATE TABLE links (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id    TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    block_id       INTEGER REFERENCES blocks (id) ON DELETE CASCADE,
    item_id        INTEGER REFERENCES items (id) ON DELETE SET NULL,
    seq            INTEGER NOT NULL,
    anchor         TEXT,
    raw_url        TEXT NOT NULL,
    canonical_url  TEXT,
    url_key        TEXT,
    domain         TEXT,
    kind           TEXT NOT NULL DEFAULT 'article',
    is_tracking    INTEGER NOT NULL DEFAULT 0,
    is_paywalled   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (document_id, seq)
);

CREATE TABLE media (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    block_id     INTEGER REFERENCES blocks (id) ON DELETE CASCADE,
    seq          INTEGER NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'image',
    url          TEXT NOT NULL,
    alt          TEXT,
    caption      TEXT,
    width        INTEGER,
    height       INTEGER,
    UNIQUE (document_id, seq)
);

CREATE TABLE items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id      TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    source_id        TEXT NOT NULL REFERENCES sources (id),
    seq              INTEGER NOT NULL,
    section          TEXT,
    first_block_seq  INTEGER,
    last_block_seq   INTEGER,
    item_type        TEXT NOT NULL DEFAULT 'news',
    headline         TEXT NOT NULL,
    subheadline      TEXT,
    summary          TEXT,
    why_it_matters   TEXT,
    author_take      TEXT,
    body             TEXT,
    primary_url      TEXT,
    url_key          TEXT,
    is_vendor_claim  INTEGER NOT NULL DEFAULT 0,
    flags            TEXT NOT NULL DEFAULT '{}',
    extractor        TEXT NOT NULL,
    prompt_version   TEXT,
    created_at       TEXT NOT NULL,
    UNIQUE (document_id, seq)
);

CREATE TABLE item_facts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id            INTEGER NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    seq                INTEGER NOT NULL,
    kind               TEXT NOT NULL,
    subject            TEXT,
    claim              TEXT NOT NULL,
    value              NUMERIC,
    unit               TEXT,
    as_of              TEXT,
    evidence           TEXT NOT NULL,
    evidence_block_id  INTEGER REFERENCES blocks (id) ON DELETE SET NULL,
    verified           INTEGER NOT NULL DEFAULT 0,
    UNIQUE (item_id, seq)
);

CREATE TABLE item_quotes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id            INTEGER NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    seq                INTEGER NOT NULL,
    text               TEXT NOT NULL,
    speaker            TEXT,
    speaker_role       TEXT,
    evidence_block_id  INTEGER REFERENCES blocks (id) ON DELETE SET NULL,
    verified           INTEGER NOT NULL DEFAULT 0,
    UNIQUE (item_id, seq)
);

CREATE TABLE entities (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    kind           TEXT NOT NULL,
    name           TEXT NOT NULL,
    canonical_key  TEXT NOT NULL UNIQUE,
    ticker         TEXT,
    aliases        TEXT NOT NULL DEFAULT '[]',
    meta           TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE item_entities (
    item_id    INTEGER NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    entity_id  INTEGER NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    role       TEXT NOT NULL DEFAULT 'mentioned',
    mentions   INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (item_id, entity_id, role)
);

CREATE TABLE item_embeddings (
    item_id     INTEGER PRIMARY KEY REFERENCES items (id) ON DELETE CASCADE,
    model       TEXT NOT NULL,
    embedding   BLOB NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE topics (
    id           TEXT PRIMARY KEY,
    parent_id    TEXT REFERENCES topics (id),
    label        TEXT NOT NULL,
    description  TEXT
);

CREATE TABLE item_topics (
    item_id      INTEGER NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    topic_id     TEXT NOT NULL REFERENCES topics (id) ON DELETE CASCADE,
    confidence   REAL NOT NULL,
    assigned_by  TEXT NOT NULL,
    PRIMARY KEY (item_id, topic_id)
);

CREATE TABLE stories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    summary         TEXT,
    primary_topic   TEXT REFERENCES topics (id),
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    item_count      INTEGER NOT NULL DEFAULT 0,
    source_count    INTEGER NOT NULL DEFAULT 0,
    brand_count     INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'open',
    merged_into     INTEGER REFERENCES stories (id),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE story_items (
    story_id    INTEGER NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
    item_id     INTEGER NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    similarity  REAL,
    added_by    TEXT NOT NULL,
    PRIMARY KEY (story_id, item_id)
)
