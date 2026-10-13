# Newsroom pilot plan v2: 3 daily newsletters for Indian readers, made by Claude Code agents

**Version 2 (2026-10-13).** Rewritten to fix all 50 gaps in `NEWSROOM_PLAN_REVIEW.md`; gap IDs are
shown in brackets, e.g. [T1]. The appendix maps every gap to its fix.

**Decisions taken (owner, 2026-10-13):**
- **Audience:** Indian readers who follow global tech, markets and jobs. Issues land **07:45-08:30 IST**,
  before Indian markets open at 09:15. [P1, T1]
- **Editions:** three, Monday to Friday: **Tech**, **Markets** (with a trading section; the separate
  Trading edition is merged in) and **Jobs**. [C3]
- **Pipeline build stays paused.** For 60 days, Claude Code agents plus a human editor produce the
  issues. Reused: Gmail ingest -> Supabase, the issue schema and renderer, the "never name a source"
  test, the design samples.

---

## 0. The plan on one page

- **Why this timing works:** our source newsletters land 15:00-18:00 IST and the US close lands
  around 01:40 IST (02:40 after 1 Nov). A **05:00 IST cutoff** therefore contains the *entire*
  previous US day, and we reach Indian readers first, with a verified, India-angled summary. [T1]
- **Schedule is anchored in IST**, which has no daylight saving. The 1 Nov US change only shifts
  when US data arrives, and it still arrives before 05:00. [T2]
- **One promise per edition** (section 2), each with a "Why it matters in India" line on the big story. [C4]
- **Scripts collect; agents only judge and write.** No AI in collection: all summarising happens in
  Triage. [B5]
- **Evidence tiers** decide what we may say about paywalled or single-source news. Newsletter scoops
  and opinions are never used. [C1]
- **A person approves every issue** using a signed checklist. Only the publish script holds the
  email-platform key, and it refuses to send without a matching approval. [L7, O6]
- **Start small:** week 0 builds **Tech + Markets** only; Jobs follows after its sample issue and
  company list. The trading section goes public only after a SEBI review. [B1, L3, N4]
- **Keep-alive first:** a daily heartbeat runs from today, so Gmail and Supabase never silently
  die again. [N1]

---

## 1. Fix-now items (before any build work)

| # | Action | Owner | Gap |
|---|---|---|---|
| 1 | Restore the Supabase project (dashboard -> Restore) | Owner | N1 |
| 2 | Re-authenticate Gmail **on the always-on machine**: `cd tools/google-skill && npx tsx skills/gmail/scripts/gmail.ts auth` | Owner | N1 |
| 3 | Google Cloud Console -> OAuth consent screen -> publishing status **In production**. **Do not** submit for verification (that triggers a weeks-long security review). The unverified-app warning and 100-user cap are fine for one inbox. Confirm the token survives past day 7. | Owner | O1 |
| 4 | Turn on the **daily heartbeat** (section 8): ingest + `doctor` at 04:30 IST every day including weekends, with an alert on failure. This also stops Supabase pausing after 7 idle days. | Claude + Ops | N1 |

---

## 2. Editions, audience and promise

| | **Tech** | **Markets** | **Jobs** |
|---|---|---|---|
| Promise | The global tech and AI news that matters to Indian builders, verified and explained before 8 a.m. | What happened overnight in the US and global markets, and what it means for India's open. No tips, just clarity. | Fresh, verified roles and the hiring signals that matter for Indian professionals. Never pay to apply. |
| Reader | Developers, founders, product people | Investors, finance professionals, curious savers | Job seekers and early-career professionals in India, plus remote-friendly roles |
| Send (IST) | 08:00 | 07:45 | 08:30 |
| Window | Since the previous cutoff: 24h; **Monday: since Friday's cutoff (72h), labelled "Since Friday"** [T5] | same | Listings posted within 72h (owner-signed exception, shown with posted date) [T6] |

**Before launch:** test each one-line promise with 10 target readers; adjust. [C4]
**Brand:** pick the final name before any public send; "Twenty to One" hints at the many-to-one
model. The name becomes a renderer setting, and the newsletter-centric schema fields (`roster`,
`issues_read`, `ads_removed`) become optional and internal. [P5]

---

## 3. Format: one skeleton per edition

