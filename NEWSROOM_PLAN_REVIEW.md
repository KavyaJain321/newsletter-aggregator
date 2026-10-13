# Gap review of NEWSROOM_PLAN.md (2026-10-13)

> **Status:** all 50 gaps are addressed in `NEWSROOM_PLAN.md` v2 (2026-10-13); see its appendix for the
> gap -> fix map. Keep this file as the record of why each rule exists.

Two passes: an independent adversarial review (it didn't see the plan author's reasoning) and a
check of the plan's assumptions against live data and the repo. **50 gaps: 8 Blockers, 22 High,
18 Medium, 2 Low.** IDs are stable so the team can reference them in PRs.

---

## Found live this week (not theory)

| ID | Sev | Gap | Evidence | Fix |
|---|---|---|---|---|
| **N1** | Blocker | Infrastructure decays when nothing runs. The plan assumes a daily run that doesn't exist yet. | 2026-10-13: the Supabase project is **paused** (its domains return NXDOMAIN: free projects pause after 7 days idle; last ingest was Oct 6). The **Gmail token has expired** (`invalid_grant`, 7-day testing-mode expiry). | Owner restores the Supabase project (dashboard -> Restore) and re-authenticates Gmail. From now on, a **daily heartbeat** (ingest + `doctor`) runs from the always-on machine, starting before week 0. Alert when it fails. |
| **T1** | Blocker | The 12:30 IST cutoff comes before the US morning newsletters arrive. | Measured arrivals (IST): Semafor 15:10-15:30; Neuron, TLDR, Snacks, Hustle 16:00-16:15; Finks, TLDR Dev, Axios Markets, Daily Upside, EntryPoint 16:35-17:55; Superhuman 18:45. Our sends are 16:00-17:30 IST. **Every issue would be built from yesterday's newsletters and land before that morning's TLDR**, so we'd always be one news cycle behind. | Choose one: (a) **India-morning product**: cutoff ~05:00 IST takes in the whole previous US day; send 07:30-08:30 IST. (b) **US-midday product**: cutoff 18:30 IST after the US morning newsletters; produce in the IST evening; send ~12:00 ET. (c) Keep US-morning and position it honestly as a "yesterday, verified" digest. Decide per edition (see P1). |

## A. Timing and freshness

| ID | Sev | Gap | Fix |
|---|---|---|---|
| T2 | Blocker | **US daylight saving ends 1 Nov 2026**, during the public weeks. Every ET-IST conversion and the "16:00 IST no-approval deadline" shift by an hour. | Write the run sheet in the audience's time zone, derive IST from it, keep a DST checklist, and set deadlines relative to send time (T-30 min). |
| T3 | High | Trading's Indian data is stale on arrival. NSE trades 09:15-15:30 IST, so a 16:30 IST issue carries yesterday's Nifty and FII/DII figures next to today's close. | Decide Trading's audience. An India edition needs its own slot: before the open (~08:00 IST) or after the close (~16:00 cutoff, 18:30 send). |
| T4 | High | The "pre-market" label doesn't match the data. Futures fetched at 03:00 ET are 3.5 hours old at a 06:30 ET send, while Europe trades the whole time. | Refresh the data only at about T-30 min, without re-approval of the prose, or label everything "as of HH:MM ET" and drop futures. |
| T5 | High | Several named sources can never pass the 24h rule: CFTC COT (Friday release), AAII (weekly), HN Who's Hiring (monthly), and Monday editions, whose window skips Friday's US news. | An exemption list for scheduled datasets, showing their "as of" date; a Monday "Since Friday" window of up to 72h. |
| T6 | Medium | Freshness rules conflict: §4 uses the email Date header, §7 the primary source's time. Jobs uses 72h against the stated 24h requirement. | An inbox item inherits its primary source's age, or it's ineligible. The owner signs off on the jobs exception. |
| T7 | High | The run-sheet timings are unproven: 15 min to collect ~15 sources plus transcripts, 45 min for ~100 research clusters on free-tier rate limits, 75 min for 4 reviews with no slack. | Time every stage in the dry runs. Start collection earlier. Set per-stage timeouts that fall back to a short edition. |

## B. Content and editorial

