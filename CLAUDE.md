# CLAUDE.md — read this first (auto-loaded every session)

You are working on the **Newsletter Aggregator** project. This file loads into every session
(any teammate, cloud or local), so it's the shared starting point.

## Get oriented before doing anything
**Read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)** — it's the full state, every decision, and a
**Session Log** of what past sessions did. That's how you "continue" the shared thread of work.
Live per-newsletter status is in `data/sources.csv`. Design is in `PHASE4_DESIGN.md`.

## Hard rules
- **Never commit secrets.** Gmail OAuth token/credentials are gitignored and machine-local.
  `~/.config/google-skill/credentials.json` and `.claude/*.local.json` must never be pushed.
- **Gmail access is LOCAL-only.** Only a session with the authenticated `tools/google-skill` tool
  can read `notifyy1008@gmail.com`. Cloud/teammate sessions usually can't — don't wait on Gmail there.
  Do Gmail work in the local session, push results (e.g. `data/sources.csv`), teammates `git pull`.
- **Collection stays scripted (no AI in capture).** Since 2026-10-06 the team runs a 60-day pilot where
  Claude Code agents do the *editorial* work (triage, research, writing, fact-check). See `NEWSROOM_PLAN.md`.
- **Readers never see which newsletters we read** (instruction.md rule 11; enforced by a render test).

## How we collaborate (see CONTRIBUTING.md for detail)
- Work on a **branch**, push, open a **PR** — don't commit directly to `main`. The owner reviews PRs.
- When a session did meaningful work, **append a note to `PROJECT_CONTEXT.md`** (Session Log) and
  include it in your PR, so everyone sees what was discussed/decided.

## Where things stand (2026-10-13)
**Pipeline build is paused.** 60-day pilot: **3 daily newsletters for Indian readers** (Markets 07:45,
Tech 08:00, Jobs 08:30 IST; Trading merged into Markets) produced by Claude Code agents + a human
approver. Read **`NEWSROOM_PLAN.md` (v2)** first; `NEWSROOM_PLAN_REVIEW.md` explains why each rule exists.
Reused from the pipeline: Gmail ingest -> Supabase (`DATABASE_URL` in `.env`), the issue schema and
renderer (`pipeline/compose`, `pipeline/render`), samples in `design/`. Session Log in `PROJECT_CONTEXT.md`.