All three share a masthead (date, issue number, read time, story count), **Today** (exactly 3
teasers), **How we work** (method only), and a footer (address, unsubscribe, AI disclosure,
disclaimers). Every time in copy carries a zone: "02:30 IST (4:00 PM ET)". [C8]

**Tech** (1,000-1,200 words)
| Slot | Rule |
|---|---|
| Number of the day | one figure, 1-2 sentences, primary-source credit |
| The big one | 180-250 words: headline, So what, **Why it matters in India** (1 sentence), body, What we know ledger |
| The split *or* Hype check | 120-180 words |
| Quick hits | 6 x 40-60 words, badges (Reported / Reports differ / Self-reported) |
| For builders | 5-7 releases, repos, papers, case studies with primary links |
| Try this today | one prompt, tool or technique |
| Morsels | 3 |

**Markets** (1,000-1,300 words; information only, never advice) [L3]
| Slot | Rule |
|---|---|
| The close | US close, India's previous close, USD/INR (RBI reference rate), crude, gold, bitcoin: **only fields cleared in the licence table** (section 5), each with "as of" time [L5, T4] |
| The big one | as Tech, with Why it matters in India |
| What moved | 6 movers (US + India), each with its reason; large caps only, never small caps from social alone |
| The split *or* Hype check | 120-180 words |
| **Trading section** | Flows (FII/DII provisional), positioning (Cboe put/call; CFTC on Mondays, "as of Friday"), today's calendar in IST (Indian + US releases, earnings), concept of the day (no named stock) |
| Quick hits | 5 |
| Disclaimer | fixed text, every issue |

**Jobs** (800-1,100 words) [C5]
| Slot | Rule |
|---|---|
| Hiring pulse | 3-4 hiring, layoff and pay stories (news rules apply) |
| Fresh roles | 10 listings: company, role, city or remote, posted date, **official apply link on the employer's own job board** |
| Skill in demand | 1 short item with evidence |
| Pay datapoint | 1, attributed |
| Career move | 1 practical tactic |
| Standing line | "We never charge. Never pay to apply." |

Hard limits checked in code: subject <= 60 characters, preheader <= 90, email under 102 KB,
word budgets per slot.

---

## 4. Evidence and freshness rules

**Evidence tiers** [C1]
| Tier | What it is | What we may write |
|---|---|---|
| A | Primary source we can read in full: company post, filing, government or exchange release, open article, official data | Full use, with the primary link |
| B | A named outlet's paywalled report that we see only as a headline or summary | Headline-level fact only, credited "Reuters reported", with no detail beyond what's visible |
| C | The same fact reported by 2+ independent outlets | State it as reported fact, linking the best primary |
| Never | A source newsletter's own scoop, analysis or opinion; anything from an outlet in our newsletter registry that we can't confirm elsewhere; transcript-only numbers [N3] | Not used |

**Freshness** [T5, T6]
- An item's age is its **primary source's** publish time. A newsletter recap inherits the age of what
  it recaps; if that can't be established, it isn't news.
- Scheduled datasets are exempt but always show "as of": CFTC (Friday), AAII (weekly), HN Who's
  Hiring (monthly), PLFS/EPFO (monthly), FII/DII (previous session).
- Google News links are decoded to the real article URL in the collector. [C1]

**Links** [C2]
- A script (not an agent) resolves every link: follows redirects, stores the final canonical URL
  and status, and rejects soft-404s.
- Accept 2xx/3xx. A known bot-blocking domain (SEC, NSE, major paywalls) passes if its cached
  evidence quote exists.
- Tracking and subscription links are never resolved.

---

## 5. Data sources and the licence table

**Collection is scripted per channel**, writing items with
`id, channel, source, url, published_at, title, body, engagement, collected_at` into Supabase, so
dedupe and story memory cover everything.

