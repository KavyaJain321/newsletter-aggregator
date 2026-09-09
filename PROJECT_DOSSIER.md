# 📓 Newsletter Aggregator — Complete Project Dossier

> **What this is:** the single, exhaustive reference for the whole project — history, research,
> every decision, all designs, the data, the strategy, and the hard-won learnings.
>
> **How to use it:** this is a **deep-reference, read on demand** — it is deliberately **NOT
> auto-loaded** every session (that's `CLAUDE.md` → `PROJECT_CONTEXT.md`'s job, kept short to save
> context). Come here when you need the full detail on any topic. `data/sources.csv` is the live
> per-newsletter status; this doc is the "why and how" behind everything.
>
> **Maintained by:** tdsworks@gmail.com · **Repo:** https://github.com/KavyaJain321/newsletter-aggregator

---

## Table of contents
1. Executive summary
2. Goal & vision
3. History & the key pivot (KTN → Gmail)
4. Gmail infrastructure (account, +tags, filters)
5. The 45 newsletters — full catalog by segment
6. Subscription status & how we verify it correctly
7. The 4 dead newsletters + recommended alternatives
8. Content-structure research (the 5 shapes)
9. Editorial analysis — News segment source USPs
10. Product strategy — building our OWN newsletter
11. The 6 sample issues (pointer)
12. Phase 4 — capture / archive design
13. Phase 5 — LLM enrichment design (non-Claude)
14. Tech stack & tooling (Gmail API, OAuth, tokens)
15. Collaboration & cloud model
16. Key learnings / gotchas (consolidated)
17. Roadmap & open items
18. File index
19. Timeline

---

## 1. Executive summary
A pipeline that subscribes **one dedicated Gmail** (`notifyy1008@gmail.com`) to **~45 newsletters
across 9 topic segments**, auto-sorts them with Gmail filters into per-segment folders, will
**archive every issue** into a structured store (`.eml` + clean `.md` + SQLite), and will finally
**summarize them with a non-Claude LLM (Groq / local Qwen)** into our **own aggregated digest
newsletter** per segment.

**Status (verified live):** **38 of 45** confirmed delivering real issues; **41 subscribed** total;
**4 genuinely dead**. **500+** newsletter emails received. Phases 1–3 done; Phase 4 (archive)
designed + proven on one email; Phase 5 (enrichment) designed; Phase 6 (digest product) scoped with
six sample issues.

---

## 2. Goal & vision
- **Practical goal:** stop drowning in 20–30 newsletters/day; get one distilled digest instead.
- **Product goal:** build our **own** newsletter per segment that aggregates the sources — we produce
  no original reporting, so we win on the **synthesis/curation layer** no single source can build
  (see §10). Starting focus: the **News** segment.

---

## 3. History & the key pivot (KTN → Gmail)
- **Original approach (abandoned):** Kill-the-Newsletter (KTN) — a service turning emails into RSS
  feeds, one feed per segment. Auto-subscription via Playwright hit CAPTCHAs/paywalls and, critically,
  **many sites blocked the `kill-the-newsletter.com` address** → only 3 of 45 subscribed. Retired.
  The KTN-era scripts (`scripts/phase2*`, `debug_ktn*`) remain for reference only — **obsolete**.
- **Current approach:** a single real Gmail with **plus-addressing** (`+tag`) so each segment gets its
  own auto-labeled folder, while all mail lands in one inbox. Real Gmail signs up far more reliably.

---

## 4. Gmail infrastructure

### Account & plus-addressing
- **One account:** `notifyy1008@gmail.com`. No other accounts exist.
- **Plus-addressing:** `notifyy1008+techai@gmail.com` etc. all deliver to the one inbox; the `+tag`
  is used by filters to apply a per-segment label. No setup needed per address — Gmail does it natively.

