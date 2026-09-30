"""Fast breakdown for the QA pass: heuristic cards for every captured issue,
then upgrade one recent issue per segment to full LLM so each segment shows
real product quality. Avoids a 20-min all-LLM run under free-tier limits.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, db, llm, extract as E

config.load_env()
conn = db.connect()

# 1) heuristic breakdown for any issue with no cards (instant, no API)
msgs = [dict(r) for r in conn.execute("SELECT * FROM messages")]
made = 0
for m in msgs:
    if conn.execute("SELECT COUNT(*) FROM story_cards WHERE gmail_id=?", (m["gmail_id"],)).fetchone()[0]:
        continue
    text = (config.ROOT / m["clean_text_path"]).read_text(encoding="utf-8")
    db.replace_cards(conn, m["gmail_id"], E.heuristic_cards(m, text))
    made += 1
conn.commit()
print(f"heuristic backfill: {made} issues")

# 2) upgrade one recent issue per segment to LLM
client = llm.get_llm()
for seg in config.SEGMENTS:
    row = conn.execute(
        "SELECT * FROM messages WHERE segment=? ORDER BY internal_ts DESC LIMIT 1", (seg,)).fetchone()
    if not row:
        continue
    m = dict(row)
    text = (config.ROOT / m["clean_text_path"]).read_text(encoding="utf-8")
    cards = E.llm_cards(m, text, client)
    db.replace_cards(conn, m["gmail_id"], cards)
    conn.commit()
    print(f"  LLM upgrade {seg:9} {m['newsletter'][:20]:20} -> {len(cards)} cards "
          f"({cards[0]['extractor'] if cards else '-'})")
    time.sleep(2)
print("done")
