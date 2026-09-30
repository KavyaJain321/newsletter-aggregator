"""Apply the is_issue classifier to already-captured messages (offline).

Reads each stored clean text, re-classifies, updates is_issue + issue_reason.
Reports what got dropped as junk. Raw .eml is kept regardless.

Run: python scripts/reclassify.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, db
from src.classify import classify

conn = db.connect()
try:
    conn.execute("ALTER TABLE messages ADD COLUMN issue_reason TEXT")
except Exception:
    pass

rows = conn.execute("SELECT gmail_id, newsletter, subject, sender_name, clean_text_path FROM messages").fetchall()
dropped = []
for r in rows:
    body = (config.ROOT / r["clean_text_path"]).read_text(encoding="utf-8").split("\n\n", 1)[-1]
    ok, reason = classify(r["subject"], r["sender_name"], body)
    conn.execute("UPDATE messages SET is_issue=?, issue_reason=? WHERE gmail_id=?",
                 (1 if ok else 0, reason, r["gmail_id"]))
    if not ok:
        dropped.append((r["newsletter"], reason))
conn.commit()

kept = conn.execute("SELECT COUNT(*) FROM messages WHERE is_issue=1").fetchone()[0]
src_all = conn.execute("SELECT COUNT(DISTINCT source_id) FROM messages").fetchone()[0]
src_real = conn.execute("SELECT COUNT(DISTINCT source_id) FROM messages WHERE is_issue=1").fetchone()[0]
print(f"messages: {len(rows)} -> kept {kept} real, dropped {len(dropped)} junk")
print(f"distinct sources: {src_all} -> {src_real} real")
print("dropped:")
for n, reason in sorted(dropped):
    print(f"  [{reason}] {n}")
