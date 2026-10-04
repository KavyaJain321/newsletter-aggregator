# pipeline/ — newsletter generation pipeline

Built step by step from [`instruction.md`](../instruction.md). **Status: Step 0 (setup & config) done.**

## Setup
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r pipeline/requirements.txt     # Windows (use .venv/bin/python elsewhere)
cp pipeline/env.example .env                                          # then edit; .env is git-ignored
.venv/Scripts/python -m pipeline.cli doctor          # config, Gmail, LLMs, DB, paths
.venv/Scripts/python -m pipeline.cli doctor --deep   # + one live JSON completion
.venv/Scripts/python -m pytest tests -q
```
`doctor` exits 0 only when every required check passes: config valid, Gmail token refreshes with
**exactly** `gmail.readonly` on the expected account, at least one LLM provider usable, DB and
output dirs writable.

## What exists (Step 0)
| Path | What |
|---|---|
| `config/sources.yaml` | Every Tech/Finance source: full sender address (+ display-name regex where an address is shared), brand, editions, cadence, paywall mode, disclosures. Addresses verified against the inbox |
| `config/editions.yaml` | Tech + Finance: schedule, run window, roster order (= coverage-strip order), slots, ranking weights |
| `config/registry.py` | Loads + strictly validates both YAMLs; `match_sender()` resolves a From header to a source |
| `config/settings.py` | Machine settings from env / `.env` (keys masked in repr) |
| `llm/client.py` | One interface: Ollama (native `/api/chat`, `think` + JSON-schema `format`) → Groq (OpenAI-compatible, real User-Agent). Retries, fallback, empty-output guard, JSONL call logs. No silent mock |
| `llm/json_repair.py` | Recovers JSON from model output (reasoning blocks, fences, prose, trailing commas, truncation) — never invents content |
| `ingest/gmail.py` | Read-only auth + profile; refuses any token scope beyond `gmail.readonly` |
| `store/db.py` | SQLite connect + writability probe (schema arrives in Step 4) |
| `cli.py` | `doctor` |

Other packages are empty placeholders named for the step that fills them.

## Key rules baked in
- Runtime LLMs are local Ollama or Groq only — never Anthropic models.
- Coverage counts **brands** (all Semafor editions = 1; TLDR and TLDR Dev = 2).
- A sender must match a full address; shared addresses also need a display-name regex.
- `data/llm_logs/`, `data/archive/`, `out/`, `*.db` are git-ignored (they hold third-party text).
