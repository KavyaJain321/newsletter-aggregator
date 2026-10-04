# pipeline/ — newsletter generation pipeline

Built step by step from [`instruction.md`](../instruction.md). **Status: Step 0 (setup, config, isolated on-demand GPU host + health monitoring) and Step 1 (ingest) done.**

## Setup
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r pipeline/requirements.txt     # Windows (use .venv/bin/python elsewhere)
cp pipeline/env.example .env                                          # then edit; .env is git-ignored
#   DATABASE_URL = Supabase session-pooler string (ask the owner for access; never commit it)
.venv/Scripts/python -m pipeline.cli db migrate      # create/upgrade the shared schema (safe to repeat)
.venv/Scripts/python -m pipeline.cli doctor          # config, Gmail, LLMs, DB, paths
.venv/Scripts/python -m pipeline.cli doctor --deep   # + one live JSON completion
.venv/Scripts/python -m pytest tests -q
```
`doctor` exits 0 only when every required check passes: config valid, Gmail token refreshes with
**exactly** `gmail.readonly` on the expected account, at least one LLM provider usable, the shared
database reachable and writable, output dirs writable.

## What exists (Steps 0-1)
| Path | What |
|---|---|
| `config/sources.yaml` | Every Tech/Finance source: full sender address (+ display-name regex where an address is shared), brand, editions, cadence, paywall mode, disclosures. Addresses verified against the inbox |
| `config/editions.yaml` | Tech + Finance: schedule, run window, roster order (= coverage-strip order), slots, ranking weights |
| `config/registry.py` | Loads + strictly validates both YAMLs; `match_sender()` resolves a From header to a source |
| `config/settings.py` | Machine settings from env / `.env` (keys masked in repr) |
| `llm/client.py` | One interface: Ollama (native `/api/chat`, `think` + JSON-schema `format`) → Groq (OpenAI-compatible, real User-Agent). Retries, fallback, empty-output guard, JSONL call logs. No silent mock |
| `llm/json_repair.py` | Recovers JSON from model output (reasoning blocks, fences, prose, trailing commas, truncation) — never invents content |
| `ingest/gmail.py` | Read-only Gmail: auth, list (all pages, spam/trash included), raw fetch. Refuses any scope beyond `gmail.readonly`; retries 429/5xx and rate-limit 403s |
| `ingest/ingest.py` | Step 1: watermark window, sender matching, alias-copy dedupe, per-source report; email row + raw copy in one transaction |
| `store/db.py` | Shared Supabase Postgres (SQLite only as the offline test double): one portable SQL dialect, migrations, team-wide run lock, secrets scrubbed from errors |
| `store/migrations/` | `postgres/NNN_*.sql` = the real schema; `sqlite/NNN_*.sql` = its test double (parity is tested) |
| `store/raw.py` | Original emails gzip-compressed into `email_raw`, sha256-verified on read |
| `llm/remote_ollama.py` | On-demand Ollama on the shared GPU host over SSH: guarded start, tagged process, stops only its own |
| `llm/host_monitor.py` | Shared-host health: GPU heat/util/power/fan/VRAM/throttling, CPU load, RAM, swap, disk. Start gate, background watch, per-request gate |
| `llm/session.py` | `llm_session()`: the one way a run gets an LLM client - start, monitor, tunnel, always stop |
| `cli.py` | `doctor [--deep]`, `ollama status|up|down`, `host status|watch`, `ingest`, `db status|migrate`, `export-eml` |

Other packages are empty placeholders named for the step that fills them.

## Shared database (Supabase)
Everything the pipeline stores lives in one Supabase Postgres project (Mumbai), so every teammate
works on the same data. Nothing is stored on a laptop. `DATABASE_URL` may be pasted exactly as the
dashboard shows it, raw password included; special characters are encoded automatically.
- **Connect:** put the dashboard's *Connect -> Session pooler* string in `.env` as `DATABASE_URL`.
  It works over IPv4 and keeps the run lock. Only this database connection is used; the Supabase
  API keys are not needed.
- **Locked down:** Row Level Security is on for every table with no policies, so the public
  Supabase API (anon/publishable keys) can read nothing. Access needs the database password.
- **Gmail is still local-only:** only the machine with the Gmail token runs `ingest`. Everyone
  else reads the results from Supabase.
- **One run at a time:** a Postgres advisory lock stops two people ingesting at once.

**The content store: four layers, each rebuildable from the one below**
([`store/migrations/postgres/001_content_store.sql`](store/migrations/postgres/001_content_store.sql)):

| Layer | Tables | Filled by |
|---|---|---|
| 1 Raw | `sources` (newsletters from `sources.yaml` + future RSS/API feeds), `documents` (one issue / article, any channel), `document_raw` (byte-exact original, gzip), `duplicates`, `ingest_skips`, `ingest_runs` | Step 1 (done) |
| 2 Structure | `blocks` (section > heading > subheading > paragraph / list / quote / image / table, in order, sponsor-flagged), `links` (clean URL + `url_key` to match the same article across sources), `media` (image URL/alt/caption, never the file) | Step 3 |
| 3 Meaning | `items` (one news story: headline, sub-headline, summary, why it matters, body, type, section), `item_facts` (every number/claim + the exact sentence it came from), `item_quotes`, `entities` + `item_entities`, `item_embeddings` (pgvector halfvec 768) | Step 5 |
| 4 Topics | `topics` (tree: `tech.ai.models`), `item_topics`, `stories` (one real-world event across all sources, with coverage counts), `story_items` | Step 6 |

- **Channel-agnostic:** an RSS article or HN post is just another `documents` row
  (`channel = rss|web|api`), so Pranav's outside data drops into the same layers.
- **`story_cards` view:** serves `items` in Pranav's story-card shape (`card_id, gmail_id, headline,
  what, why, facts_json, links_json`), so his code can read our data unchanged.
- **Rebuildable:** every derived row records its extractor/model/version, and deleting a document
  removes everything derived from it.
- **Size:** about 0.5 MB/day for layer 1 (measured: 5.2 MB for Sep 24 - Oct 4). Layers 2-4 add
  roughly 1-2 MB/day, so the free 500 MB lasts about 6-9 months. After that, prune `blocks`
  (rebuildable) or move to Pro.

```bash
.venv/Scripts/python -m pipeline.cli db status                    # schema version + row counts
.venv/Scripts/python -m pipeline.cli export-eml 1a0fc3227c848e33  # original email -> .eml file (sha256-checked)
TEST_DATABASE_URL=... .venv/Scripts/python -m pytest tests/integration -q   # real-Postgres tests (throwaway schema)
```

## Ingest (Step 1)
```bash
.venv/Scripts/python -m pipeline.cli ingest --edition all                     # since the last OK run
.venv/Scripts/python -m pipeline.cli ingest --edition finance --since 2026-09-24   # backfill (only widens)
```
- Query: `from:(<every edition sender>) after:<window start>`, spam + trash included (flagged).
- Exactly once: stored ids are never fetched again. TLDR's per-alias copies (distinct
  Message-IDs, up to ~20 min apart) collapse to one row, and the extras are recorded in `email_duplicates`.
- Mail from a registered address that no matcher accepts (e.g. Bloomberg "You've subscribed!")
  goes to `ingest_skips` and is listed in the report.
- Any per-message error makes the run `partial`. The next run then re-covers that whole window,
  even a `--since` backfill, so nothing is skipped.
- Exit code 0 only if every edition finished `ok`.

## On-demand GPU host (trijya-3)
The team's `qwen3:14b` runs on the shared **trijya-3** workstation (RTX 3080 Ti, via Tailscale).
Its Ollama autostart was disabled on request, so with `OLLAMA_REMOTE_SSH` set the pipeline
**starts its own private Ollama only for a run and stops it afterwards**:
- **isolated:** listens on private port `11436` (not the shared `11434` that the team proxy
  forwards), reached only through an SSH tunnel this process holds. Other services keep
  seeing Ollama "off" and can't queue work on our instance. If anything else holds `11436`, we refuse
- **health-gated start:** GPU < 80 C, no thermal throttling, >= `OLLAMA_MIN_FREE_VRAM_MB` free,
  CPU load/core, RAM, swap and disk all within limits; never in the 04:00-06:45 IST power-off
  window (Mon-Sat), and its lifetime is capped to end before it
- **watched while running** (`llm/host_monitor.py`, logged to `data/host_monitor/`): every 30 s and
  before every request. >= 82 C pauses our requests until 78 C; >= 87 C, hardware throttling,
  RAM/swap exhaustion or a lost connection stops our Ollama immediately
- runs under `timeout`, so it dies on schedule even if this machine crashes
- tagged `nlp-ollama-serve`; we only ever stop a process still carrying our tag
- 1 loaded model, 1 parallel request, model unloaded before stopping

```bash
.venv/Scripts/python -m pipeline.cli ollama status   # read-only
.venv/Scripts/python -m pipeline.cli ollama up       # manual start (normally per run)
.venv/Scripts/python -m pipeline.cli ollama down     # stops only our tagged process
.venv/Scripts/python -m pipeline.cli host status     # heat / load / memory, read-only
.venv/Scripts/python -m pipeline.cli host watch --interval 30 --count 10
```
Measured 2026-10-04: start 4 s; `qwen3:14b` 9.6 GB, 100% on GPU; isolated JSON round-trip 5.0 s incl.
load (61 s when the instance was on the shared port and other services queued on it).
SSH uses classic curve25519 key exchange: the post-quantum default hung on a Tailscale direct path.

## Key rules baked in
- Runtime LLMs are local Ollama or Groq only — never Anthropic models.
- Coverage counts **brands** (all Semafor editions = 1; TLDR and TLDR Dev = 2).
- A sender must match a full address; shared addresses also need a display-name regex.
- `.env` (database password), `data/llm_logs/` and `out/` are git-ignored. Newsletter text lives only in the private Supabase database.