### The 9 segments → address → label
| Segment | Subscribe address | Gmail label |
|---|---|---|
| 1-TechAI | notifyy1008+techai@gmail.com | Newsletters/1-TechAI |
| 2-BizFinance | notifyy1008+biz@gmail.com | Newsletters/2-BizFinance |
| 3-Legal | notifyy1008+legal@gmail.com | Newsletters/3-Legal |
| 4-HRPeopleOps | notifyy1008+hr@gmail.com | Newsletters/4-HR |
| 5-GitHubRepos | notifyy1008+github@gmail.com | Newsletters/5-GitHub |
| 6-IndieHacker | notifyy1008+indie@gmail.com | Newsletters/6-IndieHacker |
| 7-Absurdist | notifyy1008+satire@gmail.com | Newsletters/7-Absurdist |
| 8-MicroSmallCap | notifyy1008+smallcap@gmail.com | Newsletters/8-SmallCap |
| 9-MainstreamNews | notifyy1008+news@gmail.com | Newsletters/9-News |

### Filters (three kinds)
1. **Tag-based (9):** match on **`deliveredto:notifyy1008+<tag>@gmail.com`** (NOT the "To" field — it's
   unreliable for plus-addresses) → apply the segment label. Imported from `gmail_filters.xml`.
2. **Sender-based (4):** for sites that **rejected the `+`**, we subscribed with the **plain** address
   and route by **sender domain**: Morning Brew (`morningbrew.com`)→2-BizFinance, HR Brew
   (`hrbrew@morningbrew.com`)→4-HR, FindLaw (`findlaw.com`)→3-Legal, Babylon Bee
   (`babylonbee.com`)→7-Absurdist. From `gmail_filters_sender.xml`.
3. **Lawfare fix:** Lawfare was subscribed via a Substack recommendation on the `+techai` address, so
   it lands in 1-TechAI; `gmail_filter_lawfare.xml` re-tags it to 3-Legal.

### Setup mechanics learned
- Filters must be created with the **search bar empty** (creating them while viewing a label bakes a
  stray `label:newsletters` match condition that never fires on new mail — this bit us; fixed by
  re-importing clean XML).
- Gmail's **Import filters** (Settings → Filters → Import) accepts an Atom XML file — how we bulk-created
  and fixed all filters.

---

## 5. The 45 newsletters — full catalog by segment
Legend: ✅ active (issues arriving) · 🟡 subscribed/pending · ❌ dropped · **(plain)** = plain-address+sender-filter

**1 — Tech/AI (+techai)** — TLDR ✅ · Superhuman AI ✅ · The Neuron ✅ · The Pragmatic Engineer ✅ (weekly, Tue) · Import AI ✅ (weekly, Mon)

**2 — Business/Finance (+biz)** — Morning Brew ✅ **(plain)** · The Hustle ✅ · The Daily Upside ✅ · The Average Joe ✅ (3×/wk) · The Diff ✅ (weekly)

**3 — Legal (+legal)** — Above the Law ✅ · National Law Review ✅ · FindLaw ✅ **(plain)** · SCOTUSblog ✅ · Lawfare ✅ (arrives under 1-TechAI)

**4 — HR/People Ops (+hr)** — HR Brew ✅ **(plain)** · HR Dive ✅ (very active) · SHRM HR Today ✅ · I Hate It Here ✅ (low volume) · **Workology ❌ dropped** (no signup option)

**5 — GitHub/Dev (+github)** — Changelog Nightly ✅ · TLDR WebDev ✅ · Console ✅ (Fri) · Bytes ✅ (Tue) · DevOps'ish ✅ (Fri)

**6 — Indie Hacker (+indie)** — Indie Hackers ✅ · Starter Story ✅ · The Bootstrapped Founder 🟡 (needs confirm-email click, Arvid Kahl) · Trends.vc ✅ (Sun) · No CS Degree 🟡 (subscribed, silent)