| ID | Sev | Gap | Fix |
|---|---|---|---|
| C1 | Blocker | **Our sourcing rules may starve Markets and Tech.** Newsletter scoops and analysis are banned. Primary reporting (Bloomberg, WSJ, FT, Reuters) is paywalled, so the required verbatim evidence can't be fetched. Google News RSS links are redirects, not primary URLs. | Define evidence tiers: a full-text primary source; a headline-only paywalled report, credited "X reported" with no detail beyond it; a fact confirmed by 2+ outlets. Decode Google News links in the collector. Track the drop rate per stage in week 1. |
| C2 | High | "Fact-check returns 200" isn't a real check. SEC returns 403 without a User-Agent; paywalls and Cloudflare return 403; redirects return 301; soft-404s return 200; Kit rewrites every link for tracking. A URL tool for the fact-checker also contradicts "no web tools". | A script, not the agent, resolves redirects, stores the final canonical URL and its status, and allowlists known bot-blocking domains. The fact-checker relies on the cached evidence quote. |
| C3 | High | Markets and Trading overlap almost entirely (close vs dashboard, movers vs "what moved", both calendars), 30 min apart. | Write an ownership matrix (story type -> edition), or **merge them into one edition for the pilot**. |
| C4 | High | No positioning: nothing says why a reader picks us over TLDR, Morning Brew, Finshots or Zerodha, which land at the same time. The coverage strip (our old hook) is gone. | A one-line promise and target reader per edition. Test it with 10 target readers before launch. |
| C5 | Medium | One skeleton doesn't fit all. Jobs (6 modules + 10 roles + big one + split + 6 hits) blows the word budget; "Split" and "Number of the day" are forced for Jobs and Trading. | A skeleton and word budget per edition. Dry-render each against the 102 KB limit. |
| C6 | Medium | Some named sources conflict with the rules: Trendlyne's value is technical calls (banned); curated-job newsletters (e.g. Rise) would mean reusing their curation. | Drop sources whose only value is banned content. Verify every listing on the employer's board. |
| C7 | Medium | Jobs verification is underspecified: no target-company list, no reader country or work-authorisation filter, no re-check that a listing is still open at send time, no estimate of the human cost. | A 100-company list per region before week 2. An automated still-open re-check at publish time. |
| C8 | Medium | No time-zone labels in copy and no holiday files. The pilot spans Diwali (Muhurat trading), Thanksgiving/Black Friday and Christmas. | House style: every time carries ET or IST. Commit 2026 NSE/BSE and NYSE holiday files, plus a team leave calendar. |
| N2 | High | **Story memory has no writer.** The 7-day no-repeat rule and "Update:" stories need a record of what we published, but no agent writes published stories back to Supabase (`items`/`stories` stay empty). | The Publisher writes every sent story (headline, url_key, entities, edition, date) to Supabase. Triage reads it. |
| N3 | Medium | Numbers from YouTube transcripts are unreliable (auto-captions mishear figures). | Transcript-only numbers are never published unless a second source confirms them. |
| N4 | Medium | **No sample issue for Trading or Jobs.** Their format is unproven, and the writers have no exemplar. | Hand-build one Trading and one Jobs sample from real data before their dry runs (as was done for Tech and Markets). |

## C. Legal and compliance

