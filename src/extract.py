"""Step 2 — MAP: each issue -> structured story cards.

Deterministic part (always): split into stories, drop ad/section blocks, and
extract links straight from the source text (never invented).
Semantic part: an LLM fills headline/what/why. Without an API key the MockLLM
triggers a heuristic fallback so this stage still runs and is inspectable.
"""
from __future__ import annotations
import json
import re
import time

from . import config, db, llm as llm_mod
from .clean import AD_MARKERS

PROMPT_VERSION = "map_v1"

# Category/section dividers that are NOT stories themselves.
SECTION_LABELS = {
    "quick links", "miscellaneous", "big tech & startups", "around the horn",
    "science & futuristic technology", "programming, design & data science",
    "treats to try", "midweek wisdom", "in the know", "productivity", "tutorial",
    "extras", "today in ai", "from the frontier", "a cat's commentary", "want more?",
    "ai skill of the day", "meme multiverse", "in partnership", "presented",
}
_HEADING = re.compile(r"^\s*(#{1,4}\s+|\*{0,2}\d+\.\s+\*\*|\[?\*{0,2}[A-Z0-9][A-Z0-9 &'’,\-\(\)/]{10,79}$)")
_URL = re.compile(r"https?://[^\s)\]>]+")
# a heading line that is ITSELF a markdown link -> almost always a CTA/ad slot
_MDLINK_HEAD = re.compile(r"^\s*\[[^\]]+\]\((?:\[link\]|https?://)[^)]*\)\s*$")
_MDLINK = re.compile(r"\[([^\]]+)\]\((?:\[link\]|https?://)[^)]*\)")
# ad / sponsor signals beyond the FROM-OUR-PARTNERS markers in clean.AD_MARKERS
_AD = re.compile(
    r"register now|save your (spot|seat)|book a demo|request a demo|"
    r"get your free|download the|start (your )?free|try it free|"
    r"buysellads|/ads/|\?cid=|ref\.[a-z]|subscribe to unlock", re.I)


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith(("View image", "Follow image", "Caption", "*Asterisk")):
        return False
    return bool(_HEADING.match(s))


def _clean_heading(line: str) -> str:
    s = _MDLINK.sub(r"\1", line)                       # [text](url) -> text
    s = re.sub(r"^\s*(#{1,4}\s+|\*+\s*\d+\.\s*\*+|\*+)", "", s)
    return s.strip().strip("*[]").strip()


def split_stories(text: str) -> list[dict]:
    """Deterministic segmentation into {heading, body} story chunks."""
    lines = text.splitlines()
    chunks, cur = [], None
    for ln in lines:
        if _is_heading(ln):
            if cur:
                chunks.append(cur)
            cur = {"raw": ln.strip(), "body": []}
        elif cur is not None:
            cur["body"].append(ln)
    if cur:
        chunks.append(cur)

    stories = []
    for c in chunks:
        body = "\n".join(c["body"]).strip()
        head = _clean_heading(c["raw"])
        raw_nohash = re.sub(r"^\s*#{1,4}\s*", "", c["raw"])   # drop md '##' prefix
        norm = re.sub(r"^[^A-Za-z]+", "", head).lower()       # drop leading emoji
        blob = f"{c['raw']}\n{head}\n{body[:250]}"
        if _MDLINK_HEAD.match(raw_nohash):           # heading is a bare link = ad slot
            continue
        if norm in SECTION_LABELS or any(norm.startswith(s) for s in SECTION_LABELS):
            continue
        if AD_MARKERS.search(blob) or _AD.search(blob):
            continue
        if len(re.findall(r"\w+", body)) < 20:       # too thin to be a story
            continue
        stories.append({"heading": head, "body": body})
    return stories


def _links_in(text: str) -> list[dict]:
    seen, out = set(), []
    for u in _URL.findall(text):
        u = u.rstrip(").,")
        if "utm_" not in u and u not in seen and "[link]" not in u:
            seen.add(u)
            out.append({"anchor": "", "url": u})
    return out


