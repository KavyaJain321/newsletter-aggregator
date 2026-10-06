# Newsroom pilot plan: 4 daily newsletters with Claude Code agents (60 days)

**Decision (team, 2026-10-06):** pause building the automated pipeline. For 1-2 months, produce the
newsletters with Claude Code agents plus a human editor, learn what works, then automate only what
proved worth it. This plan replaces `instruction.md` Steps 2-12 for the pilot; Step 1 (Gmail ingest
into Supabase) and the renderer are kept and reused.

---

## 0. The plan on one page

- **Four editions, weekdays:** Tech/AI, Markets, Trading, Jobs & Careers. Each has a **fixed
  skeleton** (same sections, same order, word budgets). Every issue is a JSON file that must pass
  `pipeline/compose/schema.py`, then the existing renderer makes the email.
- **Fresh data only:** news must be published in the **24 hours before the edition's cutoff**,
  measured by original publish time (not when we fetched it). Evergreen modules (term of the day,
  try-this) are exempt because they aren't news.
- **Scripts collect, agents judge.** Collection is deterministic scripts and existing tools (Gmail
  ingest, RSS/APIs, YouTube Data API, yt-dlp, Apify for X). Agents never browse while writing;
  they only use the collected, cited material.
- **Nine agent roles** in a fixed relay with files between them:
  Collect -> Triage -> Research -> Write -> Fact-check -> Standards -> Publish.
  Every failure has a bounded fix loop (max 2 rewrites), then the story is dropped, never shipped wrong.
- **A human approves every issue** (10-15 min). A hook blocks scheduling without a signed approval file.
- **Readers never see our sources** (rule 11): primary-source credit only; other newsletters' own
  opinions and scoops are never used. Enforced by a test on every render.
- **Biggest gaps to close in week 0:** Trading and Jobs have **zero** inbox sources today; Reddit's
  free access is reportedly ending mid-pilot; market-data APIs mostly forbid republishing numbers;
  SEBI rules forbid buy/sell calls; Gmail's OAuth token expires weekly until the app is published;
  a new sending domain needs DNS auth and warm-up.

---

## 1. What we keep, what changes

| Keep (already built and tested) | Change |
|---|---|
| Gmail ingest -> Supabase `documents` (dedupe of TLDR-style alias copies, 24h watermark, spam/trash) | Extract/compose/validate are done by **agents**, not pipeline code |
| Supabase content store (raw -> structure -> meaning -> topics) as the shared memory and seen-store | `CLAUDE.md` hard rule "no Claude in the capture pipeline" becomes: *pilot uses Claude Code agents for editorial work; collection stays scripted* (owner decision) |
| Issue JSON contract + email renderer + the "never name a source newsletter" test | Add schema blocks for **Jobs** (role list) and **Trading** (dashboard with data credit) |
| Design (`design/samples/*_2026-10-05`) as the style exemplars | Send time and window per edition (section 3) |

Current inbox inflow (measured in Supabase, Sep 28 - Oct 5): **Tech 10-13 issues per weekday, Finance
5-14; weekends 3-6. Trading 0. Jobs 0.**

---

## 2. Decisions the team must make (with recommendations)

| # | Decision | Recommendation |
|---|---|---|
| D1 | Primary audience and time zone | **US-morning sends, produced in the IST afternoon.** Our sources are US-centric, and a US 6:30-8:00 ET send = 16:00-17:30 IST, so the human approver works normal hours. The old "Markets after the bell 17:00 ET" slot would need approval at 02:30 IST: move Markets to **pre-market**. If the audience is India-first, flip to a 06:00-08:00 IST production shift instead. |
| D2 | Edition names and days | Tech, Markets, Trading, Jobs; **Mon-Fri**. Optional Saturday "week in review" for Tech/Jobs only after week 3. No Markets/Trading on US *and* India market holidays (see edge cases). |
| D3 | Trading scope | **Information and education only**: what moved and why, flows, calendar, concepts. No buy/sell/hold, targets, levels or "setups" (SEBI RA rules; finfluencer rules). If the team wants calls, someone must register as a SEBI Research Analyst first. |
| D4 | Email platform | **Kit free plan** (10k subscribers, API on free) with one account and 4 tags; agents create **drafts** by API, the human schedules. beehiiv's post API is paid-only; Substack has no API. |
| D5 | Sending domain | Buy a domain; send from a subdomain (e.g. `mail.<domain>`); SPF + DKIM + DMARC (`p=none`) before the first send. |
| D6 | X/Twitter access | **Apify actor** for ~100 curated accounts (about $10-30/month) as default; a dedicated burner account with cookies only as fallback. Never a personal or brand account. |
| D7 | Claude usage | Run on a Claude Max plan (or API billing with a cap). Measure tokens per edition in week 1 before committing to 4 editions. |
| D8 | Market-data licence | Use exchange/official/attribution-allowed sources (FRED, CoinGecko with credit, exchange EOD facts in prose). Decide by day 30 whether to buy a redistribution licence if Trading continues. |
| D9 | AI disclosure | Footer line: *Produced with AI tools; reviewed and edited by our team.* (EU AI Act Art. 50 from Aug 2026; FTC deception rules.) |
| D10 | Brand name | "Twenty to One" hints at the many-to-one model; pick a final name before the public launch. |