| Channel | Method | Phase | ToS risk |
|---|---|---|---|
| Newsletters | Gmail ingest (read-only, local machine) | 0a | med (personal-use terms: facts only) [L4] |
| News | Google News RSS (links decoded), company newsrooms, wire RSS, PIB/RBI/SEBI press releases | 0a | low-med |
| Filings and macro | SEC EDGAR, FRED, BLS calendars, RBI, MoSPI, NSE/BSE published reports (read, never scraped) | 0a | low |
| Hacker News, GitHub trending, arXiv, lab blogs | public APIs and RSS | 0a | low |
| YouTube | Data API v3 uploads lists -> filter -> local captions; numbers from transcripts never used alone [N3] | 1 | med (yt-dlp vs ToS) [L4] |
| X | Apify over curated lists; burner-account fallback | 1 | high [L4] |
| Reddit | RSS while it lasts (closure reported for Oct-Nov 2026, unverified [B6]); afterwards none | 1 | high |
| Jobs | Greenhouse, Lever and Ashby boards for the company list; Adzuna (credit); RemoteOK (credit); USAJobs | 0b | low-med |
| LinkedIn | never automated | - | - |

**ToS register:** every source in `sources.yaml` gets a `tos_risk` and a note; the owner signs off
the register once. [L4]

**Licence table (Markets "The close")** [L5]
| Field | Source we may use | Status |
|---|---|---|
| USD/INR | RBI reference rate (public) | OK |
| Bitcoin | CoinGecko, with attribution | OK |
| US 10-year yield | US Treasury daily rates (public) | OK |
| S&P 500, Nasdaq, Dow, Nifty, Sensex | single closing values and % changes **in prose**, as widely reported facts, corroborated by 2 sources; no tables | **Needs legal confirmation** |
| Crude, gold | single reported values in prose, corroborated | **Needs legal confirmation** |
| Index futures, intraday quotes | none | Dropped |

New subscriptions for Jobs (phase 0b, to `notifyy1008+jobs@`, verify each is free): Indian
hiring/careers newsletters for **signals only**; their curated listings are never reused, and
every role is verified on the employer's own board. [C6] Trendlyne-style technical-call newsletters
are not used. [C6]

**Jobs company list** [C7]: 100 companies hiring in India or remote-friendly from India, with their
public board URLs, built in phase 0b. At publish time a script re-checks every listing is still
open; closed ones are dropped. Filters: India location or "remote, India eligible".

---

## 6. The agent team

**Orchestration** [O3]: the `/produce-issue <edition> <date>` skill **is** the orchestrator. It runs
in the main session (one headless `claude -p` process per edition) and calls the subagents below.
Subagents never call other subagents.

| Agent (`.claude/agents/`) | Model | Allowed tools | Output |
|---|---|---|---|
| Triage Editor | Haiku | Read, Write (run folder only) | dedupe, freshness, injection scan, per-item summary, clusters, scores |
| Researcher | Sonnet | Read, Write, `fetch_cited.py` (only URLs already in the candidates) | story cards with evidence tier and verbatim evidence |
| Market Analyst | Sonnet | Read, Write | bull/bear material, risk notes (Markets only) |
| Writer | Sonnet (Opus for the big story if the budget allows) | Read, Write | issue JSON in the edition's voice |
| Fact-Checker | Sonnet or Opus | Read, Write (**no web**; uses link-check results) | claim-by-claim verdicts |
| Standards Editor | Sonnet + code tests | Read, `run_checks.py` | rules report |
| Weekly Analyst | Sonnet | Read | Friday report |

**Scripts, not agents:** collectors, `linkcheck.py`, `render.py`, `publish.py` (the only holder of
the email-platform key), `heartbeat.py`. That makes **6 editorial agents + 1 weekly agent + scripts**. [B5]

**The relay per edition:**
collect -> triage -> research -> (analyst) -> write -> fact-check -> standards -> render ->
human approval -> publish.
- Fact-check or standards failure: the writer fixes it, at most 2 rounds. Still failing: the story
  is dropped and the next reserve card goes in.
- **Minimum issue:** 1 big story + 4 hits (Jobs: pulse + 6 roles). Below that, a marked short
  edition or a skip notice.
- **Per-stage timeouts** fall back to the short edition rather than missing the send. [T7]

**Story memory** [N2]: `publish.py` writes every sent story (headline, url_key, entities, edition,
date) to Supabase. Triage drops repeats from the last 7 days unless there is a real update.

**Security** [O5, O6]:
- Agents run under a **permission allowlist** in `.claude/settings.json`. `.env`, the Gmail token
  and the cookie stores are **deny-read**. Bash is limited to the named scripts.
- Scripts load secrets themselves; agents never see them.
- Scraped text is data, never instructions. Triage flags injection attempts, and an injection
  test set runs on every prompt change.
