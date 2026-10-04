# instruction.md — Newsletter Generation Pipeline

**What this builds:** a pipeline that reads the latest issues of the newsletters we subscribe to,
extracts and analyzes the stories across all of them, and generates **one aggregated issue per
edition** ("Twenty to One"). The editions are **Tech** and **Finance**, and the output looks like the
two approved samples.

**Who follows it:** a teammate or an AI coding session. Each step has a goal, inputs, outputs, the
method, what to borrow and an acceptance check. Do the steps in order. A step is done only when its
acceptance check passes.

**Version scope**
| Phase | Scope | Leaves the system? |
|---|---|---|
| **v1 (build now)** | Inbox newsletters → Tech + Finance issues → HTML + PDF for **human review** | No. Nothing is sent |
| **Phase 2** | Human approval gate → automated scheduling, sending, feedback loop | Only after approval |
| **Phase 3** | Add outside, live data (RSS, Hacker News, arXiv, GitHub Trending, web search) | Only after approval |

---

## 0. Hard rules (non-negotiable)

1. **No Claude/Anthropic models at runtime.** Every LLM call goes through one client. The primary is
   **local Qwen via Ollama** and the fallback is **Groq**.
2. **Gmail is read-only for ingestion** (`gmail.readonly`).
   - The OAuth token is machine-local and never committed.
   - Gmail work runs on the local machine, not in CI or the cloud.
3. **Never republish full text.**
   - Write short paraphrased summaries with attribution and links.
   - Use at most one direct quote per story, under 15 words.
   - Paywalled or preview issues are summarized only from what the email itself shows.
4. **Every fact is traceable** to `(newsletter, Gmail message id, evidence snippet)`.
   - Never invent numbers, names, URLs or dates.
   - Every number in the final copy maps to a stored fact.
5. **Sponsored or promotional content is never news.** Detect it, mark it and exclude it from
   extraction.
6. **Never click or resolve links that change subscription state** (confirm, unsubscribe, manage,
   preferences, "Yes, I'm real"). Never resolve links that carry a subscriber ID.
7. **A human approves every issue** before it can leave the system. v1 sends nothing.
8. **Borrowed code:**
   - Copy only from MIT or CC0 repos, and keep their license notice in the file header.
   - Repos with no license are a source of **ideas only**. See §6.
9. **Secrets and third-party text stay out of git:**
   - tokens, `.env`, LLM call logs and the raw archive are gitignored;
   - test fixtures containing newsletter text are kept local only.
10. **Finance copy contains no investment advice and no stock tips.** Politics is framed neutrally.

---

## 1. Pipeline at a glance

```
            ┌──────────── config: sources.yaml · editions.yaml · settings ────────────┐
Gmail ─► [1 Ingest] ─► [2 Classify email] ─► [3 Clean & normalize] ─► [4 Store & archive]
                                                                            │
          ┌─────────────────────────────────────────────────────────────────┘
          ▼
   [5 Extract: story cards + typed modules]   (rules first, LLM second, every fact verified)
          ▼
   [6 Analyze across sources]  cluster → coverage → conflicts → The Split → hype check → freshness
          ▼
   [7 Rank & select]  one weighted score → fill the edition's slots
          ▼
   [8 Compose]  LLM writes the issue as strict JSON (never free HTML)
          ▼
   [9 Validate]  facts · sources · links · sponsors · length · size  (fail → back to 8, max 2 retries)
          ▼
   [10 Render]  email-safe HTML + plain text + PDF
          ▼
   [11 Human review]  approve / edit / reject      ── Phase 2 ──►  [12 Schedule & send] ─► [13 Feedback]
```

All stages read from and write to **SQLite** plus an **on-disk archive**. Each stage is
**idempotent**: re-running it with the same input changes nothing. Each stage is **resumable**: a
failed run restarts from the stage that failed.

---

## 2. Repository layout (fresh package, separate from Pranav's `src/`)

