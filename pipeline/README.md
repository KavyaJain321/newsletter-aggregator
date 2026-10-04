# pipeline/ — newsletter generation pipeline

Built step by step from [`instruction.md`](../instruction.md). **Status: Step 0 (setup & config) done, including on-demand GPU host control.**

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
| `llm/remote_ollama.py` | On-demand Ollama on the shared GPU host over SSH: guarded start, tagged process, stops only its own |
| `cli.py` | `doctor [--deep]`, `ollama status|up|down` |

Other packages are empty placeholders named for the step that fills them.

## On-demand GPU host (trijya-3)
The team's `qwen3:14b` runs on the shared **trijya-3** workstation (RTX 3080 Ti, via Tailscale).
Its Ollama autostart was disabled on request, so with `OLLAMA_REMOTE_SSH` set the pipeline
**starts Ollama only for a run and stops it afterwards** (`llm/remote_ollama.py`):
- starts only if the GPU has >= `OLLAMA_MIN_FREE_VRAM_MB` free, and never in the host's
  04:00-06:45 IST power-off window (Mon-Sat); lifetime capped so it exits before it
- runs under `timeout`, so it dies on schedule even if this machine crashes
- tagged `nlp-ollama-serve`; we only ever stop a process still carrying our tag.
  A server someone else started is used but never stopped
- bound to 127.0.0.1 on the host, reached through the team's Tailscale proxy (`:11435`)
- 1 loaded model, 1 parallel request, model unloaded 2 min after the last request

```bash
.venv/Scripts/python -m pipeline.cli ollama status   # read-only
.venv/Scripts/python -m pipeline.cli ollama up       # manual start (normally per run)
.venv/Scripts/python -m pipeline.cli ollama down     # stops only our tagged process
```
Measured 2026-10-04: start 4 s; `qwen3:14b` 9.6 GB, 100% on GPU; first call ~14 s incl. load.
SSH uses classic curve25519 key exchange: the post-quantum default hung on a Tailscale direct path.

## Key rules baked in
- Runtime LLMs are local Ollama or Groq only — never Anthropic models.
- Coverage counts **brands** (all Semafor editions = 1; TLDR and TLDR Dev = 2).
- A sender must match a full address; shared addresses also need a display-name regex.
- `data/llm_logs/`, `data/archive/`, `out/`, `*.db` are git-ignored (they hold third-party text).