- `publish.py` refuses unless `approval.json` holds the SHA-256 of the exact rendered email and
  the approver's checklist. **Edits happen in the issue JSON, then re-render and re-approve.
  Never edit in the email platform's UI.**
- The newsroom runs in its own folder under a separate OS user, away from other projects in `D:\Work`.

---

## 7. Daily run sheet (IST, Monday-Friday)

| IST | Step | Owner |
|---|---|---|
| 04:30 | Heartbeat: Gmail token, Supabase, disk, platform API reachable; alert if red | script |
| 05:00 | **Cutoff.** Collection: Gmail ingest + all collectors; link check | scripts |
| 05:15-06:15 | Triage -> research -> write -> fact-check -> standards, 3 editions in parallel, per-stage timeouts | agents |
| 06:15 | Rendered drafts + test emails + fact-check reports ready | `publish.py` (draft only) |
| 06:15-07:30 | **Human review**: approver signs the checklist per issue (target <= 20 min each) | approver |
| 07:30 | Publish script schedules approved issues; **no approval by 07:30 = that edition skips today** | script |
| 07:45 / 08:00 / 08:30 | Markets / Tech / Jobs land | platform |
| 09:00 | Approver skims replies; flags corrections | approver |
| Friday 17:00 | Weekly review: metrics, approver edit diffs, golden-set results, prompt-change PR | team |

**US daylight saving (1 Nov)** [T2]: IST anchors don't move. Checklist: the US close arrives at
about 02:40 IST instead of 01:40; US data releases shift by an hour in the calendar; update the
"(ET)" labels in copy.

**Holidays** [C8]: committed 2026 files for NSE/BSE, NYSE and Indian public holidays, plus a team
leave calendar.
- On an NSE holiday, Markets runs global-only with a note.
- On days with no approver, the 2-edition minimum mode applies.

---

## 8. Operations

| Area | Rule |
|---|---|
| Heartbeat [N1] | 04:30 IST daily, weekends included: Gmail token check, ingest (keeps Supabase active), `doctor`, Supabase size, email-platform API reachable. Alert by email to the owner and ops. |
| Always-on machine [O4] | Named machine and owner. UPS, auto-restart and auto-login to the newsroom user; scheduled tasks re-arm on boot. A written runbook lets a second machine run everything except Gmail. |
| Claude usage [O2] | **API billing with a hard monthly spend limit** (Console) and a per-edition token budget, logged per run. Week 1 measures the real numbers. If the limit hits, Jobs drops first, then Tech. Avoid driving a team's cron from one person's subscription. |
| Backups [O7] | Nightly `pg_dump` to the machine (7 days kept) plus a weekly copy off-machine. Size alarm at 70% of 500 MB. Transcripts are stored as files, not in the database. |
| Audit [O8] | Each sent issue's JSON, fact-check report, standards report and approval are archived to Supabase. Scraped personal data is kept 90 days. |
| Corrections [O9] | **S1** material error (a wrong market number, an unfair claim about a person): correction email within 2 hours, approved by the owner. **S2**: correction box in the next issue. **S3** typo: log only. |
| Versioning [B3] | Each run's manifest records the git SHA of `.claude/`. Prompt changes ship only as PRs, reviewed Friday. Approver edits are saved as diffs and feed the next week's changes. |
| Evaluation [B2] | Golden set: 20 issues with seeded errors (wrong number, invented link, source-name leak, advice wording, stale story, duplicate) + 10 injection samples. It runs on every prompt change; the fact-checker must catch at least 95% of errors. |

---

## 9. Email platform, deliverability and the reader experience

**Day-1 spike** (Kit free plan, the leading option) [O10, N5]: prove by API that we can create a
draft from our HTML, send a test, and schedule it. Also check that our HTML survives intact,
what footer and branding Kit adds on the free plan, and how stats come back.
- **Per-edition opt-out:** Kit's unsubscribe is account-wide. Prove a preferences form that toggles
  edition tags, or run one Kit account per edition. If neither works, switch provider before the
  dry runs (fallback: Buttondown, which has an API on all plans).
- Send our real HTML to Gmail (web and Android), Outlook desktop and iOS Mail, in light and dark mode. [P6]