| ID | Sev | Gap | Fix |
|---|---|---|---|
| L1 | High | India's **IT Rules 2021 (digital news publishers)** likely apply to an India-based news publisher: a disclosure to MIB, a grievance officer, a code of ethics. Not mentioned. | A one-hour legal consult before public launch, covering L1-L5 together. |
| L2 | High | DPDP (India) and GDPR (EU sign-ups): no privacy notice written; tracking pixels and link tracking need disclosure. | A privacy notice (Kit as processor, tracking, retention), linked from the signup form. |
| L3 | High | SEBI exposure goes beyond buy/sell calls: "what moved and why" on named Indian stocks, flow commentary and "risk notes" can look like research; finfluencer "education" rules restrict using recent prices. | Indian securities counsel reviews a sample Trading issue. **Trading stays internal until cleared.** |
| L4 | Medium | Terms-of-service exposure: yt-dlp (YouTube ToS), Apify scraping of X, Google News RSS commercial terms, newsletters' "personal use only" terms, residual US "hot news" risk. | A ToS risk register per source, signed off by the owner. Prefer official APIs and RSS. |
| L5 | Medium | Market-data rights are unresolved field by field: CME futures, S&P/Dow index values (licensed), FRED SP500 copyright limits, NSE terms. | A licence table per dashboard field. Drop any field without a clear right. |
| L6 | Medium | No legal entity, postal address, reply-to address or grievance contact (CAN-SPAM, Kit and the renderer's `{{postal_address}}` all need one). | Decide the entity or individual sender; get a PO box or virtual address in week 0. |
| L7 | Medium | The AI disclosure promises human review; a 15-minute target invites rubber-stamping. | A review checklist the approver signs; log time spent and edits made. |

## D. Growth, product and measurement

| ID | Sev | Gap | Fix |
|---|---|---|---|
| P1 | Blocker | **The audience (D1) isn't decided, yet the content assumes both answers**: US send times and sources alongside Nifty, FII/DII, SEBI, PLFS/EPFO and India-remote jobs. This drives timing (T1/T3), sources, legal exposure and currency. | Decide the audience **per edition** before writing any persona. |
| P2 | Blocker | **No subscriber plan**: no landing page, signup form, channels (X, LinkedIn, communities, cross-promotion, referrals), target or owner. Without readers the pilot can't measure anything. | Name a growth owner. Kit landing pages with double opt-in + 18+. Weekly subscriber targets per edition with 2-3 named channels. |
| P3 | High | The metrics can't decide anything. Open rate is inflated by Apple Mail Privacy Protection. "Unsubscribes <0.5%" is noise at ~100 readers. There are no retention, click, reply, cost or human-minutes metrics, and no continue/kill rule. | Clicks, 4-week retention, replies, cost and human minutes per issue. **Write the day-30 and day-60 continue/kill thresholds now.** |
| P4 | High | Dead links in the email: `{{web_url}}`, `{{feedback_url}}`, `{{subscribe_url}}`, `{{preferences_url}}` have nothing serving them, and Kit's tag syntax differs. Nobody owns reader replies, which may ask for investment advice. | Map each tag to a Kit feature or remove it. Assign a daily reply-triage owner, with a no-personal-advice reply policy. |
| P5 | Medium | The brand undercuts rule 11: "Twenty to One" is hard-coded in the renderer; the schema still requires `roster`, `issues_read`, `ads_removed` (newsletter-centric fields). | Final name before any public send. Make those fields optional and internal. |
| N5 | High | **Kit's unsubscribe is account-wide.** With 4 editions as tags in one account, a reader who dislikes one edition loses all four. Kit's custom-HTML support and its own footer and branding (free plan) are unverified. | Prove a per-edition preference flow in Kit, or use separate lists. Send our HTML through Kit to real Gmail, Outlook-desktop and iOS inboxes on day 1. |
| P6 | Low | Accessibility and dark mode untested; no policy for our own charts; emoji in subjects. | Add dark-mode and screen-reader checks to the standards tests. |

## E. Ops, SRE and security

| ID | Sev | Gap | Fix |
|---|---|---|---|
| O1 | Blocker | **The Gmail fix is wrong as written.** "Publish the OAuth app" with the restricted `gmail.readonly` scope can trigger Google verification and a CASA security assessment (weeks). | Switch the app to **"In production" without submitting for verification**. This should remove the 7-day expiry; the unverified-app warning and 100-user cap are fine for one inbox. Verify this week (see N1). |
| O2 | High | Claude usage is unbudgeted: Max-plan 5-hour and weekly caps vs 4 parallel editions with rewrite loops; an individual subscription driving a team's headless cron may breach its terms. | API billing with a hard monthly cap and a token budget per edition. Decide the model split, and which edition to drop first when a cap hits. |
| O3 | High | The plan makes the orchestrator a subagent that calls other subagents; Claude Code doesn't reliably support subagents spawning subagents. | The `/produce-issue` skill (main session) orchestrates. "Chief Editor" is the skill, not an agent file. |
| O4 | High | One always-on machine holds everything (Gmail, cookies, residential IP, `.env`, cron), and it isn't named. | Name the machine and its owner; UPS and auto-restart; 12:00 IST health check; a written manual runbook for a second machine. |
| O5 | High | Weak security on that machine. The Researcher reads raw scraped text and can fetch any URL (an exfiltration path for `.env` secrets). "Bash, scripts only" isn't enforced. The unattended cron likely runs with relaxed permissions. The machine shares `D:\Work` with other projects. | Permission allowlists in settings; agents run without `.env` in their environment; Researcher fetches limited to cited domains; a separate OS user or folder; an injection red-team set. |
| O6 | High | The approval hook is easy to bypass: a `PreToolUse` match on a "Kit schedule" call misses a Python or curl call, and it ignores a human editing the draft in Kit's UI after approval. | Only the publish script holds the Kit key, and it refuses without a matching approval hash; agents never see the key. Edits happen in the issue JSON, never in Kit. |
| O7 | Medium | Supabase is a single point of failure (see N1): no free-tier backups; transcripts and posts head toward the 500 MB cap. | Nightly `pg_dump` to the machine; size alarm at 70%; raw transcripts stay out of the DB. |
| O8 | Medium | No audit trail: `runs/` is local and gitignored, so fact-check reports and approvals for sent issues die with the machine. | Archive each sent issue's JSON, fact-check report and approval to Supabase. Set a retention policy for scraped personal data. |
| O9 | Medium | Corrections are too slow: "fix it in the next issue" means a Friday error is fixed Monday; there's no severity ladder for a serious financial error. | Same-day correction email for material errors; an on-call owner; a template. |
| O10 | Medium | Kit is assumed, not proven: drafts, test email, scheduling, stats and preferences by API on the free plan, plus account review or flagging of a new sender. | Prove draft -> test -> schedule by API on day 1 of week 0. Keep a fallback provider account. |
| O11 | Medium | Warm-up is vague: no weekly volumes, no seed-inbox tests, no DMARC reporting address, no spam-complaint plan. | A week-by-week volume ramp; seed inboxes (Gmail, Outlook, Yahoo); DMARC `rua=`. |

## F. Build and process

| ID | Sev | Gap | Fix |
|---|---|---|---|
| B1 | Blocker | **Week 0 can't be done in 5 days, and it hasn't started.** A week after the plan, no `.claude/agents` or skills exist. Scope: 10 decisions, domain/DNS/Kit, ~15 collectors, 10+ agent files, 4 personas, the skill, schema changes (`edition` accepts only tech/finance; renderer accents only for those two), the hook, holiday files and company lists. | **Cut week 0 to Tech + Markets** (inbox, HN, RSS, EDGAR, FRED only). Trading and Jobs move to a later "week 0b". |
| B2 | High | No agent evaluation before day 1: no golden set, seeded errors or known-bad issues, so "fact-checker catch rate" has no ground truth. | 20 seeded-error issues + 10 injection samples, run as a test on every prompt change. |
| B3 | High | No prompt versioning or learning loop. | Record the agent-file git SHA in each run manifest; Friday changes ship as a PR; approver edits are logged as diffs and feed the next week's prompts. |
| B4 | High | Staffing single point of failure: approver and backup unnamed; 60 weekdays x 75+ min against a hard deadline; no RACI for sources, legal, growth or the machine. | Named primary and backup approver per weekday; a 2-edition minimum mode; a one-page RACI. |
| B5 | Medium | Internal inconsistencies: "nine roles" vs 7 relay stages vs 10 agents in the table; collectors "scripts + Haiku" and a cheap model summarising during collection contradict "no AI in capture". | Fix the count. Move all summarisation into Triage. |
| B6 | Low | Unverified claims: Reddit closure dates (13 Nov in §4, 31 Oct / 13 Nov in §7), Kit's free API, the scope of EU AI Act Art. 50 (editorial-review exemption), "domain ~$1" (that's per month). | Add a source link or an "unverified" mark to each. |

---

## Top 10 to settle before any build work

1. **N1:** restore Supabase and re-authenticate Gmail now, then start a daily heartbeat run.
2. **P1 + T1 + T3:** decide the audience per edition; that fixes the clock (cutoff, send time, Trading's slot).
3. **T2:** redo the run sheet around the 1 Nov DST change.
4. **O1:** switch the Gmail app to "In production" (no verification) and confirm the token stops expiring.
5. **B1:** cut week 0 to Tech + Markets; Trading and Jobs follow once cleared (L3) and sampled (N4).
6. **C1 + C2:** evidence tiers for paywalled reports, Google News link decoding, a real link checker.
7. **C3:** merge Markets and Trading for the pilot, or write the ownership matrix.
8. **O2 + O3 + O6:** API billing with a cap, the skill as orchestrator, the Kit key held only by the publish script.
9. **P2 + P3 + N5:** growth owner and signup page, decision-grade metrics with continue/kill thresholds, a per-edition unsubscribe in Kit.
10. **L1-L3 + L6 + B4:** one legal consult (IT Rules, DPDP, SEBI), entity and address, named approver rota and RACI.
