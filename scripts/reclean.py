"""Re-clean all captured issues from their stored raw .eml (offline, no Gmail).

Use after improving the cleaner: re-derives clean text + word_count + hash from
the lossless .eml, in place. This is why we keep the raw email — reprocessing
never needs the network.

Run: python scripts/reclean.py
"""
from __future__ import annotations
import email, hashlib, sys
from email import policy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, db
from src.clean import clean_text, word_count


def bodies_from_eml(raw: bytes) -> tuple[str, str]:
    msg = email.message_from_bytes(raw, policy=policy.default)
    tp = th = ""
    for part in msg.walk():
        ct = part.get_content_type()
        if ct not in ("text/plain", "text/html"):
            continue
        try:
            payload = part.get_content()
        except Exception:
            continue
        if ct == "text/plain":
            tp += payload
        else:
            th += payload
    return tp, th


def main() -> None:
    conn = db.connect()
    rows = conn.execute("SELECT gmail_id, newsletter, clean_text_path, raw_eml_path FROM messages").fetchall()
    changed = fixed = 0
    for r in rows:
        eml = config.ROOT / r["raw_eml_path"]
        md = config.ROOT / r["clean_text_path"]
        tp, th = bodies_from_eml(eml.read_bytes())
        text = clean_text(tp, th)
        wc = word_count(text)
        header = md.read_text(encoding="utf-8").split("\n\n", 1)[0]
        md.write_text(f"{header}\n\n{text}", encoding="utf-8")
        old_wc = conn.execute("SELECT word_count FROM messages WHERE gmail_id=?", (r["gmail_id"],)).fetchone()[0]
        conn.execute("UPDATE messages SET word_count=?, content_hash=? WHERE gmail_id=?",
                     (wc, hashlib.sha256(text.encode()).hexdigest(), r["gmail_id"]))
        if wc != old_wc:
            changed += 1
            if old_wc < 40 <= wc:
                fixed += 1
                print(f"  FIXED {r['newsletter']}: {old_wc} -> {wc} words")
    conn.commit()
    conn.close()
    print(f"re-cleaned {len(rows)} issues; {changed} changed; {fixed} short->healthy")


if __name__ == "__main__":
    main()