**Merge tags** [P4]
- Unsubscribe and address come from the platform's own footer tags.
- `{{web_url}}` only if the platform hosts a web version; otherwise it's removed.
- The feedback buttons are replaced by "Hit reply and tell us".
- The renderer gets a platform-specific tag map.

**Deliverability** [O11, D5]
- Own domain; send from a subdomain with SPF, DKIM and DMARC (`p=none`, `rua=` to an ops inbox).
- Ramp: week 1 the team (10), week 2 friends (up to 100), week 3 up to 300, then organic.
- Weekly seed tests (Gmail, Outlook, Yahoo); spam complaints over 0.1% pause growth.

**Replies** [P4]: the reply-to inbox is read by the approver each morning. Requests for personal
investment advice get a fixed polite decline and never an answer.

---

## 10. Growth and measurement

**Growth owner** (named) runs the subscriber engine from week 2. [P2]
- **Signup:** one landing page per edition (Kit landing pages) with double opt-in, an 18+
  checkbox and the privacy notice.
- **Channels for Indian readers:** the team's own LinkedIn and X posts (a daily "number of the day"
  card); relevant communities (developer, investing and careers groups, following their rules);
  college and alumni networks; WhatsApp and Telegram channels with a daily teaser; cross-promotion
  later.
- **Targets (hypotheses to test):** 300 subscribers across editions by day 30, 1,000 by day 60.
  Each channel is tracked with its own signup link.

**Metrics that can decide** [P3]
| Kind | Metric |
|---|---|
| Reader value | Unique click rate per delivered email; 4-week retention (still subscribed and clicking); replies per 100 readers; a one-question monthly survey |
| Growth | New subscribers per week per channel |
| Operations | On-time sends; human minutes per issue; Claude cost per issue; factual errors published (target 0); golden-set catch rate |

Open rates are recorded but not used for decisions (Apple Mail inflates them).

**Continue / kill rules** (written now, applied at day 30 and day 60)
- **An edition continues** if click rate >= 8%, 4-week retention >= 60%, human review <= 25 min,
  and zero S1 errors in the last 2 weeks.
- **An edition is cut** if click rate < 3% for two consecutive weeks, or human review > 40 min.
- **Pipeline build starts** (automating the proven steps first: collection, dedupe, render, link
  check) if at least one edition passes at day 30 and manual effort exceeds 1 hour a day.

---

## 11. Legal and compliance

**One legal consult before the public launch** (book in week 0) [L1, L2, L3]:
- India's IT Rules 2021 for digital news publishers: MIB disclosure, grievance officer, code of ethics.
- DPDP Act: notice and consent; the privacy notice text.
- SEBI: review of a sample Markets issue including the trading section.
- The licence table and the ToS register.

**Fixed items:**
- **Entity and address** [L6]: decide the publishing entity or the individual sender; get a PO box
  or virtual office address; set a reply-to and a grievance contact.
- **Privacy notice** [L2]: the platform as processor, open and click tracking, retention, deletion
  requests.
- **Markets** [L3]: information only. No buy, sell or hold, no targets, levels or setups, no named
  stock in "concept of the day", no personal replies, no broker or affiliate money. Staff don't
  trade names covered within 24h. Disclaimer on every issue.
- **The trading section stays internal until the SEBI review clears it.**
- **AI disclosure** [L7]: "Produced with AI tools; reviewed and edited by our team." The approver
  signs a checklist per issue (facts spot-checked, links opened, tone, legal flags), with time spent
  logged. [B6: the EU AI Act Art. 50 editorial-review exemption is worth confirming in the consult.]
- **Copyright:** paraphrase; quotes under 15 words, one per story; no third-party images, charts or
  transcript excerpts; primary-source links.
- **Rule 11:** no source-newsletter names, links or coverage counts, enforced by the render test.

---

## 12. People (RACI) [B4]

| Area | Responsible | Accountable | Consulted |
|---|---|---|---|
| Daily approval (primary and backup per weekday) | named rota | Owner | - |
| Always-on machine, tokens, heartbeat alerts | Ops | Owner | - |
| Sources, ToS register, company list | Source curator | Owner | Legal |
| Growth and community | Growth owner | Owner | - |
| Legal and compliance | Legal contact | Owner | external counsel |
| Prompts and agent files (Friday PRs) | Editor | Owner | approvers |

