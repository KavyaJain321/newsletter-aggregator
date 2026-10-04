-- The shared content store (Supabase Postgres). Source of truth for the schema;
-- migrations/sqlite/001_ingest.sql mirrors its tables for offline unit tests (parity is tested).
--
-- Four layers, each rebuildable from the one below it:
--   1 RAW        sources, documents, document_raw          (what arrived, byte-exact)
--   2 STRUCTURE  blocks, links, media                      (the document as laid out)   <- Step 3
--   3 MEANING    items, item_facts, item_quotes,           (each news story in it)      <- Step 5
--                entities, item_entities, item_embeddings
--   4 TOPICS     topics, item_topics, stories, story_items (across all sources)         <- Step 6
-- Channel-agnostic: a newsletter email, an RSS article, an HN post or a web page are all
-- `documents`, so outside data (Phase 3 / Pranav's feeds) lands in the same tables.
--
-- Security: Row Level Security is ON for every table with NO policies, so Supabase's public
-- REST API (anon / publishable keys) sees nothing. Only direct Postgres connections with the
-- database password (the pipeline, team members) can read or write.

CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- ============================================================ 1. RAW
CREATE TABLE sources (
    id          TEXT PRIMARY KEY,                -- sources.yaml id (newsletters) or e.g. 'rss_hn_front'
    kind        TEXT NOT NULL CHECK (kind IN ('newsletter', 'rss', 'api', 'web')),
    name        TEXT NOT NULL,
    brand       TEXT,                            -- coverage is counted per brand
    editions    JSONB NOT NULL DEFAULT '[]',     -- ["tech", "finance"]
    homepage    TEXT,
    config      JSONB NOT NULL DEFAULT '{}',     -- matchers, cadence, paywall mode, feed url ...
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE ingest_runs (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    channel       TEXT NOT NULL,                 -- email | rss | web | api
    scope         TEXT NOT NULL,                 -- edition (email) or feed id
    window_start  TIMESTAMPTZ NOT NULL,
    window_end    TIMESTAMPTZ NOT NULL,          -- the next run starts here (minus overlap)
    query         TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('running', 'ok', 'partial', 'failed')),
    started_at    TIMESTAMPTZ NOT NULL,
    finished_at   TIMESTAMPTZ,
    stats         JSONB                          -- per-run report
);
CREATE INDEX ingest_runs_scope_status ON ingest_runs (channel, scope, status, window_end);

CREATE TABLE documents (
    id               TEXT PRIMARY KEY,           -- email: Gmail message id; others: <channel>_<hash>
    channel          TEXT NOT NULL CHECK (channel IN ('email', 'rss', 'web', 'api')),
    external_id      TEXT NOT NULL,              -- Gmail id / feed guid / canonical URL
    source_id        TEXT NOT NULL REFERENCES sources (id),
    series           TEXT,                       -- sub-series (Pragmatic deepdive/pulse/podcast)
    kind             TEXT NOT NULL DEFAULT 'unknown',   -- issue | welcome | promo | ... (Step 2)
    title            TEXT NOT NULL DEFAULT '',   -- email subject / article title
    preheader        TEXT,
    author           TEXT,                       -- sender display name / byline
    url              TEXT,                       -- web version / article URL, if any
    url_key          TEXT,                       -- sha1 of the canonical URL (cross-source match)
    language         TEXT,
    published_at     TIMESTAMPTZ,                -- Date header / feed pubDate
    received_at      TIMESTAMPTZ NOT NULL,       -- when it reached us (Gmail internalDate)
    received_day_et  DATE NOT NULL,              -- received_at's calendar day in America/New_York
    -- email transport (NULL for other channels)
    rfc_message_id   TEXT,
    thread_id        TEXT,
    from_header      TEXT,
    to_header        TEXT,
    label_ids        JSONB NOT NULL DEFAULT '[]',
    in_spam          BOOLEAN NOT NULL DEFAULT FALSE,
    in_trash         BOOLEAN NOT NULL DEFAULT FALSE,
    meta             JSONB NOT NULL DEFAULT '{}',-- channel-specific extras
    -- the original and the cleaned text
    size_bytes       INTEGER NOT NULL,
    sha256           TEXT NOT NULL,              -- of the original bytes
    content_hash     TEXT,                       -- of the cleaned text (cross-channel duplicates)
    word_count       INTEGER,
    reading_minutes  REAL,
    is_preview       BOOLEAN NOT NULL DEFAULT FALSE,
    paywall_cut_at   INTEGER,                    -- block seq where a paywall cuts the text
    -- processing state: each step stamps when it ran and with which version
    classified_at    TIMESTAMPTZ,
    structured_at    TIMESTAMPTZ,
    structure_version TEXT,
    extracted_at     TIMESTAMPTZ,
    extract_version  TEXT,
    ingest_run_id    BIGINT REFERENCES ingest_runs (id),
    ingested_at      TIMESTAMPTZ NOT NULL,
    UNIQUE (channel, external_id)
);
CREATE INDEX documents_source_received ON documents (source_id, received_at);
CREATE INDEX documents_day ON documents (received_day_et);
CREATE INDEX documents_kind ON documents (kind);
CREATE INDEX documents_rfc_message_id ON documents (rfc_message_id);
CREATE INDEX documents_url_key ON documents (url_key);

-- The byte-exact original (gzip): the source of truth every other layer is rebuilt from.
-- Written in the same transaction as its documents row.
CREATE TABLE document_raw (
    document_id   TEXT PRIMARY KEY REFERENCES documents (id) ON DELETE CASCADE,
    content_type  TEXT NOT NULL,                 -- message/rfc822 | text/html | application/json
    encoding      TEXT NOT NULL DEFAULT 'gzip' CHECK (encoding IN ('gzip')),
    data          BYTEA NOT NULL
);

-- The same document delivered more than once (TLDR to three +aliases, each with its own
-- Message-ID). Kept for audit; only the canonical copy is stored and processed.
CREATE TABLE duplicates (
    channel                TEXT NOT NULL,
    external_id            TEXT NOT NULL,
    canonical_document_id  TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    reason                 TEXT NOT NULL CHECK (reason IN ('message-id', 'alias-copy', 'same-url', 'same-content')),
    recipient              TEXT,
    received_at            TIMESTAMPTZ NOT NULL,
    ingest_run_id          BIGINT REFERENCES ingest_runs (id),
    ingested_at            TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (channel, external_id)
);

-- Arrived from a known sender/feed but is not content we track (e.g. Bloomberg
-- "You've subscribed!"). Visible for config review; re-evaluated when seen again.
CREATE TABLE ingest_skips (
    channel           TEXT NOT NULL,
    external_id       TEXT NOT NULL,
    reason            TEXT NOT NULL,
    from_header       TEXT,
    title             TEXT,
    received_at       TIMESTAMPTZ,
    last_seen_run_id  BIGINT REFERENCES ingest_runs (id),
    PRIMARY KEY (channel, external_id)
);

-- ============================================================ 2. STRUCTURE (Step 3)
-- The document exactly as laid out, in reading order. A section block parents its
-- headings and paragraphs, so "everything under 'Big Tech & Startups'" is one query.
CREATE TABLE blocks (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id   TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,              -- reading order within the document
    parent_id     BIGINT REFERENCES blocks (id) ON DELETE CASCADE,
    depth         SMALLINT NOT NULL DEFAULT 0,
    type          TEXT NOT NULL CHECK (type IN ('section', 'heading', 'subheading', 'paragraph', 'list_item',
                                                'quote', 'image', 'table', 'divider', 'cta', 'footer')),
    level         SMALLINT,                      -- heading level 1-6
    content       TEXT NOT NULL DEFAULT '',      -- markdown, links inline as [anchor](url)
    is_sponsored  BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (document_id, seq)
);

CREATE TABLE links (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id    TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    block_id       BIGINT REFERENCES blocks (id) ON DELETE CASCADE,
    item_id        BIGINT,                       -- set by Step 5 (FK added below)
    seq            INTEGER NOT NULL,
    anchor         TEXT,
    raw_url        TEXT NOT NULL,                -- as in the email (never fetched if tracking/subscription)
    canonical_url  TEXT,                         -- unwrapped, utm_* stripped
    url_key        TEXT,                         -- sha1(canonical_url): same article across sources
    domain         TEXT,
    kind           TEXT NOT NULL DEFAULT 'article' CHECK (kind IN ('article', 'source', 'sponsor', 'social',
                                                 'subscription', 'internal', 'image', 'other')),
    is_tracking    BOOLEAN NOT NULL DEFAULT FALSE,
    is_paywalled   BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (document_id, seq)
);
CREATE INDEX links_url_key ON links (url_key);
CREATE INDEX links_domain ON links (domain);

-- Images are kept as references (URL, alt, caption), never as files.
CREATE TABLE media (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id  TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    block_id     BIGINT REFERENCES blocks (id) ON DELETE CASCADE,
    seq          INTEGER NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'image' CHECK (kind IN ('image', 'chart', 'logo', 'gif', 'video', 'other')),
    url          TEXT NOT NULL,
    alt          TEXT,
    caption      TEXT,
    width        INTEGER,
    height       INTEGER,
    UNIQUE (document_id, seq)
);

-- ============================================================ 3. MEANING (Step 5)
-- One news story / article / tool / deal as ONE source told it.
CREATE TABLE items (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id      TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    source_id        TEXT NOT NULL REFERENCES sources (id),
    seq              INTEGER NOT NULL,           -- order within the document
    section          TEXT,                       -- the section it appeared under
    first_block_seq  INTEGER,                    -- its span of blocks
    last_block_seq   INTEGER,
    item_type        TEXT NOT NULL DEFAULT 'news' CHECK (item_type IN ('news', 'analysis', 'opinion', 'explainer',
                     'tool', 'launch', 'deal', 'research', 'data', 'event', 'job', 'quote', 'other')),
    headline         TEXT NOT NULL,
    subheadline      TEXT,
    summary          TEXT,                       -- what happened (paraphrased)
    why_it_matters   TEXT,
    author_take      TEXT,                       -- the newsletter's own opinion, kept separate
    body             TEXT,                       -- the item's text as published (markdown)
    primary_url      TEXT,                       -- the story's main outbound link
    url_key          TEXT,                       -- sha1(canonical primary_url)
    is_vendor_claim  BOOLEAN NOT NULL DEFAULT FALSE,
    flags            JSONB NOT NULL DEFAULT '{}',
    extractor        TEXT NOT NULL,              -- rule:<name> | llm:<model>
    prompt_version   TEXT,
    created_at       TIMESTAMPTZ NOT NULL,
    UNIQUE (document_id, seq)
);
CREATE INDEX items_source ON items (source_id);
CREATE INDEX items_url_key ON items (url_key);
CREATE INDEX items_fts ON items USING gin (to_tsvector('english', headline || ' ' || coalesce(summary, '')));
ALTER TABLE links ADD CONSTRAINT links_item_fk FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE SET NULL;

-- Every number and claim, with the exact sentence it came from (evidence must be a
-- substring of the document: nothing in our issues can be invented).
CREATE TABLE item_facts (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_id            BIGINT NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    seq                INTEGER NOT NULL,
    kind               TEXT NOT NULL CHECK (kind IN ('number', 'money', 'percent', 'date', 'claim',
                                                     'prediction', 'statistic')),
    subject            TEXT,                     -- what the number is about
    claim              TEXT NOT NULL,            -- the fact as one plain sentence
    value              NUMERIC,
    unit               TEXT,                     -- USD, %, bps, users, x ...
    as_of              TEXT,                     -- date or period the value refers to
    evidence           TEXT NOT NULL,
    evidence_block_id  BIGINT REFERENCES blocks (id) ON DELETE SET NULL,
    verified           BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (item_id, seq)
);

CREATE TABLE item_quotes (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_id            BIGINT NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    seq                INTEGER NOT NULL,
    text               TEXT NOT NULL,
    speaker            TEXT,
    speaker_role       TEXT,
    evidence_block_id  BIGINT REFERENCES blocks (id) ON DELETE SET NULL,
    verified           BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (item_id, seq)
);

-- Each company / person / ticker / product exists once, however many sources mention it.
CREATE TABLE entities (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind           TEXT NOT NULL CHECK (kind IN ('company', 'person', 'ticker', 'product', 'organization',
                                                 'place', 'technology', 'event', 'law')),
    name           TEXT NOT NULL,
    canonical_key  TEXT NOT NULL UNIQUE,         -- '<kind>:<normalised name>'
    ticker         TEXT,
    aliases        JSONB NOT NULL DEFAULT '[]',
    meta           JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE item_entities (
    item_id    BIGINT NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    entity_id  BIGINT NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    role       TEXT NOT NULL DEFAULT 'mentioned', -- subject | mentioned | quoted | acquirer | target ...
    mentions   INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (item_id, entity_id, role)
);
CREATE INDEX item_entities_entity ON item_entities (entity_id);

-- One meaning-vector per item (half precision), kept apart so items stay small and the
-- embedding model can be swapped by re-filling this table.
CREATE TABLE item_embeddings (
    item_id     BIGINT PRIMARY KEY REFERENCES items (id) ON DELETE CASCADE,
    model       TEXT NOT NULL,
    embedding   extensions.halfvec(768) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL
);

-- ============================================================ 4. TOPICS (Step 6)
CREATE TABLE topics (
    id           TEXT PRIMARY KEY,               -- 'tech.ai.models', 'finance.markets.rates'
    parent_id    TEXT REFERENCES topics (id),
    label        TEXT NOT NULL,
    description  TEXT
);

CREATE TABLE item_topics (
    item_id      BIGINT NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    topic_id     TEXT NOT NULL REFERENCES topics (id) ON DELETE CASCADE,
    confidence   REAL NOT NULL,
    assigned_by  TEXT NOT NULL,                  -- rule:<name> | llm:<model> | human
    PRIMARY KEY (item_id, topic_id)
);
CREATE INDEX item_topics_topic ON item_topics (topic_id);

-- One real-world event across every source ("OpenAI raises $40B": TLDR + Neuron + Axios).
CREATE TABLE stories (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title           TEXT NOT NULL,
    summary         TEXT,
    primary_topic   TEXT REFERENCES topics (id),
    first_seen_at   TIMESTAMPTZ NOT NULL,
    last_seen_at    TIMESTAMPTZ NOT NULL,
    item_count      INTEGER NOT NULL DEFAULT 0,
    source_count    INTEGER NOT NULL DEFAULT 0,
    brand_count     INTEGER NOT NULL DEFAULT 0,  -- coverage ("covered by N of M")
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed', 'merged')),
    merged_into     BIGINT REFERENCES stories (id),
    created_at      TIMESTAMPTZ NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL
);
CREATE INDEX stories_last_seen ON stories (last_seen_at);

CREATE TABLE story_items (
    story_id    BIGINT NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
    item_id     BIGINT NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    similarity  REAL,
    added_by    TEXT NOT NULL,                   -- url | embedding | llm | human
    PRIMARY KEY (story_id, item_id)
);
CREATE INDEX story_items_item ON story_items (item_id);

-- ============================================================ compatibility
-- Pranav's pipeline (origin/feat/pipeline-mvp) reads "story cards":
-- {card_id, gmail_id, source_id, seq, headline, what, why, facts_json, links_json}.
-- This view serves our items in exactly that shape. security_invoker keeps RLS in force.
CREATE VIEW story_cards WITH (security_invoker = true) AS
SELECT i.id::text AS card_id,
       d.external_id AS gmail_id,
       i.source_id,
       i.seq,
       i.headline,
       i.summary AS what,
       i.why_it_matters AS why,
       COALESCE((SELECT jsonb_agg(f.claim ORDER BY f.seq) FROM item_facts f WHERE f.item_id = i.id), '[]') AS facts_json,
       COALESCE((SELECT jsonb_agg(jsonb_build_object('anchor', l.anchor, 'url', COALESCE(l.canonical_url, l.raw_url))
                                  ORDER BY l.seq)
                 FROM links l WHERE l.item_id = i.id AND NOT l.is_tracking), '[]') AS links_json,
       i.extractor,
       i.prompt_version,
       i.created_at
FROM items i JOIN documents d ON d.id = i.document_id;

-- ============================================================ security
ALTER TABLE schema_migrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingest_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_raw ENABLE ROW LEVEL SECURITY;
ALTER TABLE duplicates ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingest_skips ENABLE ROW LEVEL SECURITY;
ALTER TABLE blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE links ENABLE ROW LEVEL SECURITY;
ALTER TABLE media ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE stories ENABLE ROW LEVEL SECURITY;
ALTER TABLE story_items ENABLE ROW LEVEL SECURITY;
