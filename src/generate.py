"""Step 3 — Generate: a day's story cards -> our newsletter.

Reduce step: gather all cards for one segment+day (already extracted by the
MAP step), hand them to the LLM with the segment's editorial template, and
get back the finished newsletter. Merging/dedup/selection happen inside that
call (the cards are the compact, judgment-friendly input — not raw email).
"""
from __future__ import annotations
import json
import re

from . import config, db, llm as L


def _cut(s: str, n: int) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[:n] + "…"


def load_day_cards(conn, segment: str, date: str) -> list[dict]:
    """Compact, deduped-per-issue card list for a segment on a given day."""
    rows = conn.execute(
        "SELECT c.headline,c.what,c.why,c.facts_json,c.links_json,m.newsletter "
        "FROM story_cards c JOIN messages m ON m.gmail_id=c.gmail_id "
        "WHERE c.segment=? AND m.is_issue=1 AND m.sent_date LIKE ? "
        "ORDER BY m.newsletter, c.seq", (segment, date + "%")).fetchall()
    cards = []
    for r in rows:
        facts = json.loads(r["facts_json"] or "[]")
        links = [l.get("url", "") for l in json.loads(r["links_json"] or "[]") if l.get("url")]
        head = _cut(r["headline"], 110)
        what = _cut(r["what"], 200)
        if len(re.findall(r"\w+", head + what)) < 4:
            continue                                  # skip empty/degenerate cards
        cards.append({
            "source": r["newsletter"], "headline": head, "what": what,
            "why": _cut(r["why"], 140), "facts": facts[:3],
            "link": links[0] if links else "",
        })
    return cards


def generate(segment: str, date: str, template: str = "tech") -> dict:
    conn = db.connect()
    cards = load_day_cards(conn, segment, date)
    if not cards:
        conn.close()
        raise SystemExit(f"no cards for {segment} on {date} — capture+extract that day first")
    sources = sorted({c["source"] for c in cards})
    sys_prompt = (config.PROMPTS / f"generate_{template}.txt").read_text(encoding="utf-8")
    payload = json.dumps({"date": date, "sources": sources, "cards": cards}, ensure_ascii=False)

    client = L.get_llm()
    res = client.complete(sys_prompt, payload, prompt_version=f"gen_{template}_v1",
                          input_ids=[f"{segment}:{date}"], temperature=0.4)
    md = res.text.strip()
    md = re.sub(r"^```(?:markdown|md)?\s*", "", md)
    md = re.sub(r"\s*```$", "", md)

    config.GENERATED.mkdir(parents=True, exist_ok=True)
    out = config.GENERATED / f"{date}-{segment}-OURS.md"
    out.write_text(md, encoding="utf-8")
    conn.close()
    return {"segment": segment, "date": date, "template": template,
            "sources": sources, "cards_in": len(cards),
            "out": str(out.relative_to(config.ROOT)), "chars": len(md),
            "engine": client.name, "model": config.llm_settings()["model"]}