**Minimum mode:** when short-staffed, publish Markets + Tech only. With no approver, nothing is sent.

---

## 13. Rollout

| Phase | Dates (from start) | Scope |
|---|---|---|
| **Now** | before day 1 | Fix-now items 1-4 (section 1) |
| **0a (engineering, 5 days)** | days 1-5 | Tech + Markets collectors (phase 0a sources), Google News decoding, `linkcheck.py`, schema update (editions `tech`/`finance`(Markets)/`jobs`, trading-section blocks, optional internal fields, brand setting), agent files + skill, permission allowlist, `publish.py` with approval hash, story memory writes, golden set v1, platform spike, holiday files |
| **0b (business, parallel)** | days 1-10 | Final name; domain + DNS; entity + address; legal consult; landing pages + privacy notice; promise tests with 10 readers; Jobs subscriptions + company list; a hand-built **Jobs sample** and an updated **Markets sample with the trading section** [N4] |
| **Week 1** | days 6-10 | Internal dry runs, Tech + Markets: time every stage, measure tokens, drop rates per stage, human minutes |
| **Week 2** | days 11-15 | Jobs collectors + dry runs; soft launch Tech + Markets (without trading section) to friends |
| **Weeks 3-8** | days 16-45+ | Public; trading section once SEBI-cleared; Jobs public once its dry runs pass |
| **Day 30 / day 60** | | Apply the continue/kill and pipeline rules (section 10) |

**Rough monthly cost:** Claude API with a hard cap (set after week 1) · Apify for X ~$10-30
(from phase 1) · domain ~$12/year · platform free tier · YouTube API and Whisper free tiers.

---

## 14. Credentials

The owner of each account sets it on the always-on machine; **never paste credentials into chat**.
- API keys go in `.env`, which agents are not allowed to read: `YOUTUBE_API_KEY`, `APIFY_TOKEN`,
  `GROQ_API_KEY`, `EXA_API_KEY`, the email-platform key.
- The X burner account's cookies go through `agent-reach configure twitter-cookies`.
- Re-export cookies weekly (heartbeat reminder).

---

## Appendix: gap -> fix map (all 50)

| Gap | Fix in v2 | Gap | Fix in v2 |
|---|---|---|---|
| N1 | §1, §8 heartbeat | O1 | §1 item 3 |
| T1 | decision + §0, §7 (05:00 cutoff) | O2 | §8 Claude usage |
| T2 | §0, §7 IST anchor + DST checklist | O3 | §6 skill orchestrates |
| T3 | Trading merged into Markets, India-morning timing | O4 | §8 machine |
| T4 | §3 "as of" times, no futures | O5 | §6 security |
| T5 | §2 Monday window, §4 exemptions | O6 | §6 publish.py + approval hash |
| T6 | §4 primary-source age, §2 jobs exception | O7 | §8 backups |
| T7 | §6 timeouts, week 1 timing | O8 | §8 audit |
| C1 | §4 evidence tiers, link decoding | O9 | §8 corrections |
| C2 | §4 link script | O10 | §9 spike |
| C3 | Markets + Trading merged | O11 | §9 deliverability |
| C4 | §2 promises + reader tests | B1 | §13 phases 0a/0b |
| C5 | §3 per-edition skeletons | B2 | §8 golden set |
| C6 | §5 source rules | B3 | §8 versioning |
| C7 | §5 company list + re-check | B4 | §12 RACI + minimum mode |
| C8 | §3 zone labels, §7 holiday files | B5 | §6 agent count, summarising in Triage |
| N2 | §6 story memory | B6 | marked "unverified" / to confirm in §5, §11 |
| N3 | §4, §5 transcript numbers | P1 | decision (India-morning) |
| N4 | §13 phase 0b samples | P2 | §10 growth |
| N5 | §9 per-edition opt-out, real-client tests | P3 | §10 metrics + rules |
| L1 | §11 consult | P4 | §9 merge tags, replies |
| L2 | §11 privacy notice | P5 | §2 brand + optional fields |
| L3 | §11 SEBI review, trading section internal | P6 | §9 client and dark-mode tests |
| L4 | §5 ToS register | L6 | §11 entity and address |
| L5 | §5 licence table | L7 | §11 checklist + time log |