---

## 3. The fixed format (every issue, every day)

Every edition uses the same skeleton so readers learn it and agents can't drift. Lengths are hard
limits checked by the Standards agent.

| Slot | Rule |
|---|---|
| Subject | <= 60 characters, 2-3 items, one emoji per item max |
| Preheader | <= 90 characters, a fourth hook |
| Masthead | date, issue number, "N-min read · N stories · no ads" |
| Number of the day | one figure + 1-2 sentences + **primary source credit** |
| Today | exactly 3 one-line teasers |
| **The big one** | 180-250 words: headline, **So what** (1-2 sentences), body, **What we know** ledger (confirmed / claimed / unclear) |
| **The split** or **Hype check** | 120-180 words; split = 2-3 sides of a real disagreement; hype check = a viral claim vs its fine print |
| Quick hits | 6 items, 40-60 words each, optional primary link and badges (Reported / Reports differ / Self-reported) |
| Edition modules | below |
| Morsels | 3 short, true, delightful facts |
| How we work | fixed text: checked numbers, confirmed vs claimed, no sponsors |
| Footer | unsubscribe, preferences, postal address, AI disclosure, disclaimers |

Target 1,000-1,300 words, 5-7 minute read, email under 102 KB.

**Edition modules:**

- **Tech/AI:** Try this today (one prompt/tool/technique) · For builders (5-7: releases, repos,
  papers, case studies with primary links) · Career signal (1 paragraph).
- **Markets (pre-market):** The close (indices, 10-year, bitcoin, from official/attribution-allowed
  data) · Movers (6, each with the reason) · The big picture (one theme, primary estimates) ·
  Term of the day · Calendar (today) / Week ahead (Mondays).
- **Trading (pre-market, information only):** Dashboard (US index futures, Nifty/Sensex, USD/INR,
  crude, gold, BTC: each with a data credit and timestamp) · What moved and why (5) · Flows and
  positioning (FII/DII daily, Cboe put/call, CFTC COT on Mondays) · Today's calendar (data
  releases, earnings) · Concept of the day (educational, no named stock) · Risk note. Disclaimer
  block on every issue. No calls, no targets, no levels.
- **Jobs & Careers:** Hiring pulse (3-4 items: hiring/layoffs/pay news) · Fresh roles (10 verified
  listings from employer job boards: company, role, location/remote, posted date, official apply
  link) · Skill in demand · Pay datapoint (attributed) · Career move of the day (tactic) ·
  Interview question of the day · standing line: *We never charge. Never pay to apply.*

---

## 4. Data: what we collect, how, and how fresh

**Freshness rule:** a news item is eligible only if its **original publish time** is within the 24
hours before the edition cutoff. Each item carries `published_at` from the source (email Date
header, feed pubDate, API timestamp). Unknown publish time -> not eligible as news. Job listings:
posted within 72 hours, shown with their posted date (daily volume is too thin for 24h).

**Collection is scripted** (one script per channel, writing `items.jsonl` with
`id, channel, source, url, published_at, title, body, engagement, collected_at`), stored in
Supabase `documents` (channel `rss|web|api`) so the seen-store and dedupe cover everything.

