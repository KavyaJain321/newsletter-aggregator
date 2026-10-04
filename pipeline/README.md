# pipeline/ — newsletter generation pipeline

Built step by step from [`instruction.md`](../instruction.md). **Status: Step 0 (setup & config) done, including isolated on-demand GPU host control and health monitoring.**

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
| `llm/host_monitor.py` | Shared-host health: GPU heat/util/power/fan/VRAM/throttling, CPU load, RAM, swap, disk. Start gate, background watch, per-request gate |
| `llm/session.py` | `llm_session()`: the one way a run gets an LLM client - start, monitor, tunnel, always stop |
| `cli.py` | `doctor [--deep]`, `ollama status|up|down`, `host status|watch` |

Other packages are empty placeholders named for the step that fills them.

## On-demand GPU host (trijya-3)
The team's `qwen3:14b` runs on the shared **trijya-3** workstation (RTX 3080 Ti, via Tailscale).
Its Ollama autostart was disabled on request, so with `OLLAMA_REMOTE_SSH` set the pipeline
**starts its own private Ollama only for a run and stops it afterwards**:
- **isolated:** listens on private port `11436` (not the shared `11434` that the team proxy
  forwards), reached only through an SSH tunnel this process holds. Other services keep
  seeing Ollama "off" and can't queue work on our instance. If anything else holds `11436`, we refuse
- **health-gated start:** GPU < 80 C, no thermal throttling, >= `OLLAMA_MIN_FREE_VRAM_MB` free,
  CPU load/core, RAM, swap and disk all within limits; never in the 04:00-06:45 IST power-off
  window (Mon-Sat), and its lifetime is capped to end before it
- **watched while running** (`llm/host_monitor.py`, logged to `data/host_monitor/`): every 30 s and
  before every request. >= 82 C pauses our requests until 78 C; >= 87 C, hardware throttling,
  RAM/swap exhaustion or a lost connection stops our Ollama immediately
- runs under `timeout`, so it dies on schedule even if this machine crashes
- tagged `nlp-ollama-serve`; we only ever stop a process still carrying our tag
- 1 loaded model, 1 parallel request, model unloaded before stopping

```bash
.venv/Scripts/python -m pipeline.cli ollama status   # read-only
.venv/Scripts/python -m pipeline.cli ollama up       # manual start (normally per run)
.venv/Scripts/python -m pipeline.cli ollama down     # stops only our tagged process
.venv/Scripts/python -m pipeline.cli host status     # heat / load / memory, read-only
.venv/Scripts/python -m pipeline.cli host watch --interval 30 --count 10
```
Measured 2026-10-04: start 4 s; `qwen3:14b` 9.6 GB, 100% on GPU; isolated JSON round-trip 5.0 s incl.
load (61 s when the instance was on the shared port and other services queued on it).
SSH uses classic curve25519 key exchange: the post-quantum default hung on a Tailscale direct path.

## Key rules baked in
- Runtime LLMs are local Ollama or Groq only — never Anthropic models.
- Coverage counts **brands** (all Semafor editions = 1; TLDR and TLDR Dev = 2).
- A sender must match a full address; shared addresses also need a display-name regex.
- `data/llm_logs/`, `data/archive/`, `out/`, `*.db` are git-ignored (they hold third-party text).
