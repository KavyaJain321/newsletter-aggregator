#!/usr/bin/env python3
"""
SessionEnd hook: append a dated outline of this session's user requests to
PROJECT_CONTEXT.md (the team handoff doc). Reads the hook JSON from stdin,
parses the session transcript, extracts the human's prompts, and inserts a
concise auto-logged entry above the log marker.

Deterministic (no AI). Fails silently so it can never break session end.
Test:  SESSION_LOG_TARGET=/tmp/ctx.md  echo '{"transcript_path":"...","session_id":"abc","reason":"clear"}' | python3 scripts/session_log.py
"""
import sys, os, json, datetime
from pathlib import Path

MARKER = "<!-- Add the next session's summary above this line -->"
MAX_PROMPTS = 40
TRUNC = 140


def target_file() -> Path:
    override = os.environ.get("SESSION_LOG_TARGET")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "PROJECT_CONTEXT.md"


def extract_user_prompts(transcript_path: str):
    prompts = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "user":
                    continue
                msg = obj.get("message", {}) or {}
                content = msg.get("content")
                text = ""
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    parts = [p.get("text", "") for p in content
                             if isinstance(p, dict) and p.get("type") == "text"]
                    text = " ".join(parts)
                text = " ".join(text.split()).strip()
                if not text:
                    continue
                # skip injected / meta / tool-result / interruption noise
                low = text.lower()
                if text.startswith("<") or "system-reminder" in low:
                    continue
                if text.startswith("[Request interrupted") or low.startswith("caveat:"):
                    continue
                if len(text) > TRUNC:
                    text = text[:TRUNC].rstrip() + "…"
                prompts.append(text)
    except Exception:
        return []
    return prompts


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    transcript_path = data.get("transcript_path")
    session_id = str(data.get("session_id", "") or "")
    reason = str(data.get("reason", "") or "session end")
    if not transcript_path or not os.path.exists(transcript_path):
        return 0

    prompts = extract_user_prompts(transcript_path)
    if not prompts:
        return 0

    tgt = target_file()
    if not tgt.exists():
        return 0
    try:
        doc = tgt.read_text(encoding="utf-8")
    except Exception:
        return 0

    sid = session_id[:8] or "unknown"
    # dedup: don't log the same session twice
    if f"session:{sid}" in doc:
        return 0

    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"### [auto] Session {today} · session:{sid}",
             f"_Ended: {reason}. Auto-logged from transcript — {len(prompts)} request(s). "
             f"Ask Claude to write a fuller summary if this session mattered._"]
    for p in prompts[:MAX_PROMPTS]:
        lines.append(f"- {p}")
    if len(prompts) > MAX_PROMPTS:
        lines.append(f"- …and {len(prompts) - MAX_PROMPTS} more")
    entry = "\n".join(lines) + "\n\n"

    if MARKER in doc:
        doc = doc.replace(MARKER, entry + MARKER, 1)
    else:
        doc = doc.rstrip() + "\n\n" + entry
    try:
        tgt.write_text(doc, encoding="utf-8")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