**7 — Absurdist/Satire (+satire)** — The Onion ✅ · Reductress ✅ · Babylon Bee ✅ **(plain)** · **The Hard Times ❌ dropped** (404/no signup) · The Beaverton ✅

**8 — Micro/Small-Cap (+smallcap)** — Zacks SCR Digest ✅ · **Small Cap Discoveries ❌ dropped** (paid) · RedChip 🟡 (needs code `1fcc44` entered on site) · Planet MicroCap ✅ · **OTC Adventures ❌ dropped** (Substack deleted)

**9 — Mainstream News (+news)** — NYT Morning Briefing ✅ (daily) · Washington Post The 7 ✅ (daily) · The Guardian ✅ (many editions) · Axios AM ✅ (daily) · Semafor ✅ (10 regional editions)

**Bonus subscriptions** (from Substack "recommended" checkboxes, now flowing): SmallCap gained Boyar
Research, Mindset Value, Value Investing World, The Intellectual Investor, Behind the Balance Sheet.
News gained many extra Guardian editions + all Semafor regional editions (why News volume is huge).

---

## 6. Subscription status & how we verify it correctly

### Current numbers (committed to `data/sources.csv`)
- `confirmed_active` 38 · `subscribed` 1 (No CS Degree) · `subscribed_pending_confirmation` 1
  (Bootstrapped Founder) · `pending_confirmation` 1 (RedChip) · `dropped` 4.
- **41 subscribed, 38 actively delivering, 4 dead.** 500+ emails received.

### How verification works
This session (local) reads the **actual `notifyy1008` inbox live** via the authenticated `google-skill`
Gmail API tool (read-only OAuth). We list messages, extract From/To/Subject/Date, MIME-decode subjects,
map each to a newsletter, and mark it active if a **real issue** (not welcome/confirm) arrived.

### ⚠️ Verification correctness rules (learned the hard way — a teammate's device got this wrong)
To avoid false "not subscribed" reports, any delivery check MUST:
1. **Search `in:anywhere`, NOT `in:inbox`** — filters archive mail under labels (skip-inbox), so an
   inbox-only search sees nothing.
2. **Match the 4 plain-addressed ones by SENDER domain, not by `+tag`** — Morning Brew, **HR Brew**,
   FindLaw, Babylon Bee arrive at plain `notifyy1008@gmail.com`. A `to:+hr` search misses HR Brew and
   falsely flags it as unregistered (this exact mistake happened).
3. **MIME-decode subjects** (`=?utf-8?...`) before testing for "confirm/welcome" — otherwise encoded
   confirm emails look like real issues (mislabeled The Diff / No CS Degree once).
4. **Read the account that actually has the mail** — only `notifyy1008` via the local `google-skill`
   OAuth. A different Gmail connector may point at a different/empty account and report zeros.
5. **`git pull` the latest `sources.csv`** — old commits carry stale Aug-2 "CAPTCHA/paywall" notes
   from the first KTN-era attempt, not current reality.

---

## 7. The 4 dead newsletters + recommended alternatives
| Dead | Segment | Why | Best free alternative(s) |
|---|---|---|---|
| Workology | HR | No newsletter signup | **Recruiting Brainfood** (Hung Lee), People Managing People |
| The Hard Times | Absurdist | 404 / no signup | **McSweeney's Internet Tendency**, The Betoota Advocate, ClickHole |
| Small Cap Discoveries | SmallCap | Paid only | **MicroCapClub**, Kingswell (also: bonus Substacks already flowing) |
| OTC Adventures | SmallCap | Substack deleted | (same as above) |

Also skippable: **RedChip** (promotional IR firm, low editorial value — could drop rather than enter the code).
Keep-but-click: **Bootstrapped Founder** (good; just confirm the email).

---

## 8. Content-structure research (audit of ~70 real issues)

### Universal facts (all newsletters)
- Every newsletter is HTML; **~70% also ship `text/plain`** (easier to parse); ~30% are **HTML-only**
  (all Semafor editions, Axios, NYT, most Substacks).
