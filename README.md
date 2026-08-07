# Newsletter Aggregator

An automated pipeline that **subscribes one Gmail to ~45 newsletters across 9 topic segments**,
auto-sorts them, archives every issue into a structured store, and (in progress) uses a
**non-Claude LLM** (Groq / local Qwen) to summarize them into our own digest newsletters.

> **👉 New here? Read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) first.** It's the full handoff:
> every decision, current status, how the Gmail API access works, the DB design, and the
> product strategy. It also has a **Session Log** recording what each work session discussed.

---

## Team workflow (how we collaborate)

We collaborate through this repo — shared files + a shared decision log. GitHub does **not** stream
live Claude Code chats; instead we keep the discussion durable in `PROJECT_CONTEXT.md`.

**Every session:**
1. `git pull` — get the latest.
2. Read the top of [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) (esp. the **Session Log**) to see what's new.
3. Do your work / discuss with Claude Code in your own session.
4. Ask Claude: *"update PROJECT_CONTEXT.md with this session"* → appends a dated Session Log entry.
5. `git add -A && git commit && git push`.

Keep `data/sources.csv` as the live status tracker; keep design in `PHASE4_DESIGN.md`.

---

## First-time setup (each machine needs its own Gmail access)

Secrets are **never** committed. Each teammate authenticates their own Gmail API access:

1. Install Node.js (v20+) and `pnpm`.
2. Set up the Gmail tool:
   ```bash
   cd tools/google-skill
   pnpm install
   # Provide OWN Google Cloud OAuth creds at ~/.config/google-skill/credentials.json
   # (Google Cloud project → enable Gmail API → OAuth Desktop client → download JSON)
   npx tsx skills/gmail/scripts/gmail.ts auth   # opens browser, read-only Gmail scope
   ```
   Full steps: see **Section 6** of [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md).
3. Read the inbox:
   ```bash
   npx tsx skills/gmail/scripts/gmail.ts list --query="in:anywhere newer_than:2d" --max=50
   ```

The Gmail API is **free**. The capture/parse pipeline uses **no AI**; only the enrichment step (Phase 5)
uses an LLM, and that is **Groq or local Qwen — never Claude**.

---

## Repo map
| Path | What |
|---|---|
| [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) | Master context / team handoff / session log |
| [`PHASE4_DESIGN.md`](PHASE4_DESIGN.md) | Archive + LLM-enrichment design + full DB schema |
| [`NEWSLETTER_SCHEDULE.md`](NEWSLETTER_SCHEDULE.md) | Per-newsletter frequency & expected delivery |
| `data/sources.csv` | Live per-newsletter status tracker |
| `data/category_feeds.csv` | 9 segments → +tag → label mapping |
| `gmail_filters*.xml` | Importable Gmail filters |
| `tools/google-skill/` | Gmail-API tool (secrets & node_modules are gitignored) |
| `data/archive/` | Local newsletter archive (.eml + .md) — **gitignored, stays local** |

---

## Status (2026-08-07)
Phases 1–3 done (~39–41/45 newsletters live). Phase 4 (archive) designed + proven on one email.
Phase 5 (LLM enrichment) designed. See `PROJECT_CONTEXT.md` for the full picture and next steps.
