# 👋 Team Onboarding — Newsletter Aggregator

> **New here? Read this once, top to bottom.** It tells you what we're building, what's done,
> how the finance work stands, where everything lives, and how to contribute — in ~5 minutes.
> For the exhaustive deep-reference, see [`PROJECT_DOSSIER.md`](PROJECT_DOSSIER.md). Live day-to-day
> status is [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) and [`data/sources.csv`](data/sources.csv).

**Repo:** https://github.com/KavyaJain321/newsletter-aggregator
**Last updated:** 2026-09-30

---

## 1. What this project is (in one paragraph)

We subscribe **one dedicated Gmail** (`notifyy1008@gmail.com`) to a curated set of the best
newsletters across **9 topic areas**, auto-sort them into labeled folders with Gmail filters,
archive every issue in a structured store (SQLite + raw `.eml` + clean `.md`), and then use a
**local/non-Claude LLM** to fuse many newsletters into **our own aggregated digest** per topic.
Think: "read 200 newsletters, publish the 1 that matters." Nothing hits anyone's personal inbox.

---

## 2. How the plumbing works (the one concept to understand)

- Every newsletter is subscribed with a **plus-tagged address**, e.g. `notifyy1008+biz@gmail.com`.
  Gmail delivers all `+anything` mail to the same inbox, and a **filter routes each `+tag`** to a
  labeled folder like `Newsletters/2-BizFinance`.
- Some big publishers (Bloomberg, Morning Brew, Yahoo, Axios) **reject the `+`**, so those are
  subscribed with the **plain** address and routed by a **sender-based filter** instead
  (see [`gmail_filters_sender.xml`](gmail_filters_sender.xml)).
- ⚠️ **Sender filters use the exact address, not just the domain**, when a domain is shared —
  e.g. `markets@axios.com` (Axios Markets) vs Axios AM, or `netinterest@substack.com` (never a bare
  `substack.com`, which would grab every Substack we get).

---

## 3. The 9 segments

| # | Segment | Folder | Examples |
|---|---|---|---|
| 1 | Tech / AI | `1-TechAI` | TLDR, The Pragmatic Engineer, Import AI |
| 2 | **Business / Finance** | `2-BizFinance` | Morning Brew, The Daily Upside, Money Stuff *(see §4)* |
| 3 | Legal | `3-Legal` | Above the Law, National Law Review, SCOTUSblog |
| 4 | HR / People Ops | `4-HRPeopleOps` | HR Brew, HR Dive, SHRM |
| 5 | GitHub / Dev tools | `5-GitHubRepos` | Changelog Nightly, TLDR WebDev, Bytes |
| 6 | Indie Hacker | `6-IndieHacker` | Indie Hackers, Starter Story, Trends.vc |
| 7 | Absurdist / Satire | `7-Absurdist` | The Onion, Reductress, Babylon Bee |
| 8 | Micro / Small-Cap | `8-MicroSmallCap` | Zacks SCR, Planet MicroCap |
| 9 | Mainstream News | `9-MainstreamNews` | NYT, WaPo, Guardian, Axios AM, Semafor |

We started with **5 curated picks per segment (45 total)**; ~38 were confirmed delivering before the
finance expansion below. A few originals were dropped (paid-only or no signup) — tracked in `sources.csv`.

---

## 4. Finance — where it stands (this is the area we've pushed hardest)

The **Business/Finance segment (`2-BizFinance`)** was expanded from 5 → **17 newsletters tracked**.

**✅ Confirmed active (11):**
| Newsletter | Frequency |
|---|---|
| Morning Brew | daily |
| The Hustle | daily |
| The Daily Upside | daily |
| The Average Joe | 3×/week |
| The Diff | weekly |
| **Money Stuff** (Matt Levine / Bloomberg) ⭐ | daily |
| **Axios Markets** | daily |
| **Net Interest** (Marc Rubinstein) ⭐ | weekly |
| **Doomberg** | 2×/week |
| **Bloomberg Businessweek Daily** | daily |
| **EntryPoint** (Sherwood) | daily |

**🟡 Subscribed, awaiting confirmation (3):** Snacks · Axios Pro Rata · Stratechery
*(click the confirm/verify email in the inbox to activate)*

**⬜ Chosen but not yet subscribed (3):** Bloomberg Five Things · Yahoo Finance Morning Brief · What's the Big Deal (Wall Street Prep)

