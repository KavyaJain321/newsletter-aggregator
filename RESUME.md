# Newsletter Aggregator — Resume Prompt

Paste this entire file into a new Claude Code chat to resume exactly where we left off.

---

## What This Project Is

A newsletter aggregation pipeline that:
1. Subscribes to 45 newsletters across 9 topic segments, all delivered to ONE Gmail
   (`notifyy1008@gmail.com`) using `+tag` plus-addressing for auto-sorting.
2. Eventually summarizes them with AI (Phase 4 — NOT started yet).

**Project folder:** `D:/Work/Projects/newsletter-aggregator/newsletter-aggregator/`

> **IMPORTANT — approach changed (2026-08-02):** This project originally used
> Kill-the-Newsletter (KTN) to turn newsletters into RSS feeds. We RETIRED that because
> the KTN address got blocked by many signup forms (only 3 of 45 subscribed). We now use a
> single real Gmail with per-segment `+tags`. The old `scripts/phase2*` and `debug_ktn*`
> files are KTN-era and no longer part of the live plan.

---

## Project Files

| File | Purpose |
|---|---|
| `data/sources.csv` | All 45 newsletters — signup URLs, segment Gmail `+tag`, label, status |
| `data/category_feeds.csv` | 9 segments → `+tag` address + Gmail label |
| `GMAIL_SETUP.md` | Step-by-step to create the 9 auto-sorting Gmail filters |
| `SIGNUP_CHECKLIST.md` | Ordered, grouped checklist for doing the 45 signups |
| `scripts/*` | KTN-era Playwright scripts — obsolete, kept for reference only |

---

## 9 Segments → Gmail addresses & labels

| Segment | Subscribe with | Gmail label |
|---|---|---|
| 1-TechAI | `notifyy1008+techai@gmail.com` | Newsletters/1-TechAI |
| 2-BizFinance | `notifyy1008+biz@gmail.com` | Newsletters/2-BizFinance |
| 3-Legal | `notifyy1008+legal@gmail.com` | Newsletters/3-Legal |
| 4-HRPeopleOps | `notifyy1008+hr@gmail.com` | Newsletters/4-HR |
| 5-GitHubRepos | `notifyy1008+github@gmail.com` | Newsletters/5-GitHub |
| 6-IndieHacker | `notifyy1008+indie@gmail.com` | Newsletters/6-IndieHacker |
| 7-Absurdist | `notifyy1008+satire@gmail.com` | Newsletters/7-Absurdist |
| 8-MicroSmallCap | `notifyy1008+smallcap@gmail.com` | Newsletters/8-SmallCap |
| 9-MainstreamNews | `notifyy1008+news@gmail.com` | Newsletters/9-News |

All 9 `+tag` addresses deliver to the single `notifyy1008@gmail.com` inbox. No extra
accounts exist. Gmail filters read the `+tag` and apply the matching label.

---

## Current Status (as of 2026-08-02)

- Approach pivoted from KTN → Gmail `+tags`.
- 9 tag-based Gmail filters created (imported from `gmail_filters.xml`) — WORKING.
- **Signups done: 44 / 45.**
  - 36 subscribed via `+tag` (auto-sorted by the 9 filters).
  - 4 rejected the `+` so used plain `notifyy1008@gmail.com` — need sender-based filters
    (`gmail_filters_sender.xml`): Morning Brew, FindLaw, HR Brew, Babylon Bee.
  - 8 of the above are double opt-in (`subscribed_pending_confirmation`) — need a confirm click.
  - 1 failed: Small Cap Discoveries (`failed_retry`).
- `expected_next_check` dates filled: daily ~2026-08-05, weekly ~2026-08-11.

### Open to-dos
1. Import `gmail_filters_sender.xml` (4 sender filters) with "apply to existing".
2. Verify the 4 sender domains once real mail arrives (adjust if From differs from guess).
3. Click the 8 confirmation links.
4. Optional: retry Small Cap Discoveries.
5. On the next-check dates, verify newsletters are landing in each label.
6. Then start Phase 4.

---

## What To Do Next (in order)

1. **Create the 9 Gmail filters** — follow `GMAIL_SETUP.md`. (~10 min, one-time.)
2. **Do the signups** — follow `SIGNUP_CHECKLIST.md`, easiest tier first. For each, paste the
   segment's `+tag` address into the signup form.
3. **Confirm subscriptions** — open Gmail, click any "Confirm/Verify" links. Many newsletters
   send nothing until confirmed.
4. **Update `sources.csv`** — set `status = subscribed` and `date_subscribed` per row as you go.
5. **Phase 4 (NOT started)** — LLM summarization pipeline:
   - Read the segment labels from Gmail via the Gmail API.
   - Run entries through Claude to summarize.
   - Compose a digest.
   Do NOT start Phase 4 until at least one full send cycle has arrived and is confirmed working.

---

## Rules & Conventions

- One Gmail `+tag` PER SEGMENT (not per newsletter) — all 5 newsletters in a segment share one tag.
- `status` values: `not_subscribed` | `subscribed`.
- `signup_note` = a hint about the signup hurdle (CAPTCHA / paywall / JS form / simple).
- `expected_next_check` = `date_subscribed` + frequency days + 2 buffer
  (daily=3, weekly=9, biweekly=16, 3x-weekly=5, monthly=32).

---

## Tech Stack

- Single Gmail account with `+tag` plus-addressing + filters (no KTN, no RSS).
- CSV files only — no database yet.
- Phase 4 will use the Gmail API to read mail (planned, not built).
- Python 3.11 / Playwright scripts in `scripts/` are KTN-era and obsolete.