```
pipeline/
  config/        sources.yaml  editions.yaml  settings.py  registry.py   # no secrets; env vars for keys
  ingest/        gmail.py                                         # read-only Gmail client
  classify/      email_kind.py
  clean/         html2md.py  links.py  sponsors.py  paywall.py  structure.py
  store/         schema.sql  db.py  archive.py
  extract/       rules/ (axios.py, importai.py, prorata.py, calendars.py, movers.py …)  cards.py  modules.py
  analyze/       cluster.py  coverage.py  conflicts.py  split.py  hype.py  freshness.py
  rank/          score.py  slots.py
  compose/       compose.py
  validate/      checks.py
  render/        templates/ (email.html.j2, web.html.j2, text.txt.j2)  render.py  pdf.py
  review/        review.py
  llm/           client.py  json_repair.py
  prompts/       classify.md  extract_card.md  same_story.md  compare.md  stance.md  judge.md  compose.md
  style/         exemplar_tech.json  exemplar_finance.json        # approved sample issues (style anchor)
  cli.py
tests/           unit/  golden/        # golden fixtures live outside git (see §8)
out/             <YYYY-MM-DD>/<edition>/  (gitignored)
data/            archive/ (gitignored)  pipeline.db (gitignored)
```

**Stack:** Python 3.11+, `requests`, `beautifulsoup4` + `lxml`, `jinja2`, `premailer`, `rapidfuzz`,
`pyyaml`, `pydantic` (schemas) and `pytest`. PDFs are printed with headless Chromium or Edge.
Phase 3 adds `feedparser`.

---

## 3. Data model (SQLite, `store/schema.sql`)

| Table | Key columns | Purpose |
|---|---|---|
| `sources` | `id`, `brand`, `editions`, `match` (full address + optional display-name regex + series), `cadence`, `expected_send_et`, `paywall_mode`, `html_only`, `disclosure`, `verified`, `active` | Map each sender to a newsletter, its brand and its editions. Source of truth: `pipeline/config/sources.yaml` (mirrored into SQLite) |
| `emails` | `msg_id` PK, `source_id`, `received_at`, `subject`, `preheader`, `kind`, `eml_path`, `html_path`, `md_path`, `is_preview`, `paywall_cut_at`, `run_id` | One row per received email |
| `sections` | `id`, `msg_id`, `seq`, `heading`, `text`, `is_sponsored` | The email split into structural sections |
| `links` | `id`, `msg_id`, `section_id`, `raw_url`, `canonical_url`, `is_tracking`, `is_paywalled`, `http_status` | Every outbound link |
| `cards` | `id`, `msg_id`, `section_id`, `headline`, `what_happened`, `author_take`, `section_tag`, `stance`, `is_opinion`, `is_vendor_claim`, `extractor` (`rule`/`llm`), `model` | One story as one newsletter told it |
| `facts` | `id`, `card_id`, `claim`, `value`, `unit`, `as_of`, `evidence`, `verified` | Atomic claims. `evidence` must be an exact substring of the email text |
| `entities` | `card_id`, `kind` (company/person/ticker/product/place), `value` | Used for clustering and per-entity views |
| `modules` | `id`, `msg_id`, `type`, `payload` (JSON), `evidence`, `verified` | Typed items: number, mover, calendar, deal, repo, tool, prompt, term, morsel, quote |
| `runs` | `id`, `edition`, `window_start`, `window_end`, `status`, `stage`, `stats` (JSON) | One pipeline run per edition per day |
| `clusters` | `id`, `run_id`, `title`, `coverage_n`, `roster_n`, `sources` (JSON), `conflicts` (JSON), `split` (JSON), `hype` (JSON), `stale`, `score`, `slot` | The same real-world story across newsletters |
| `cluster_members` | `cluster_id`, `card_id` | Every card in the cluster is kept, never discarded |
| `issues` | `id`, `run_id`, `edition`, `issue_no`, `status`, `json_path`, `html_path`, `pdf_path`, `subject`, `preheader`, `word_count`, `validation` (JSON), `reviewer`, `reviewed_at`, `notes` | One generated issue and its review state |

**Issue status lifecycle:** `draft → in_review → approved | rejected`.
Phase 2 extends it with `approved → scheduled → sent`.

---

## 4. Step-by-step build

### Step 0: Setup and config
- **Goal:** a runnable skeleton that knows its sources, editions and models.
- **Do:**
  - Create the layout in §2.
  - Write `sources.yaml` from `data/sources.csv` and the research files. Use **exact sender
    addresses** where a domain is shared, for example `markets@axios.com` (not `axios.com`) and
    `netinterest@substack.com` (never bare `substack.com`).
  - Write `editions.yaml`:
    - **Tech:** morning, about 09:30 ET. Its window is "since the last Tech run". On Fridays it
      also includes weeklies from the last 7 days.
    - **Finance:** "After the Bell", about 17:00 ET on weekdays. Its window is "since the last
      Finance run".
    - **Both:** each edition's roster order (this is the order of the coverage strip) and its slot
      template (see Step 7).