| Channel | Method | Auth / cost | Risk |
|---|---|---|---|
| Newsletters (all 4) | existing `pipeline.cli ingest` (Gmail read-only) | local machine only | token expiry (publish the OAuth app) |
| Hacker News | Algolia API, points filter | none | low |
| GitHub trending | daily page + `gh api` enrichment | none/token | low |
| News | Google News RSS `when:1d`, company newsrooms, wire RSS (GlobeNewswire, PR Newswire, Business Wire) | none | low-med |
| Filings and macro | SEC EDGAR Atom (8-K, Form 4, S-1), FRED, BLS/Fed/Treasury calendars, RBI/MoSPI, NSE/BSE reports (read, don't scrape) | User-Agent with contact email | low |
| YouTube | Data API v3 uploads playlists (1 unit per 50 videos) -> filter (no Shorts, >3 min, keyword match, top N by views/hour) -> captions via yt-dlp (local IP) -> Whisper (Groq or local) if no captions | free API key | med (IP blocks on cloud) |
| X/Twitter | Apify actor over curated account lists; fallback twitter-cli with a burner account, 1-2 runs/day, local IP | Apify key / burner cookies | med / high |
| Reddit | subreddit `.rss` **until it closes (reported 13 Nov 2026)**; afterwards Exa/Google `site:reddit.com` search | none | high (ending) |
| Telegram | public `t.me/s/<channel>` pages or self-hosted RSSHub | none | low |
| Bluesky | public API / profile RSS | none | low |
| Podcasts | RSS + `podcast:transcript`, else Whisper | none | low |
| Web articles (primary sources) | Jina Reader `r.jina.ai/<url>`; Exa search through Agent-Reach (mcporter) | none / free tier | low |
| Jobs | Greenhouse/Lever/Ashby public boards for a target-company list, Adzuna (credit required), RemoteOK (link + credit), USAJobs, HN "Who is hiring" (monthly), JobSpy for discovery only | free keys | med (fake jobs) |
| LinkedIn | **not automated** (ToS, lawsuits); a human may paste a public post by hand | n/a | high |

**Source mix per edition:**
- **Tech:** inbox, HN, GitHub trending, lab/company blogs and arXiv RSS, Google News, YouTube
  (curated channels), X (curated AI/dev accounts), Bluesky, Product Hunt RSS.
- **Markets:** inbox, EDGAR, Fed/BLS/Treasury, company IR and wires, Google News, FRED, X (curated
  FinTwit via Apify), podcasts.
- **Trading:** inbox (new subscriptions needed), exchange/official data, Cboe/CFTC/AAII, NSE FII/DII,
  EDGAR Form 4, YouTube (filtered), Telegram (verified channels only, pump filter), X via Apify.
- **Jobs:** inbox (new subscriptions needed), employer job boards, Adzuna/RemoteOK/USAJobs, BLS/JOLTS,
  PLFS/EPFO (India), layoffs.fyi (credit), Google News for hiring/layoffs.

**New subscriptions to add in week 0** (to `notifyy1008+trading@` / `+jobs@`, with Gmail filters
and `sources.yaml` entries): Trading: Trendlyne technical newsletter, Zerodha Daily Brief,
AAII weekly, Stocktwits Daily Rip, Cboe commentary. Jobs: Rise Jobs, Remote Jobs from India,
Technical.ly This Week in Jobs, The Assist, Consulo. *(Check each is free and still active.)*

**Handling high-volume channels (hundreds of videos/posts a day):** metadata filter first (allowlist,
duration, keywords, engagement velocity), then a per-edition cap (e.g. 20 transcripts, 200 posts),
then a cheap model summarises each into one card, then clustering. Never feed raw volume to the writer.

---

## 5. The agent team

All agents live in `.claude/agents/*.md` (frontmatter: `name`, `description`, `tools`, `model`,
`maxTurns`). The day is driven by a skill, `/produce-issue <edition> <date>`. Agents hand off through
files in `runs/<date>/<edition>/` (gitignored), so any step can be re-run or resumed.

| # | Agent | Model | Tools | Input -> Output | Done when |
|---|---|---|---|---|---|
| 1 | **Chief Editor** (orchestrator) | Sonnet | Read, Write, Bash (scripts only), subagents | edition config -> `00_manifest.json`, `run_log.md` | every stage has an output or a logged failure; never writes copy |
| 2 | **Collectors** (inbox, feeds, social, data desk, jobs desk) | scripts + Haiku | Bash (collector scripts only) | sources -> `10_raw/*.jsonl` | counts per source logged; dead sources flagged |
| 3 | **Triage Editor** | Haiku | Read, Write | raw -> `20_candidates.json` (top 25 clusters) | stale/duplicate/sponsored/promo removed; injection scan done; clusters scored |
| 4 | **Researcher** | Sonnet | Read, Write, Jina/Exa (primary sources only) | candidates -> `30_cards.json` | every fact has a verbatim evidence quote + source id/url; status confirmed / claimed / unclear; conflicts recorded |
| 5 | **Market Analyst** (Markets/Trading) | Sonnet | Read, Write | cards + data snapshot -> bull/bear material, risk notes | no advice language; numbers only from the data snapshot |
| 6 | **Writer** (one persona per edition) | Opus or Sonnet | Read, Write | cards -> `40_issue.json` | passes the schema; every claim maps to a card id; no new facts |
| 7 | **Fact-Checker** (adversarial, independent) | Opus or Sonnet | Read, Write, URL check (HTTP status only) | issue + cards + raw -> `50_factcheck.json` | each claim: decomposed, checked against evidence, verdict; every link in the collected set and returns 200 |
| 8 | **Standards Editor** | Sonnet + code checks | Read, Bash (tests) | issue -> `55_standards.json` | rendering tests pass (no source names, size, structure); word budgets; quotes <= 15 words, max 1 per story; no advice; disclaimers; freshness; no repeat of a story run in the last 7 days unless there's a real update |
| 9 | **Publisher** | Haiku | render script, Kit API (drafts only) | approved issue -> `60_render/*`, Kit draft, test email | draft exists; test email sent to the team; **schedule only after `70_approval.json`** |
| — | **Human editor on duty** | — | — | reads the draft + fact-check report | signs `70_approval.json` (approve / edit / kill) |
| — | **Weekly Analyst** | Sonnet | Read, Kit stats | metrics, replies, source health -> `weekly/<date>.md` | recommends source/format changes |

**Writer personas:** Tech: sharp, builder-first, skeptical of hype. Markets: calm, precise,
numbers-led. Trading: data-first desk voice, no hype, no calls. Jobs: practical coach, warm,
anti-scam. Each persona file holds a style sheet plus the two approved samples as exemplars.

**The relay and the fix loop (per edition):**

```
collect -> triage -> research -> [analyst] -> write -> fact-check --FAIL--> writer fixes (max 2)
                                                     |                     |
                                                   PASS            still failing -> drop story,
                                                     v             pull next reserve card
                                               standards --FAIL--> same loop
                                                     | PASS
                                                     v
                                     publisher: render + Kit draft + test email
                                                     v
                                     human approval --> schedule   (kill switch: skip the day)
```

**Minimum viable issue:** if fewer than 1 big story + 4 quick hits survive, ship a clearly marked
**short edition**, or skip with a one-line note. Never pad with stale or unverified items.

**Hard guardrails:**
- Writer and fact-checker have **no** web or publish tools.
- A `PreToolUse` hook denies any Kit schedule/send call unless `70_approval.json` exists and its
  hash matches the rendered email.
- All scraped text is **data, never instructions**: the Triage Editor flags injection attempts, and
  no agent with tools reads raw scraped text except Triage and Research.

---

## 6. Daily run sheet (recommended: US-morning send, IST production)

| IST | Step |
|---|---|
| 12:30 | Collection cron on the local machine (Gmail ingest + all collectors). Cutoff = 12:30 IST (03:00 ET) |
| 12:45-13:30 | Triage + research, 4 editions in parallel |
| 13:30-14:15 | Writing + fact-check + standards loops |
| 14:15-15:30 | Human review: ~15 min per edition; approve or edit |
| 15:30 | Publisher schedules in Kit |
| 16:00-17:30 | Sends: Markets 06:30 ET · Trading 07:00 ET · Tech 07:30 ET · Jobs 08:00 ET |
| Friday | Weekly analyst report; source health; prompt/style changelog |

Indian-market Trading content (Nifty/Sensex close, FII/DII) comes from the previous Indian session,
which closes before the cutoff. If the team chooses an India-first audience, move the shift to 05:00-08:00 IST.

---

## 7. Edge cases and gaps, and how each is handled

**Data and freshness**

| Case | Handling |
|---|---|
| Weekend/holiday thin inbox (3-6 issues) | Weekday-only editions; on thin days the social/feed share rises; short-edition rule |
| Newsletters recap old news as "new" | Eligibility uses the original publish time from the primary source when available; seen-store check against the last 14 days |
| Unknown publish time (images, undated pages) | Not eligible as news |
| Same story, conflicting numbers | Ledger "Unclear" or "Reports differ" badge; never pick one silently |
| Paywalled preview / headline-only item | Tagged `headline_only`; may appear only as a one-line hit with a primary link, never summarised beyond what is shown |
| Numbers inside images | Never used (unreadable, unverifiable) |
| A source stops sending / "are you still there?" emails | Daily source-health report; engagement checks are surfaced to a human, never auto-clicked |
| Gmail OAuth token expires every 7 days (testing mode) | Publish the Google OAuth app before the pilot; Monday token check in the run sheet |
| Laptop asleep or offline at cron time | Run on an always-on machine; the run sheet can be started manually; collectors are idempotent |
| Supabase free tier pauses after inactivity / 500 MB cap | Daily ingest keeps it active; `db status` shows size; prune `blocks` if needed |
| Reddit API/RSS shutdown (reported 31 Oct / 13 Nov) | Treat Reddit as optional from day 1; Exa/Google `site:reddit.com` fallback |
| X endpoints change, Apify actor breaks | Two methods (Apify, burner fallback); edition never depends on X alone |
| YouTube blocks transcript fetches | Fetch from the local residential IP; Whisper fallback; cap volume |
| Cookie/session expiry | Weekly re-export in the run sheet; `agent-reach doctor` health check |
| US vs India market holidays differ | Holiday calendar file; Trading shows only the open market's data and says which is closed |
| Market data licensing | Official/attribution-allowed data only; prose facts with a credit; no big price tables from personal-licence APIs |

**Content quality and accuracy**

| Case | Handling |
|---|---|
| Hallucinated fact, number, name or link | Writer cites card ids; the fact-checker verifies every claim against verbatim evidence; links must be in the collected set and return 200 |
| Vendor claims presented as fact | "Self-reported" badge; ledger "Claimed" |
| Viral misleading stats | Hype-check slot; the fine print goes in the ledger |
| Bots, engagement bait, AI slop on social | Allowlists, engagement thresholds, corroboration across source types required for social-only stories |
| Pump-and-dump content (Trading Telegram/X) | Never feature small caps from social alone; flag and drop |
| Fake job listings | Employer-board links only; apply domain must match the company; drop fee/Telegram/WhatsApp/crypto/"tasks" posts; standing "never pay to apply" line |
| Same story in two editions | Cross-edition dedupe at triage; one edition owns it, the other may link a different angle |
| Repeating yesterday's story | 7-day story memory; repeats only as "Update:" with new facts |
| Breaking news after cutoff | Not chased that day; it goes into tomorrow's window |
| Corrections after send | Correction box at the top of the next issue; corrections log |
| Voice drift and repetitive structure | Persona style sheets + exemplars; weekly review of 5 random issues |
| Length overflow / Gmail clipping | Word budgets + the renderer's 102 KB check |

**Legal and policy**

| Case | Handling |
|---|---|
| Revealing source newsletters | Rendering test (rule 11); primary-source credit only |
| Re-using another newsletter's analysis or scoop | Not allowed even unattributed; facts only, with a primary source |
| Copyright (quotes, images, transcripts) | Paraphrase; quotes <= 15 words, max 1 per story; no third-party images or charts; no transcript excerpts |
| Investment advice (SEC/SEBI) | Information-only house rules in the Writer and Standards prompts; disclaimer; no personalised replies; staff trading blackout on names covered; no broker or affiliate money |
| Defamation / unverified allegations | Allegations only from named primary reporting, marked "alleged" / "reported"; Standards flags people-related negative claims for the human |
| Spam law and deliverability | Double opt-in, 18+ checkbox, privacy notice, postal address, one-click unsubscribe, SPF/DKIM/DMARC, warm-up (start with the team and friends, grow gradually) |
| AI disclosure | Footer line plus a real human review of every issue |

**Operations and security**

| Case | Handling |
|---|---|
| Claude usage limits hit mid-run | Stagger editions; Haiku for volume work; fall back to producing 2 editions; measure in week 1 |
| Run crashes midway | File-based stages; resume from the last completed stage |
| Two people run the same edition | Run lock (Supabase advisory lock pattern) + "already scheduled today" check |
| Approver unavailable | Rota with a backup; no approval by 16:00 IST means no send that day (never auto-send) |
| Prompt injection inside emails/web pages | Content treated as data; injection scan at triage; least-privilege tools; publish hook |
| Secrets (cookies, API keys, DB URL) | Only in `.env` / tool configs on the collection machine; never in chat, git or issue files; burner accounts for social |
| Accidental send of a bad issue | Kill switch; correction policy; publisher only ever creates drafts |

---

## 8. Open-source pieces to adopt

| Repo | What we take | License |
|---|---|---|
| zarazhangrui/follow-builders | The architecture: scripts fetch, the agent only remixes; strict grounding rules (only feed content, every item keeps its URL, names/titles from data fields) | ideas only (no LICENSE file) |
| draco-agent/tech-news-digest | Scoring: source priority, +5 per extra source type confirming a story, freshness, engagement tiers | MIT |
| Thysrael/Horizon | One **profile** per edition (rubric, threshold, per-category caps) over one shared item pool | MIT |
| assafelovic/gpt-researcher (multi_agents) | Editorial roles and the bounded review/revise loop with a human in the loop | Apache-2.0 |
| druce/AInewsbot | classify -> seen-filter -> summarise -> cluster -> write -> polish chain | MIT |
| duanyytop/agents-radar | Ops: cron, concurrency guard, dated run folders, review surface per issue | MIT |
| Libr-AI/OpenFactVerification (Loki) | The 5-step claim check (decompose -> check-worthiness -> query -> evidence -> verdict) as the fact-checker prompt | MIT (unmaintained; copy the method, not the code) |
| TauricResearch/TradingAgents | Bull/bear debate + risk gate for Markets/Trading | Apache-2.0 |
| speedyapply/JobSpy | Job discovery (verify on employer boards before listing) | MIT |
| DIYgod/RSSHub | Self-hosted RSS for Telegram, Bluesky, newsrooms | AGPL (run as a separate service) |
| Panniantong/Agent-Reach | yt-dlp, Jina, Exa recipes and `doctor` health checks; X/Reddit cookie routes only with burner accounts | MIT |
| VoltAgent/awesome-claude-code-subagents | Starting points for agent files (research-analyst, content-quality-editor) | MIT |

---

## 9. Rollout

| When | What |
|---|---|
| **Week 0** (5 working days) | Decide D1-D10 · domain + Kit + DNS · publish the Gmail OAuth app · subscribe to Trading/Jobs newsletters · write collector scripts · write agent files, persona style sheets and the `/produce-issue` skill · extend the schema (jobs, trading dashboard) · approval hook |
| **Week 1** | Internal dry runs for **Tech + Markets** only (sent to the team): measure tokens, time and errors caught |
| **Week 2** | Add Trading + Jobs dry runs; soft launch Tech + Markets to friends (warm-up) |
| **Weeks 3-8** | Public, 4 editions on weekdays; Friday review; tune sources and prompts |
| **Day 30 and day 60** | Go/no-go: which steps should become pipeline code first (usually collection, dedupe and rendering, which are already built) |

**Pilot success metrics:** on-time sends >= 95% · zero uncorrected factual errors · human review
<= 15 min per issue · open rate >= 40% · unsubscribes < 0.5% per issue · spam complaints < 0.1% ·
fact-checker catch rate tracked weekly.

**Rough running cost per month:** Claude Max plan (or API usage with a cap) · Apify for X ~$10-30 ·
YouTube Data API free · Groq Whisper free tier or local Whisper · Kit free · domain ~$1.

---

## 10. Credentials: how session cookies and keys are handled

The collectors need some logins (X via a **burner** account, optional Reddit, a YouTube API key,
an Apify key, a Groq key). **Do not paste them into chat.** The person who owns each account
sets it on the collection machine:

```bash
agent-reach configure twitter-cookies   # burner account auth_token + ct0, from the Cookie-Editor export
agent-reach doctor                      # shows which channels are active
```

API keys go in the git-ignored `.env` (`YOUTUBE_API_KEY`, `APIFY_TOKEN`, `GROQ_API_KEY`,
`EXA_API_KEY`). Claude runs the tools; it never needs to see the values.
