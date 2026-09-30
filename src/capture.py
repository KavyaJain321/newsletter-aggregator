"""Step 1 — Capture -> Archive -> DB.

Pull every issue for a segment/window; save raw .eml (lossless) + clean .md,
and one row per message in SQLite. Idempotent on gmail_id: re-running adds
zero duplicates. Everything downstream can be re-derived from the .eml.
"""
from __future__ import annotations
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor

from . import config, db
from .classify import classify
from .clean import clean_text, extract_bodies, word_count
from .gmail_client import GmailClient, parse_headers, sender_parts


def _iso(ts: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))


def _paths(segment: str, day: str, slug: str, gid: str):
    d = config.ARCHIVE / segment / day
    d.mkdir(parents=True, exist_ok=True)
    stem = f"{slug}__{gid[:8]}"
    return d / f"{stem}.eml", d / f"{stem}.md"


def _latest_per_source(client: GmailClient, segment: str, ids: list[str]) -> list[str]:
    """Keep only the newest issue per distinct source (one per newsletter)."""
    def meta(gid):
        try:
            return gid, client.get_meta(gid)
        except Exception:
            return gid, None
    best: dict[str, tuple[str, int]] = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for gid, mt in ex.map(meta, ids):
            if not mt:
                continue
            name, _email, domain = sender_parts(mt["from"])
            src = config.identify_source(segment, domain, name)
            if src not in best or mt["ts"] > best[src][1]:
                best[src] = (gid, mt["ts"])
    return [gid for gid, _ in best.values()]


def capture(segment: str, window: str = "2d", latest_per_source: bool = False,
            client: GmailClient | None = None) -> dict:
    if segment not in config.SEGMENTS:
        raise ValueError(f"unknown segment '{segment}'")
    client = client or GmailClient()
    conn = db.connect()
    ids = client.list_segment(segment, window)
    if latest_per_source:
        ids = _latest_per_source(client, segment, ids[:120])   # newest first; bound cost
    new = dup = err = 0

    for gid in ids:
        if db.message_exists(conn, gid):
            dup += 1
            continue
        try:
            full = client.get_full(gid)
            raw = client.get_raw(gid)
        except Exception:
            err += 1                       # one rate-limited msg never kills the run
            continue
        hdr = parse_headers(full["payload"])
        name, email, domain = sender_parts(hdr.get("From", ""))
        source = config.identify_source(segment, domain, name)
        source_id = config.slugify(source)
        ts = int(full["internalDate"]) // 1000
        day = time.strftime("%Y-%m-%d", time.localtime(ts))

        tp, th = extract_bodies(full["payload"])
        text = clean_text(tp, th)
        eml_path, md_path = _paths(segment, day, source_id, gid)
        eml_path.write_bytes(raw)
        md_path.write_text(
            f"SOURCE: {source}\nDATE: {_iso(ts)}\nSUBJECT: {hdr.get('Subject','')}\n\n{text}",
            encoding="utf-8")

        wc = word_count(text)
        is_issue, reason = classify(hdr.get("Subject", ""), name, text)
        db.upsert_source(conn, source_id, source, segment, domain=domain)
        db.insert_message(conn, {
            "gmail_id": gid, "thread_id": full.get("threadId"), "segment": segment,
            "newsletter": source, "source_id": source_id,
            "sender_name": name, "sender_email": email,
            "subject": hdr.get("Subject", ""), "sent_date": _iso(ts), "internal_ts": ts,
            "is_issue": 1 if is_issue else 0, "issue_reason": reason,
            "labels": ",".join(full.get("labelIds", [])),
            "raw_eml_path": str(eml_path.relative_to(config.ROOT)),
            "clean_text_path": str(md_path.relative_to(config.ROOT)),
            "word_count": wc, "reading_minutes": round(wc / 200, 1),
            "content_hash": hashlib.sha256(text.encode()).hexdigest(),
            "ingested_at": _iso(int(time.time())), "enrich_status": "pending",
        })
        new += 1

    db.log_sync(conn, run_at=_iso(int(time.time())), segment=segment, window=window,
                scanned=len(ids), new_added=new, duplicates=dup,
                status="ok", notes=f"errors={err}")
    conn.commit()
    summary = {"segment": segment, "window": window, "scanned": len(ids),
               "new": new, "duplicates": dup, "errors": err, **db.counts(conn)}
    conn.close()
    return summary
