"""Runtime settings from environment variables (optionally a git-ignored `.env`).

Machine-specific values only: paths, model hosts, keys. Editorial config lives in
sources.yaml / editions.yaml. Secrets are never printed: `Settings` masks them in repr.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(__file__).resolve().parent


def _read_dotenv(path: Path) -> dict[str, str]:
    """Minimal KEY=VALUE parser for a local .env (no interpolation, # comments)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        val = val.strip()
        if val[:1] in ("\"", "'"):  # quoted: take up to the matching quote, ignore the rest
            end = val.find(val[0], 1)
            val = val[1:end] if end != -1 else val[1:]
        elif val.startswith("#"):  # "KEY=   # note": empty value followed by a comment
            val = ""
        else:  # unquoted: drop an inline comment ("VALUE   # note"), as standard dotenv does
            val = re.split(r"\s+#", val, maxsplit=1)[0].strip()
        values[key] = val
    return values


def _path(value: str, base: Path = REPO_ROOT) -> Path:
    p = Path(os.path.expanduser(value))
    return (p if p.is_absolute() else (base / p)).resolve()


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_path: Path
    archive_dir: Path
    out_dir: Path
    llm_log_dir: Path
    fixtures_dir: Path
    gmail_token_path: Path
    gmail_client_path: Path
    gmail_account: str
    ollama_base_url: str
    ollama_model: str
    ollama_embed_model: str
    groq_base_url: str
    groq_model: str
    groq_api_key: str | None = field(repr=False)
    llm_provider_order: tuple[str, ...]
    llm_timeout_s: float
    llm_max_retries: int
    llm_think: bool
    llm_log_text: bool
    # On-demand remote Ollama (instruction.md option A). Off unless OLLAMA_REMOTE_SSH is set.
    ollama_remote_ssh: str | None = None
    ollama_remote_bin: str = "$HOME/ollama/bin/ollama"
    ollama_remote_port: int = 11436        # private: NOT forwarded by the host's shared proxy
    ollama_tunnel_port: int = 11437        # local end of our SSH tunnel to that port
    ollama_remote_max_minutes: int = 90
    ollama_min_free_vram_mb: int = 10000
    ollama_keep_alive: str = "2m"
    remote_tz: str = "Asia/Kolkata"
    remote_blackout: str = "03:50-06:50"      # host is powered off 04:00-~06:45
    remote_blackout_days: str = "1-6"         # ISO weekdays: Mon-Sat (Sunday stays on)
    # Shared-host health guard (pipeline/llm/host_monitor.py)
    host_start_gpu_temp_c: float = 80.0
    host_warn_gpu_temp_c: float = 82.0
    host_resume_gpu_temp_c: float = 78.0
    host_critical_gpu_temp_c: float = 87.0
    host_monitor_interval_s: float = 30.0
    host_max_cooldown_s: float = 600.0

    @property
    def groq_key_set(self) -> bool:
        return bool(self.groq_api_key)

    def __repr__(self) -> str:  # never leak the key
        key = "set" if self.groq_api_key else "unset"
        return f"Settings(db={self.db_path}, ollama={self.ollama_base_url}:{self.ollama_model}, groq={self.groq_model}[key {key}])"


def load_settings(env: dict[str, str] | None = None, dotenv_path: Path | None = None) -> Settings:
    """Environment variables win over `.env`; `.env` wins over defaults."""
    merged = _read_dotenv(dotenv_path or (REPO_ROOT / ".env"))
    merged.update(os.environ if env is None else env)
    g = merged.get

    data_dir = _path(g("PIPELINE_DATA_DIR", "data"))
    return Settings(
        data_dir=data_dir,
        db_path=_path(g("PIPELINE_DB_PATH", str(data_dir / "pipeline.db"))),
        archive_dir=_path(g("PIPELINE_ARCHIVE_DIR", str(data_dir / "archive"))),
        out_dir=_path(g("PIPELINE_OUT_DIR", "out")),
        llm_log_dir=_path(g("PIPELINE_LLM_LOG_DIR", str(data_dir / "llm_logs"))),
        fixtures_dir=_path(g("FIXTURES_DIR", "../newsletter-aggregator-fixtures")),
        gmail_token_path=_path(g("GMAIL_TOKEN_PATH", "tools/google-skill/.claude/google-skill.local.json")),
        gmail_client_path=_path(g("GMAIL_CLIENT_PATH", "~/.config/google-skill/credentials.json")),
        gmail_account=g("GMAIL_ACCOUNT", "notifyy1008@gmail.com").strip().lower(),
        ollama_base_url=g("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=g("OLLAMA_MODEL", "qwen3:14b"),
        ollama_embed_model=g("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        groq_base_url=g("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"),
        groq_model=g("GROQ_MODEL", "qwen/qwen3-32b"),
        groq_api_key=(g("GROQ_API_KEY") or "").strip() or None,
        llm_provider_order=tuple(p.strip().lower() for p in g("LLM_PROVIDER_ORDER", "ollama,groq").split(",") if p.strip()),
        llm_timeout_s=float(g("LLM_TIMEOUT_S", "180")),
        llm_max_retries=int(g("LLM_MAX_RETRIES", "3")),
        llm_think=g("LLM_THINK", "true").strip().lower() in {"1", "true", "yes", "on"},
        llm_log_text=g("LLM_LOG_TEXT", "true").strip().lower() in {"1", "true", "yes", "on"},
        ollama_remote_ssh=(g("OLLAMA_REMOTE_SSH") or "").strip() or None,
        ollama_remote_bin=g("OLLAMA_REMOTE_BIN", "$HOME/ollama/bin/ollama"),
        ollama_remote_port=int(g("OLLAMA_REMOTE_PORT", "11436")),
        ollama_tunnel_port=int(g("OLLAMA_TUNNEL_PORT", "11437")),
        ollama_remote_max_minutes=int(g("OLLAMA_REMOTE_MAX_MINUTES", "90")),
        ollama_min_free_vram_mb=int(g("OLLAMA_MIN_FREE_VRAM_MB", "10000")),
        ollama_keep_alive=g("OLLAMA_KEEP_ALIVE", "2m"),
        remote_tz=g("REMOTE_TZ", "Asia/Kolkata"),
        remote_blackout=g("REMOTE_BLACKOUT", "03:50-06:50"),
        remote_blackout_days=g("REMOTE_BLACKOUT_DAYS", "1-6"),
        host_start_gpu_temp_c=float(g("HOST_START_GPU_TEMP_C", "80")),
        host_warn_gpu_temp_c=float(g("HOST_WARN_GPU_TEMP_C", "82")),
        host_resume_gpu_temp_c=float(g("HOST_RESUME_GPU_TEMP_C", "78")),
        host_critical_gpu_temp_c=float(g("HOST_CRITICAL_GPU_TEMP_C", "87")),
        host_monitor_interval_s=float(g("HOST_MONITOR_INTERVAL_S", "30")),
        host_max_cooldown_s=float(g("HOST_MAX_COOLDOWN_S", "600")),
    )