- **Images are always remote URLs** (0 inline/attached across all). **Zero attachments** anywhere →
  store image URLs, not files. `<img>` counts are inflated by tracking pixels/spacers → filter them.
- Some free Substacks send **truncated previews** (teaser + "read online") — full text is on the web.

### The 5 content shapes (restricted to our 45; ~31 classifiable; ~52% roundup)
- **Links-roundup (16):** multi-story digest — Morning Brew, The Hustle, Daily Upside, Above the Law,
  FindLaw, SCOTUSblog, HR Brew, HR Dive, SHRM, Trends.vc, The Onion, NYT, Axios, Semafor, Superhuman, The Neuron.
- **Brief/sectioned (11):** TLDR, TLDR WebDev, Console, Bytes, Indie Hackers, Starter Story, National
  Law Review, Lawfare, Babylon Bee, Zacks, Washington Post.
- **Content essay (2):** The Average Joe, The Diff.
- **Image+content (1):** The Guardian.
- **Teaser/preview (1):** Planet MicroCap.
- **Parser priority:** build the links-roundup extractor first, then brief/sectioned, then essay/teaser.

---

## 9. Editorial analysis — News segment source USPs
- **NYT "The Morning":** one deep explainer/day, named writer, authority. Funnel to paid.
- **Washington Post:** scannable link-roundup, strong investigations, but paywalled/monetized.
- **The Guardian "First Edition":** one deep-dive + 5 stories, **personality/wit**, free (reader-funded).
- **Axios AM:** **"Smart Brevity"** — bolded "Why it matters", emoji, word-count/read-time, speed. Free/sponsored.
- **Semafor:** the **"Semaform"** — News / Reporter's View / Room for Disagreement / View from elsewhere;
  **transparency + global** (10 editions). Free.
- **Takeaway:** each wins on ONE ownable trait (brevity / transparency / voice / deep-explainer / scoops).

---

## 10. Product strategy — building our OWN newsletter

### Why we can compete without original content
Our product is the **synthesis/curation layer above** the sources. Each source is trapped inside its
own walls and cannot compare itself to competitors — we can. This is also why we're **not dependent on
any single source**: sources are interchangeable fuel; redundancy means losing one loses ~0 coverage;
ingestion is modular.

### USPs (ranked)
1. **Consensus vs. Conflict** — per story: agreed facts vs. how outlets diverge. *(killer feature)*
2. **Bias-balancing / neutrality** — read across the spectrum in one place.
3. **Cross-source salience** — "4 of 5 outlets led with this."
4. **One inbox, not five** (convenience). 5. **Personalization** (topics/length/tone).
6. **Memory / archive moat** — story timelines, "slow burn" early detection, prediction tracking.

### Signature techniques
Consensus Meter · Prediction Ledger (score the pundits) · "What you can ignore today" ·
Dinner-Party Line (shareable) · Good-News Close · layered depth (30s/3min/deep) · Steelman of the day ·
Your Blind Spots · Ask-the-newsletter · mood toggle · honest slow-day.

### Positioning & verdict
> **"5 minutes. Every side. Zero doom."**
Ship **A's ingredients at B's length**; lead marketing with **Consensus**; use **Voice** as seasoning.

### Guardrails
Stay **transformative** (summaries + attribution + links back); **never** republish full paywalled text.
Closest real competitor to study: **Ground News**.

---

## 11. The 6 sample issues (pointer)
Six News-segment sample newsletters (from real Aug-7 stories) are preserved **verbatim** in
**`NEWSLETTER_SAMPLES.md`**: A Full-Stack · B Ultra-Brief · C Consensus-only · D Deep-dive ·
E Voice · F Neutral-Wire — plus the strategy above. That file is the Phase-6 design starting point.

---