def _first_sentences(body: str, n: int = 2) -> str:
    flat = re.sub(r"\s+", " ", re.sub(r"https?://\S+", "", body)).strip()
    parts = re.split(r"(?<=[.!?])\s+", flat)
    return " ".join(parts[:n])[:400]


def heuristic_cards(msg: dict, text: str) -> list[dict]:
    cards = []
    for i, s in enumerate(split_stories(text)):
        cards.append(_card(msg, i, s["heading"], _first_sentences(s["body"]),
                           "", [], _links_in(s["body"]), extractor="heuristic"))
    return cards


def llm_cards(msg: dict, text: str, client) -> list[dict]:
    system = (config.PROMPTS / "map_v1.txt").read_text(encoding="utf-8")
    try:
        res = client.complete(system, text[:14000], prompt_version=PROMPT_VERSION,
                              input_ids=[msg["gmail_id"]],
                              model=config.llm_settings()["map_model"])
    except Exception:
        return heuristic_cards(msg, text)   # rate-limit/outage -> graceful degrade
    if res.text.strip() == "[MOCK]" or not res.text.strip():
        return heuristic_cards(msg, text)
    # strip reasoning-model noise (<think> blocks, ```json fences) before parsing
    cleaned = re.sub(r"<think>.*?</think>", "", res.text, flags=re.S)
    cleaned = cleaned.replace("```json", "").replace("```", "")
    m = re.search(r"\[.*\]", cleaned, re.S)
    if not m:
        return heuristic_cards(msg, text)
    try:
        raw = json.loads(m.group(0))
    except Exception:
        return heuristic_cards(msg, text)   # never crash on bad JSON; fall back
    source_urls = {l["url"] for l in _links_in(text)}
    cards = []
    for i, it in enumerate(raw):
        # keep only links that actually exist in the source (no hallucinations)
        links = [{"anchor": "", "url": u} for u in it.get("links", []) if u in source_urls]
        cards.append(_card(msg, i, it.get("headline", ""), it.get("what", ""),
                           it.get("why", ""), it.get("facts", []), links,
                           extractor=f"llm:{res.meta['model']}"))
    # drop empty/degenerate cards (a model can return well-formed-but-empty JSON)
    cards = [c for c in cards if len(re.findall(r"\w+", c["headline"])) >= 2]
    return cards or heuristic_cards(msg, text)


def _card(msg, seq, headline, what, why, facts, links, extractor) -> dict:
    return {
        "card_id": f"{msg['gmail_id'][:8]}-{seq}", "gmail_id": msg["gmail_id"],
        "source_id": msg["source_id"], "segment": msg["segment"], "seq": seq,
        "headline": headline[:200], "what": what, "why": why,
        "facts_json": json.dumps(facts, ensure_ascii=False),
        "links_json": json.dumps(links, ensure_ascii=False),
        "extractor": extractor, "prompt_version": PROMPT_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def extract_segment(segment: str, window: str = "2d") -> dict:
    conn = db.connect()
    client = llm_mod.get_llm()
    rows = conn.execute(
        "SELECT * FROM messages WHERE segment=? AND internal_ts >= ?",
        (segment, int(time.time()) - _window_seconds(window)),
    ).fetchall()
    total_cards, per = 0, []
    paced = client.name != "mock"
    for i, r in enumerate(rows):
        msg = dict(r)
        text = (config.ROOT / msg["clean_text_path"]).read_text(encoding="utf-8")
        cards = llm_cards(msg, text, client)
        db.replace_cards(conn, msg["gmail_id"], cards)
        total_cards += len(cards)
        per.append({"source": msg["newsletter"], "subject": msg["subject"][:48],
                    "cards": len(cards), "by": cards[0]["extractor"].split(":")[0] if cards else "-"})
        if paced and i < len(rows) - 1:
            time.sleep(1.5)                 # stay under free-tier RPM
    conn.commit()
    conn.close()
    return {"segment": segment, "issues": len(rows), "cards": total_cards,
            "engine": client.name, "per_issue": per}


def _window_seconds(window: str) -> int:
    m = re.match(r"(\d+)([dh])", window)
    if not m:
        return 2 * 86400
    n, unit = int(m.group(1)), m.group(2)
    return n * (86400 if unit == "d" else 3600)