- **LLM client** (`llm/client.py`):
  - One client interface over two transports: Ollama's **native** `/api/chat` (it exposes Qwen3's
    `think` switch and JSON-schema-constrained output via `format`) and Groq's OpenAI-compatible
    `https://api.groq.com/openai/v1`.
  - JSON mode, timeouts and retries with fallback. No silent mock fallback: if no provider works,
    the call fails loudly.
  - Send a real `User-Agent` to Groq (Pranav found a Cloudflare 1010 block without one).
  - Keep Qwen **thinking ON** for extraction (thinking OFF produced empty cards), and add an
    empty-output guard.
  - Log every call locally to a gitignored folder.
- **On-demand GPU host (approved option A):** the team's `qwen3:14b` lives on the shared trijya-3
  box, whose Ollama autostart was disabled on request. With `OLLAMA_REMOTE_SSH` set,
  `llm/remote_ollama.py` starts Ollama over SSH only for a run and stops only its own tagged
  process. Guards: minimum free VRAM; never inside the host's 04:00-06:45 IST power-off window
  (Mon-Sat), with the lifetime capped before it; hard `timeout`; 1 model, 1 request, 2-min keep-alive.
- **CLI:** `python -m pipeline.cli doctor` and `python -m pipeline.cli ollama status|up|down`
- **Acceptance:** `doctor` exits 0 only when: config validates; the Gmail token refreshes with
  **exactly** `gmail.readonly` on the expected account; **at least one** LLM provider is usable (each
  provider's state is shown); the DB and output dirs are writable. `doctor --deep` also runs one live
  JSON completion. **Status: done** (see `pipeline/README.md`).

### Step 1: Ingest
- **Goal:** fetch every new email for an edition's sources, losslessly and exactly once.
- **Input:** edition, window (watermark taken from the last successful run).
- **Do:**
  - Build a Gmail query from the sender list plus `after:`.
  - Fetch with `messages.get(format=raw)` and save the `.eml`.
  - Upsert `emails` by `msg_id`.
  - **Collapse alias duplicates.** TLDR arrives three times via `+tags`; dedupe on the RFC
    `Message-ID` header, or on sender + subject + date.
  - Skip drafts and API errors (log them and continue).
- **Output:** new `emails` rows with `kind = unknown`, and `.eml` files under
  `data/archive/<edition>/<date>/`.
- **Acceptance:** re-running the same window inserts 0 rows, and per-source counts are logged.

### Step 2: Classify the email type
- **Goal:** separate real issues from everything else.
- **Kinds:** `issue`, `welcome`, `confirm`, `verify`, `promo`, `upsell`, `podcast_notice`,
  `event_promo`, `engagement_check`, `other`.
- **Do:** rules first, then the LLM (`prompts/classify.md`) only when the rules say "ambiguous".
  The rules look at:
  - subject regexes (Welcome / Confirm / Verify / "Action Required");
  - **sender aliases** (`pragmaticengineer+deepdives` = analysis, `+the-pulse` = news, base =
    podcast);
  - **subject emoji prefixes** (Exponential View: 🔮 essay, 📈 data, 🚨 breaking, 👀 promo);
  - known engagement checks ("We're Going on a Break", "Yes, I'm real").
- **Side effect:** an `engagement_check` raises an **alert** (a source is about to stop delivering)
  and is never auto-clicked.
- **Acceptance:** every email in the golden fixtures gets the expected kind, and engagement checks
  are alerted on.

### Step 3: Clean and normalize
- **Goal:** structured, ad-free, link-clean text for each `issue`.
- **Do, in order:**
  1. **HTML to Markdown, keeping structure:** headings, lists, tables and links as `[text](url)`.
     If `text/plain` is empty (Axios, Sherwood, Exponential View), **always use the HTML**.
  2. **Split into `sections`** by headings or separators. Examples: Import AI splits on `***`;
     TLDR uses emoji section dividers.
  3. **Detect sponsors** (`clean/sponsors.py`) and set `sections.is_sponsored = true`. Keep the
     text in the archive, and never extract from those sections. The markers are:
     - labels: `(SPONSOR)`, `PRESENTED BY`, `Presented by`, `FROM OUR PARTNERS`,
       `A MESSAGE FROM`, `Sponsored by`;
     - partner asterisks;
     - referral-link domains;
     - house blocks: "FREE RESOURCE", "Shameless promo", "HIGHLY RECOMMENDED";
     - Reg A investment offerings;
     - recs blocks marked "*A message from our sponsor".
  4. **Normalize links** (`clean/links.py`):
     - canonicalize the URL and strip `utm_*`;
     - unwrap known redirect wrappers **only when the target is embedded in the URL itself**;
     - otherwise mark the link `is_tracking = true` and keep it opaque. Never fetch it.
  5. **Detect paywalls and previews** (`clean/paywall.py`): on phrases such as "Subscribe to
     unlock", "Upgrade to paid", "read on" plus truncation, or a 7-day-late "bonus free issue", set
     `emails.is_preview` and `paywall_cut_at`.
  6. **Harvest structural hints** (`clean/structure.py`), with no LLM:
     - subject topic lists: TLDR emoji triples, `Import AI N: a; b; c`, Stratechery `a, b, c`,
       The Diff `Plus! a; b; c`;
     - built-in TOCs: The Diff "In this issue", Pragmatic Engineer "We cover:";
     - the preheader.
- **Borrow:**
  - AI-Weekly-Digest `search._normalize_url` / `_dedupe` / `_unwrap_google_redirect`, adapted to
    Substack, beehiiv and Mailchimp wrappers (MIT);
  - its `verify.py` paywall heuristics (MIT).
- **Acceptance (golden fixtures):**
  - 0 sponsor sections reach extraction;
  - every HTML-only issue has non-empty text;
  - no tracking or subscription link was requested over the network.

### Step 4: Store and archive
- **Goal:** a lossless, queryable record.
- **Do:** write the `.eml`, clean `.md` and sections, links and flags to SQLite in one transaction
  per email.
- **Acceptance:** each `.md` file can be regenerated from its `.eml` alone, and row counts match the
  archive file counts.

### Step 5: Extract story cards and typed modules (MAP)
- **Goal:** turn each non-sponsored section into verified **story cards** and **typed modules**.
- **5a. Rule extractors first** (`extract/rules/`). The structure is regular, so no LLM is needed:
  - Axios signposts: `Why it matters:` / `The bottom line:` become `author_take`.
  - Import AI items: headline, `…subhead…`, `Why this matters`, `Read more`.
  - Pro Rata deal lines become `modules(type=deal)`: company, round, amount, lead investor, sector
    emoji.
  - Market strips and movers lists become `mover` and `market` modules.
  - Calendars ("What to watch", "Week ahead") become `calendar`.
  - Changelog repo lists become `repo`.
- **5b. LLM extractor** (`prompts/extract_card.md`), used where the rules don't apply:
  - **Input:** one section of text plus the source name.
  - **Output (strict JSON):** `cards[]` with:
    - `headline` (neutral, our own words);
    - `what_happened` (1–2 sentences, paraphrased);
    - `author_take` (the source's "so what", paraphrased, or null);
    - `facts[]` of `{claim, value, unit, as_of, evidence}`;
    - `entities[]`, `tickers[]`, `links[]`;
    - `section_tag`, `stance`, `is_opinion`, `is_vendor_claim`.
  - The same call also returns typed `modules[]`: number, quote, term, morsel, tool, prompt.
  - **Rules in the prompt:**
    - use only the given text;
    - `evidence` must be copied **verbatim**, at most 25 words;
    - never invent numbers, URLs or dates;
    - mark self-reported, vendor or leaked figures.
- **5c. Verify in code:**
  - each `evidence` must be an exact substring of the section text; set `verified = true`;
  - otherwise do one repair pass, then drop the fact;
  - repair broken JSON with `llm/json_repair.py`.
- **Borrow:**
  - AI-Weekly-Digest `summarize._parse_json` (JSON repair) and its "never a homepage URL, never
    modify URLs" rule (MIT);
  - tirth1263's "use only provided sources, no invented facts, URLs or dates" rules (MIT, idea);
  - projectgreenhat's fill-in JSON template plus validation (pattern only).
- **Acceptance (golden fixtures):**
  - at least 95% of facts are verified;
  - 0 cards come from sponsor sections;
  - the known typed items are captured: Number of the day, movers, calendar, repos.

### Step 6: Analyze across sources
- **Goal:** turn per-newsletter cards into cross-source **stories with intelligence**. This is the
  part no reviewed repo does; it is our core.
- **6a. Cluster** (`analyze/cluster.py`):
  1. **Candidate pairs:** cards inside the run window that share an entity or ticker, or whose
     headlines are similar (rapidfuzz/SequenceMatcher at about 0.6; borrow the pattern from
     AI-Weekly-Digest `dedup.py`).
     - Optionally add local embeddings via Ollama, and treat high cosine similarity as a candidate.
  2. **Adjudicate borderline pairs** with `prompts/same_story.md` (the same real-world event? yes or
     no, with a reason).
  3. **Keep every member.** Unlike the borrowed dedup, never keep only the "best" card.
- **6b. Coverage** (`coverage.py`):
  - Coverage counts **brands** (defined in `sources.yaml`): all Semafor editions share brand
    `semafor` (= 1), while TLDR and TLDR Dev are separate brands (= 2).
  - `coverage_n` = number of distinct roster brands in the cluster;
  - `roster_n` = number of the edition's roster brands that delivered at least one issue in the run
    window (the "M" in "covered by N of M");
  - `sources` = the covering brands in **roster order** (`editions.yaml`), which drives the coverage strip.
- **6c. Conflicts** (`conflicts.py`):
  1. **In code:** compare facts that measure the same quantity across members (same entity and
     unit, different value). Example: Paramount deal size $81B vs $110B.
  2. **With the LLM** (`prompts/compare.md`): catch differences in wording, such as "proposed" vs
     "approved", or "fired" vs "parted ways".
  3. **Output:** `conflicts[] = {field, values_by_source, likely_reason}`, which drives the
     **Sources differ** badge.
- **6d. The Split** (`split.py`):
  - For clusters with 2 or more members, `prompts/stance.md` labels each member's angle (bull or
    bear, hype or skeptic, its framing).
  - When there are 2 or more distinct supported angles, write
    `split = {sides:[{label, claim, source_ids}]}` with 2–3 sides.
- **6e. Hype check** (`hype.py`):
  - **Flag:** vendor or self-reported benchmarks, small samples, single-source leaks and claims that
    only one source caveats. Example: Tavus "48%" = 26 of 54 people, a company-run test.
  - **Output:** `hype = [{status: confirmed|claimed|unclear, text, source_ids}]`, which becomes the
    **What we actually know** ledger.
- **6f. Freshness** (`freshness.py`): set `stale = true` on events that predate the window, such as
  a DevDay recap or a paywalled piece re-sent free 7 days late.
- **Acceptance (on the golden Oct 1–2 fixtures):**
  - the top clusters and their coverage counts match the story maps within ±1;
  - the known conflicts are flagged: Paramount 81 vs 110; Bain's $6T framing; Gemini pricing
    wording.

### Step 7: Rank and select
- **Goal:** choose what goes into the issue, deterministically.
- **Score:** a **single weighted sum**, never stacked sorts (that is the AI-Weekly-Digest
  sort-order bug):
  `score = 0.40·coverage_norm + 0.25·relevance + 0.15·freshness + 0.10·source_quality + 0.10·split_bonus − penalties`
  (starting weights in `editions.yaml`; tune them against reviewer edits)
  - `relevance`: LLM-as-judge on a 1–10 rubric (`prompts/judge.md`), borrowed from
    AI-Weekly-Digest `rerank.py` (MIT). It falls back to a neutral 5 on error.
  - `source_quality`: starts neutral and is updated by feedback in Phase 2.
  - **Penalties:** stale; single-source vendor claim; preview-only source with no other coverage.
- **Slots** (from `editions.yaml`):

  | Slot | Tech | Finance | How it is chosen |
  |---|---|---|---|
  | The big one | 1 | 1 | **Highest coverage**: a hard number decides, not the LLM. Tie-break by score |
  | Split stories | 1–2 | 1 | Clusters with a `split`, ranked by score |
  | Hype check | 0–1 | 0 | Highest-severity `claimed` ledger |
  | Quick hits | 6–8 | 6–8 | Next by score |
  | Modules | try-this, builders, career, morsels | the close, movers, retail flow, take, term, calendar, morsels | Best verified module of each type |
  | Number of the day | 1 | 1 | The most striking verified `number` module |

  - **Fill-down:** if a slot type is short, fill it from the next priority (an idea from
    news-digest).
- **Acceptance:** the same inputs always give the same selection, and the lead is always the
  highest-coverage cluster.

### Step 8: Compose the issue (REDUCE)
- **Goal:** write the issue as **strict JSON** that the renderer fills in. The LLM never writes
  HTML.
- **Input:** the selected clusters with their cards, verified facts (with IDs), conflicts, split,
  hype and the chosen modules.
- **Style anchor:** include one **approved past issue** of the same edition as the style exemplar
  (`style/exemplar_*.json`, initially our two samples). This idea comes from run-llama, which
  embeds a human-written issue in its prompt.
- **Issue JSON (schema in `compose/compose.py`, validated with pydantic):**
  ```
  { edition, date, issue_no, subject, preheader,
    meta:{newsletters, issues_read, words, read_min, sponsored_removed},
    roster:[source_id…],
    number_of_day:{value, text, source_ids, fact_ids},
    today:[3 strings],
    big_one: STORY, splits:[STORY], hype_check: STORY|null, quick_hits:[STORY],
    modules:{ close?, movers?, retail_flow?, take?, term?, calendar?, try_this?, builders?, career?, morsels:[3] },
    made:{issues_read, newsletters, sponsored_removed, quiet_sources:[…]} }
  STORY = { headline, so_what, body (≤90 words), coverage:{n, of, source_ids},
            badges:[reported|sources_differ|self_reported|paywalled],
            split?:{sides:[{label, text, source_ids}]}, ledger?:[{status, text}],
            links:[{label, url}], source_ids, fact_ids, read_min }
  ```
- **Prompt rules** (`prompts/compose.md`):
  - each story leads with a one-sentence **so what**;
  - neutral headlines, no hype words (borrow the AI-Weekly-Digest banned-word list);
  - **every number must come from a listed `fact_id`**;
  - name the source whenever a claim is contested;
  - at most one quote under 15 words per story;
  - no investment advice;
  - do not invent subject-line facts;
  - subject format = **top 3 stories plus one emoji each**.
- **Acceptance:** the output validates against the schema, and every story has at least one
  `source_id` and one `fact_id`.

### Step 9: Validate (automated gate)
- **Goal:** catch errors before a human sees the issue.
- **Checks** (`validate/checks.py`):
  1. Every number in the copy matches a fact value (unit-aware).
  2. Every story has a source, and no fact comes from a sponsored section.
  3. Links are canonical and not tracking links, and HEAD returns 2xx/3xx within 5s. Paywalled links
     carry the `paywalled` badge.
  4. Badges are consistent: a conflict means `sources_differ`; a vendor claim means `self_reported`;
     a single-source leak means `reported`.
  5. Quotes: at most one per story, each under 15 words, each matching evidence verbatim.
  6. No banned hype words, and no finance-advice phrases ("buy", "sell", "price target" as a
     recommendation).
  7. The word count gives the stated read time (about 230 words/min).
  8. The rendered email is under **102 KB**, so Gmail doesn't clip it (idea from projectgreenhat).
- **On failure:** send the error list back to Step 8, at most 2 retries. If it still fails, mark the
  issue `needs_attention` and let it proceed to review with the errors attached.
- **Acceptance:** the golden run passes with 0 errors, and seeded errors (an invented number, a
  sponsor fact, a dead link) are each caught.

### Step 10: Render
- **Goal:** what the subscriber sees, matching the approved samples.
- **Outputs:**
  - `issue.html`: email-safe, table-based, with CSS inlined by `premailer` (idea from asadcs);
  - `issue.txt`: the plain-text alternative;
  - `issue.web.html`: the browser version;
  - `issue.pdf`: headless Chromium print as one continuous page, measured to the content height.
- **Design elements:**
  - the coverage strip (one square per roster source, filled when covered);
  - the highlighted "so what";
  - the "What we actually know" ledger;
  - Split panels (2–3 sides);
  - badges and the markets table;
  - the movers grid, calendar and morsels;
  - the poll;
  - the "How this issue was made" box.
- **Borrow:** the AI-Weekly-Digest table-based, Outlook-safe `newsletter.html.j2` as the skeleton
  (MIT), restyled to our design tokens:
  - type: Schibsted Grotesk / Source Serif 4 / IBM Plex Mono;
  - accents: Tech vermilion, Finance green;
  - highlighter colour: yellow.
- **Acceptance:**
  - the rendered HTML matches the approved samples' layout;
  - the email is under 102 KB;
  - the plain-text version is present;
  - the PDF is a single page.

### Step 11: Human review (end of v1)
- **Goal:** a person checks and edits every issue before it can go anywhere.
- **Output folder** `out/<date>/<edition>/`:
  - `issue.json`, `issue.html`, `issue.pdf`;
  - `validation.md` (the check results);
  - `trace.md`: every story → its cluster → member cards → facts → evidence → Gmail message ids.
- **Do:**
  - The reviewer edits `issue.json`, or overrides a slot.
  - `pipeline review --render` re-renders the issue.
  - `pipeline review --approve | --reject --notes "…"` records the decision.
  - The reviewer's diff is stored so prompts can be improved later.
- **Acceptance:** an issue can move to `approved` only through this command. Nothing in v1 sends
  email.

### Step 12: Orchestration
- **Commands:**
  - `pipeline run --edition tech|finance [--date YYYY-MM-DD] [--from-stage N]`
  - `pipeline doctor`
  - `pipeline status`
- **Schedule:** local OS scheduler (Windows Task Scheduler or cron), because Gmail access is
  local-only:
  - **Tech** about 09:30 ET, after Superhuman (~09:16 ET) arrives;
  - **Finance** about 17:00 ET, after Brew Markets (~16:15 ET) arrives;
  - the reference arrival times are Snacks 06:30, TLDR ~06:40, Axios Markets 07:30, EntryPoint
    ~08:30, Businessweek ~13:00 and Money Stuff ~14:00 ET.
- **Alerts:**
  - a source that has been quiet longer than its cadence;
  - an engagement-check email;
  - LLM fallback used repeatedly;
  - validation failures;
  - the Gmail token is about to expire. Testing-mode OAuth tokens expire about every 7 days, so
    publish the OAuth app or re-auth.

---

## 5. Phase 2: approval-gated automation
Do this only after v1 has produced reviewed issues reliably.
1. **Status flow:** `approved → scheduled → sent`. **Only `approved` issues can be scheduled.** There
   is no auto-approve.
2. **Sending:**
   - Use a separate, local `gmail.send` token (or an email service later).
   - Create a Gmail draft first.
   - Use a `[TEST]` mode that sends to the internal list.
   - Add an idempotency key (`edition + date`) as a double-send guard.
   - Send multipart HTML plus text.
   - Include the unsubscribe link and the legally required footer.
3. **Approve → send loop:** once a reviewer runs `--approve`, the scheduler sends the issue at the
   edition's slot time with no further manual step. This is the "fully automated after review" line.
4. **Feedback:**
   - The poll links ("Loved it / It was fine / Not for me") write to a `feedback` table.
   - A per-newsletter `source_quality` score is kept in SQLite: how often its cards make the final
     cut, adjusted by reader feedback. This is the idea from AI-Weekly-Digest `SourceTracker`, moved
     into SQLite. It feeds `source_quality` in the Step 7 score.
5. **Learning from edits:** periodically mine the reviewer diffs to tighten prompts and swap in a
   better style exemplar.

## 6. Phase 3: outside, live data
1. **Collectors** produce the same `emails`-like items with `source_type = web`:
   - Hacker News, arXiv and RSS (pattern from AI-Weekly-Digest, MIT);
   - GitHub Trending, for the repos module (pattern from projectgreenhat);
   - **Techmeme's RSS** as a daily baseline of what's big;
   - **engineering-leadership RSS feeds** (feed URLs only, from gregorojstersek's OPML);
   - **web search through Agent-Reach / Exa** (free) in place of paid Tavily or Perplexity.
2. **Flow:** web items go through Steps 3–10 unchanged. In clusters they count separately:
   "covered by N newsletters + M web sources".
3. **Stricter copyright:** for web items, link with at most a 2-sentence summary. Never take full
   text.
4. **Topic research:** a research step for the lead story fills `{statistics with source,
   controversies, outlook}`, a shape borrowed as an idea from asadcs. It strengthens The Split and
   the ledger.

## 7. Borrow map (from the repos reviewed)

| Piece | From | License | Use |
|---|---|---|---|
| URL normalization, dedupe, redirect unwrap | not-indro/AI-Weekly-Digest | MIT | Copy with notice → `clean/links.py` |
| Title-similarity clustering | AI-Weekly-Digest `dedup.py` | MIT | Adapt → `analyze/cluster.py`, **keeping all members** |
| Paywall / soft-404 checks | AI-Weekly-Digest `verify.py` | MIT | Adapt → `clean/paywall.py`, `validate/checks.py` |
| JSON repair; anti-hype word list; summary rules | AI-Weekly-Digest `summarize.py` | MIT | Copy → `llm/json_repair.py`, `prompts/` |
| LLM-as-judge 1–10 rerank | AI-Weekly-Digest `rerank.py` | MIT | Adapt → `rank/score.py` (single weighted score) |
| Outlook-safe email template | AI-Weekly-Digest `newsletter.html.j2` | MIT | Skeleton → `render/templates/email.html.j2` |
| Source quality + feedback | AI-Weekly-Digest `source_quality.py`, `api/feedback.py` | MIT | Phase 2, re-implemented in SQLite |
| HN / arXiv / RSS collectors | AI-Weekly-Digest `search.py` | MIT | Phase 3 |
| "Only provided sources, no invented facts, URLs or dates" | tirth1263/newsletter-generator | MIT | Prompt rules |
| Past issue as style exemplar; hard metric picks highlights | run-llama/newsletter-generator | MIT | Idea (its code is tied to Claude) |
| Fill-in JSON template + validation; 102 KB clip warning; test mode; double-send guard; GitHub Trending | projectgreenhat/newsletter-automation | Unclear (no LICENSE file) | **Patterns only. Re-implement** |
| premailer CSS inlining; draft-first send; per-section source boxes | asadcs/ai-content-automation-system | None | **Ideas only** |
| Category quota fill-down rule | Ezerhmu/news-digest | None | **Idea only** |
| Newsletter catalog (tech, dev, security) | zudochkin/awesome-newsletters | CC0 | Source discovery for `sources.yaml` |
| Engineering-leadership feed URLs | gregorojstersek/resources-… | None | Feed URLs for Phase 3; don't redistribute the list |

**Bugs to avoid when borrowing from AI-Weekly-Digest:**
- stacked stable sorts (use the single weighted score instead);
- its Hacker News keyword filter matches `ai` inside other words (use word boundaries);
- curated RSS items are never labelled as RSS.

## 8. Testing
- **Golden fixtures (local only, never committed, because they contain third-party text):**
  - the Oct 1–2, 2026 inbox issues: 18 finance and 27 tech emails, already captured as raw text;
  - the two approved sample issues;
  - the two story maps (cluster lists, conflicts, sponsor lists).
  - Tests read them from a path set in `settings.py`, and are skipped if it's absent.
- **Unit tests:** each `clean`, `extract/rules`, `analyze` and `validate` function, plus the patterns
  from the AI-Weekly-Digest tests (dedup, UTM handling, verify).
- **Regression metrics, reported each run:**
  - sponsor leakage (must be 0);
  - the share of facts verified (must be at least 95%);
  - cluster coverage accuracy against the story maps;
  - validation errors;
  - the size of the reviewer's edit diff.

## 9. Definition of done (v1)
- [ ] `pipeline run --edition tech` and `--edition finance` produce `issue.json`, `.html`, `.txt`,
      `.pdf`, `validation.md` and `trace.md` for a given day, end to end, using only local Qwen and
      Groq.
- [ ] On the golden fixtures, the output matches the samples' structure:
  - coverage counts within ±1 of the story maps;
  - known conflicts flagged;
  - 0 sponsor content;
  - 0 unverified numbers.
- [ ] Every fact in the issue traces back to an email and an evidence snippet.
- [ ] Re-running a day changes nothing (idempotent), and a failed run resumes from the failed stage.
- [ ] Nothing is sent. Issues stop at `in_review` until a human approves them.