## 12. Phase 4 — capture / archive design (full detail in `PHASE4_DESIGN.md`)

### Two-stage pipeline
- **Stage A — Capture (deterministic, no AI, free):** pull each new message from Gmail → save raw `.eml`
  (lossless) + clean `.md` (text) + a `messages` DB row. Idempotent on the permanent `gmail_id` → never
  miss, never duplicate; a missed run self-heals on the next run.
- **Stage B — Enrich (LLM):** see §13.

### Fetch method options (all give lossless raw email)
- **Gmail REST API (chosen):** `messages.list` (paginate) + `messages.get(format=raw)` = the exact
  `.eml`. Free. Already working via `google-skill`.
- **IMAP + App Password:** standard alternative, no Google Cloud project (needs 2FA). `X-GM-RAW`/
  `X-GM-LABELS`/`X-GM-MSGID` extensions make it nearly as rich as the API.
- Browser scrape (Playwright) and Google Takeout (.mbox) are fallbacks only.

### What one email yields (proven on Above the Law)
Envelope: `id`, `threadId`, `labelIds` (incl. our segment label), `snippet`, `sizeEstimate`,
`internalDate`. Headers: From/To/**Delivered-To** (segment tag lives here), Subject, Date, Reply-To,
List-Unsubscribe, DKIM/SPF/ARC (→ sending platform, e.g. HubSpot). Body: `text/plain` + `text/html`
(+ any attachments, though there are none). Derived: sender name/email, segment, is_issue, word_count,
reading_minutes, all links (deterministic href extraction), content_hash.

### Folder structure
```
data/archive/<segment>/<YYYY-MM-DD>/<slug>__<gmailid>.eml   (raw, lossless)
data/archive/<segment>/<YYYY-MM-DD>/<slug>__<gmailid>.md    (clean text)
data/archive/index.db                                       (SQLite catalog)
```
`data/archive/` is **gitignored** (regenerable + contains third-party copyrighted content).

### Never-miss guarantees
Keyed on `gmail_id` (dedupe) · raw `.eml` kept forever (re-enrichable) · `sync_log` audit · scheduled
runs that backfill · schema validation on LLM output.

---

## 13. Phase 5 — LLM enrichment design (NON-CLAUDE, swappable)
- **Provider-agnostic:** Groq (cloud, free tier, fast) OR local Qwen via Ollama (private, free) OR any
  OpenAI-compatible endpoint. Switch = change `base_url` / `model` / `api_key`. **Never Claude.**
- One JSON object per issue → schema-validated → fanned out into DB tables. Records **which** model
  produced it (`llm_provider`, `llm_model`, `prompt_version`, `raw_json`) for reproducibility.
- **SQLite tables:** `messages` (capture) · `enrichment` (tldr, headline, tone, sentiment, importance,
  main_topic + provenance) · `claims` (claim_text, type fact/prediction/opinion, subject, context) ·
  `quotes` (text, speaker, role, context) · `links` (url, anchor, domain, type) · `entities` (name,
  type person/company/product/ticker/law_case, mention_count) · `stats` (value, unit, description) ·
  `topics` · `sync_log`.

---

## 14. Tech stack & tooling

### The Gmail tool
- **`tools/google-skill/`** — clone of https://github.com/The-Focus-AI/google-skill, talks to the Gmail
  API over OAuth. We **narrowed the scope to `gmail.readonly`** (edited `scripts/lib/auth.ts`) and
  **removed the repo's embedded client secret** (GitHub push-protection flagged it; we don't use it).
- **Own Google Cloud OAuth creds** were created (project `newsletter-reader`, Desktop client). The
  repo's shared/embedded creds don't work (locked to the authors' testers).
- **Secrets (local, gitignored, never pushed):** `~/.config/google-skill/credentials.json` (OAuth
  client) and `tools/google-skill/.claude/google-skill.local.json` (refresh token).
- **Commands (run from `tools/google-skill/`):**
  - `npx tsx skills/gmail/scripts/gmail.ts auth` — browser OAuth
  - `npx tsx skills/gmail/scripts/gmail.ts list --query="in:anywhere newer_than:2d" --max=50`
  - `npx tsx skills/gmail/scripts/gmail.ts read <message-id>`
- Also `tools/google-skill/export_inbox.ts` — bulk-exports the inbox to `.eml` + `emails.csv/json`.

### ⚠️ Token expiry (recurring gotcha)
The OAuth app is in **"testing" mode**, so refresh tokens **die after ~7 days** (`invalid_grant`).
Re-auth = re-run the `auth` command (30s browser consent). **Durable fix:** *publish* the app in
Google Cloud Console (Audience → Publish) so tokens stop expiring. The Gmail API itself is **free**
(the "$300 credit" banner is irrelevant; no billing needed).

### Other environment notes
- Node v24, pnpm, git, Python 3.14 present. `gh` CLI is **not** installed locally.
- After the repo was moved up a level (see §16), `pnpm install` had to be re-run (pnpm's symlinked
  `node_modules` doesn't survive a directory move).

---

## 15. Collaboration & cloud model

### Repo & workflow
- **Branches + PRs.** Don't push real changes straight to `main`; open a PR; owner reviews the diff.
  See `CONTRIBUTING.md`. A PR template lives at `.github/pull_request_template.md`.
- **`CLAUDE.md`** auto-loads every session → points at `PROJECT_CONTEXT.md` so each teammate's session
  starts caught-up ("continue the shared thread").
- **`PROJECT_CONTEXT.md`** = short handoff + Session Log (the shared "discussions" record).
- **Session-log hook** is **local-only** (`.claude/settings.local.json`, gitignored) — it appends an
  auto session outline on your machine only. It was moved out of shared settings because in cloud it
  auto-created a PR per session (noise).

### Gmail is LOCAL-only
Only a session with the authenticated `google-skill` tool can read the inbox. **Cloud/teammate sessions
usually can't** (secrets aren't in the repo, by design). Do Gmail work locally, push results (e.g.
`sources.csv`); teammates `git pull`. Don't wait on Gmail in the cloud.

### Cloud limitations observed
- Cloud sessions **can't read `notifyy1008` Gmail** (no local token).
- Cloud sessions **can push but can't delete remote refs** (org egress policy 403 on ref-deletes) →
  branch/cleanup deletes are a **local-session job**.
- Cloud agents work on a branch + open a PR by default (good for teammate changes; was noise for the
  auto session-log, hence the hook move).

### The local↔cloud data-source gap (important lesson)
A teammate's cloud device reported many active newsletters as "not subscribed." Root cause: it was
searching by `+tag`/`in:inbox` (missing plain-addressed + archived mail), and/or pointing at a different
Gmail, and/or reading stale statuses. **The committed `sources.csv` (verified live locally) is the
source of truth.** See the correctness rules in §6.

---

## 16. Key learnings / gotchas (consolidated)
- **Plus-addressing is rejected by some sites** (Morning Brew, HR Brew, FindLaw, Babylon Bee) → use
  plain address + a sender-domain filter. Any delivery check must match these by **sender**, not tag.
- **Gmail "To"-field filters are unreliable for `+tags`** → use `deliveredto:` in "Has the words".
- **Creating a filter while inside a label** bakes a stray `label:` match that never fires → create with
  the search bar empty; bulk-fix via Import filters (XML).
- **Subjects are MIME-encoded** → decode before classifying confirm-vs-issue.
- **Testing-mode OAuth tokens expire ~7 days** → re-auth, or publish the app.
- **Substack "recommendations"** silently add bonus subscriptions (extra SmallCap Substacks, etc.).
- **Free Substack tiers can send truncated previews** — full text is on the web.
- **`in:anywhere` ≠ `in:inbox`** — archived/labeled mail is invisible to inbox-only searches.
- **Repo was accidentally double-nested** (`newsletter-aggregator/newsletter-aggregator`), which blocked
  "Move to cloud"; fixed by lifting the repo to the session root (then `pnpm install` again).
- **GitHub push-protection** blocks commits containing secrets (caught the google-skill embedded secret).
- **Cloud can't delete remote branches** (egress policy) — do it locally.

---

## 17. Roadmap & open items
- [ ] **Close out the last few:** confirm Bootstrapped Founder; enter RedChip code (or drop it);
      re-check No CS Degree next cycle; optionally swap the 4 dead for the §7 alternatives.
- [ ] **Publish the OAuth app** so Gmail stops expiring weekly.
- [ ] **Build Phase 4 capture script** (polished cleaner that strips tracking URLs + separate
      links/images tables + SQLite writes) and run a full backfill of the inbox.
- [ ] **Set the daily auto-sync** (scheduler).
- [ ] **Pick the Phase-5 LLM** (Groq to start vs local Qwen) and wire enrichment.
- [ ] **Finalize the News digest template** (from Sample A) + the section-generation prompts.
- [ ] **Optional:** trim bonus subscriptions (many Guardian/Semafor editions inflate News/HR/SmallCap).

---

## 18. File index
| File | What |
|---|---|
| `PROJECT_DOSSIER.md` | THIS file — the exhaustive deep reference (read on demand) |
| `PROJECT_CONTEXT.md` | Short handoff + Session Log (auto-referenced by CLAUDE.md) |
| `CLAUDE.md` | Auto-loaded orientation for every session |
| `CONTRIBUTING.md` / `.github/pull_request_template.md` | Team PR workflow |
| `PHASE4_DESIGN.md` | Archive + LLM-enrichment design + full DB schema |
| `NEWSLETTER_SAMPLES.md` | The 6 sample issues (verbatim) + product strategy |
| `NEWSLETTER_SCHEDULE.md` | Per-newsletter frequency & expected delivery |
| `data/sources.csv` | Live per-newsletter status tracker (source of truth) |
| `data/category_feeds.csv` | 9 segments → +tag → label mapping |
| `gmail_filters*.xml`, `gmail_filter_lawfare.xml` | Importable Gmail filters |
| `tools/google-skill/` | Gmail-API tool (secrets & node_modules gitignored) |
| `tools/google-skill/export_inbox.ts` | Bulk inbox → .eml + CSV/JSON exporter |
| `scripts/session_log.py` | Local session-log hook script |
| `scripts/phase2*`, `scripts/debug_ktn*` | KTN-era Playwright — OBSOLETE |
| `RESUME.md`, `GMAIL_SETUP.md`, `SIGNUP_*.md`, `FINISH_ACTIONS.md` | Setup/checklist docs (mostly historical) |

---

## 19. Timeline
- **~Aug 2:** KTN retired; pivoted to Gmail `+tags`; created 9 filters (via imported XML after fixing a
  `label:` bug); worked through 45 signups (many CAPTCHA/paywall — 4 required plain-address fallback).
- **Aug 2–3:** confirmations + redos; first real issues began arriving; content-structure audit.
- **Aug 6–7:** set up Gmail API read access (own Google Cloud OAuth, `gmail.readonly`); live-verified
  subscriptions; designed Phase 4 + 5; ran editorial analysis + built the 6 sample issues; created the
  team handoff + collaboration setup; published the repo to GitHub; moved repo to session root for cloud.
- **Aug 8:** re-auth after token expiry; live count (500+ emails; 38 active); resolved the local↔cloud
  reporting gap; saved samples + strategy to files.
- **(ongoing):** Phase 4 build is the next milestone.

---

*End of dossier. For live status always check `data/sources.csv`; for the short shared context see
`PROJECT_CONTEXT.md`. This file is the deep archive of the "why and how".*