**Finance-adjacent (Segment 8, Micro/Small-Cap):** Zacks SCR Digest ✅, Planet MicroCap ✅,
RedChip 🟡 (needs code) — plus bonus value-investing Substacks flowing in.

> The finance changes live on branch **`finance/add-free-newsletters`** (open PR, not merged yet).

---

## 5. Project phases — what's done vs next

1. **Phase 1–3 — Subscribe + route + verify** ✅ done. ~38+ newsletters confirmed delivering into labels.
2. **Phase 4 — Archive** (SQLite + `.eml` + clean `.md`): designed in [`PHASE4_DESIGN.md`](PHASE4_DESIGN.md); a working MVP now exists (see §6).
3. **Phase 5 — LLM enrichment** (story extraction): MVP exists (see §6). **Must use a non-Claude LLM.**
4. **Phase 6 — Our own digest**: sample issues + strategy in [`NEWSLETTER_SAMPLES.md`](NEWSLETTER_SAMPLES.md); first machine-generated issue produced (experimental).

---

## 6. 🧪 Experimental: the pipeline test (Pranav's branch)

A teammate (**Pranav**) built an **early test of the capture → extract → generate pipeline** on branch
**`feat/pipeline-mvp`**. **Status: experimental / proof-of-concept only — not merged, not production.**

In short, it's a small Python program that (1) pulls newsletters from Gmail and cleans them, (2) breaks
each into "story cards," and (3) merges cards from several newsletters into **one combined issue**. It
runs on a **local AI (qwen3), with Groq as backup — never Claude**, per our rule. As a first test it
fused 3 Tech newsletters into one sample issue ("THE SIGNAL — Tech"). The output still has rough edges
(an ad leaked in, minor AI mistakes) — which is expected for a test.

**Treat it as a spike to learn from, not the final system.** Nothing here is decided or merged.

---

## 7. Where things live (file map)

| File | What |
|---|---|
| [`data/sources.csv`](data/sources.csv) | **Live per-newsletter status tracker** (the source of truth) |
| [`data/category_feeds.csv`](data/category_feeds.csv) | 9 segments → `+tag` address → folder mapping |
| [`gmail_filters.xml`](gmail_filters.xml) | Tag-based routing filters (import into Gmail) |
| [`gmail_filters_sender.xml`](gmail_filters_sender.xml) | Sender-based filters (plus-rejecting sites) |
| [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) | Living state + session log |
| [`PROJECT_DOSSIER.md`](PROJECT_DOSSIER.md) | Exhaustive deep-reference of everything |
| [`PHASE4_DESIGN.md`](PHASE4_DESIGN.md) | Archive + DB schema design |
| [`NEWSLETTER_SAMPLES.md`](NEWSLETTER_SAMPLES.md) | Sample digest issues + product strategy |
| [`NEWSLETTER_SCHEDULE.md`](NEWSLETTER_SCHEDULE.md) | Per-newsletter send-day / delivery timing |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Full team workflow detail |

---

## 8. How to contribute

1. `git clone https://github.com/KavyaJain321/newsletter-aggregator.git`
2. Read this file + `PROJECT_CONTEXT.md`.
3. Work on a **branch**, push, open a **PR** — never commit directly to `main`. (See `CONTRIBUTING.md`.)
4. When your session does real work, ask Claude to **append a note to `PROJECT_CONTEXT.md`** so the team sees it.

### Hard rules (do not break)
- **No Claude/AI in the capture-and-summarize pipeline** — use a local LLM (qwen) or Groq.
- **Never commit secrets** — Gmail OAuth token/credentials are gitignored and machine-local.
- **Gmail access is LOCAL-only** — only a machine with the authenticated tool can read the inbox.
  Do Gmail work locally, push results (e.g. `sources.csv`); cloud/teammate sessions usually can't reach Gmail.

---

## 9. Current open branches (nothing merged into `main` yet)

| Branch | What | Status |
|---|---|---|
| `finance/add-free-newsletters` | Finance newsletters + exact-sender filters | open PR |
| `feat/pipeline-mvp` | 🧪 Pipeline experiment (Pranav) | experimental, open |
| `docs/project-dossier` | The deep-reference doc | open PR |
| `docs/team-onboarding` | This file | open PR |

**Welcome aboard.** Start with `sources.csv` to see live status, then pick a segment and dig in.
