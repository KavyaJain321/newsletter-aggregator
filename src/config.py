"""Central config: paths, segments, sender identity, and env-loaded settings.

No secrets live here. Real secrets come from `.env` (gitignored) or the
existing Gmail OAuth store at ~/.gmail-mcp/ (also gitignored).
"""
from __future__ import annotations
import os
import re
from pathlib import Path

# ---- Paths -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ARCHIVE = DATA / "archive"
DB_PATH = DATA / "index.db"
LOGS = ROOT / "logs"
PROMPTS = ROOT / "prompts"
GENERATED = ROOT / "generated"

GMAIL_DIR = Path(os.path.expanduser("~")) / ".gmail-mcp"
GMAIL_CREDS = GMAIL_DIR / "credentials.json"      # refresh/access token
GMAIL_OAUTH = GMAIL_DIR / "gcp-oauth.keys.json"   # OAuth client

for _p in (DATA, ARCHIVE, LOGS, PROMPTS, GENERATED):
    _p.mkdir(parents=True, exist_ok=True)

# ---- Segments (tag = the +plus-address; label = folder name) ---------------
SEGMENTS = {
    "tech":     {"tag": "techai",   "label": "1-TechAI"},
    "biz":      {"tag": "biz",      "label": "2-BizFinance"},
    "legal":    {"tag": "legal",    "label": "3-Legal"},
    "hr":       {"tag": "hr",       "label": "4-HRPeopleOps"},
    "github":   {"tag": "github",   "label": "5-GitHubRepos"},
    "indie":    {"tag": "indie",    "label": "6-IndieHacker"},
    "satire":   {"tag": "satire",   "label": "7-Absurdist"},
    "smallcap": {"tag": "smallcap", "label": "8-MicroSmallCap"},
    "news":     {"tag": "news",     "label": "9-MainstreamNews"},
}

# Plain-addressed sources (rejected +tag) — matched by sender, per segment.
PLAIN_SENDERS = {
    "biz":    ["from:morningbrew.com -hrbrew -hr-brew"],
    "legal":  ["from:findlaw.com OR from:newsletters.findlaw.com"],
    "hr":     ["from:hrbrew@morningbrew.com OR from:hr-brew.com"],
    "satire": ["from:babylonbee.com"],
}

# Sender-domain -> canonical source name, scoped by segment where a domain is
# shared (e.g. tldrnewsletter.com is "TLDR" in tech, "TLDR WebDev" in github).
# Verified live 2026-09-09 (incl. the tricky ones the first pass got wrong).
SOURCE_BY_SEGMENT_DOMAIN = {
    "tech": {
        "tldrnewsletter.com": "TLDR",
        "joinsuperhuman.ai": "Superhuman AI",
        "theneurondaily.com": "The Neuron",
        "pragmaticengineer.com": "The Pragmatic Engineer",
        "importai.substack.com": "Import AI",
    },
    "github": {
        "tldrnewsletter.com": "TLDR WebDev",
        "changelog.com": "Changelog Nightly",
        "console.dev": "Console Weekly",
        "bytes.dev": "Bytes (ui.dev)",
        "ui.dev": "Bytes (ui.dev)",
        "buttondown.email": "DevOps'ish",
        "devopsish.com": "DevOps'ish",
    },
    "biz": {
        "morningbrew.com": "Morning Brew",
        "thehustle.co": "The Hustle",
        "thedailyupside.com": "The Daily Upside",
        "readthejoe.com": "The Average Joe",
        "ghost.io": "The Diff",
    },
}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def identify_source(segment: str, from_domain: str, from_name: str) -> str:
    """Best-effort canonical source name from sender domain (fallback: name)."""
    table = SOURCE_BY_SEGMENT_DOMAIN.get(segment, {})
    dom = (from_domain or "").lower()
    for key, name in table.items():
        if key in dom:
            return name
    return from_name.strip() or dom or "Unknown"


# ---- LLM settings (env-driven; provider-agnostic) --------------------------
def load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader (no dependency). Silently no-ops if absent."""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


def llm_settings() -> dict:
    load_env()
    key = os.environ.get("LLM_API_KEY") or os.environ.get("GROQ_API_KEY", "")
    return {
        "api_key": key,
        "base_url": os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
        "model": os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"),
        "map_model": os.environ.get("LLM_MAP_MODEL", "llama-3.1-8b-instant"),
        "reasoning_effort": os.environ.get("LLM_REASONING_EFFORT") or None,
        "no_think": bool(os.environ.get("LLM_NOTHINK")),
    }
