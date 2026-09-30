"""Command-line entry points.

  python -m src.cli whoami
  python -m src.cli capture --segment tech --window 2d
  python -m src.cli extract --segment tech --window 2d
  python -m src.cli cards   --segment tech [--limit 20]
  python -m src.cli stats
"""
from __future__ import annotations
import argparse
import json
import sys

from . import config, db, llm as llm_mod
from .capture import capture
from .extract import extract_segment
from .gmail_client import GmailClient


def _out(obj) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="newsletter-aggregator")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami")
    for name in ("capture", "extract"):
        s = sub.add_parser(name)
        s.add_argument("--segment", default="tech", help="segment key or 'all'")
        s.add_argument("--window", default="2d")
        s.add_argument("--latest", action="store_true",
                       help="capture only the newest issue per source (one per newsletter)")
    sc = sub.add_parser("cards")
    sc.add_argument("--segment", default="tech")
    sc.add_argument("--limit", type=int, default=30)
    g = sub.add_parser("generate")
    g.add_argument("--segment", default="tech")
    g.add_argument("--date", required=True, help="YYYY-MM-DD")
    g.add_argument("--template", default="tech")
    sub.add_parser("stats")
    a = p.parse_args(argv)

    if a.cmd == "whoami":
        who = GmailClient().whoami()
        _out({"gmail": who, "llm": llm_mod.get_llm().name, "llm_ready": llm_mod.available()})
    elif a.cmd == "capture":
        segs = list(config.SEGMENTS) if a.segment == "all" else [a.segment]
        res = [capture(s, a.window, latest_per_source=a.latest) for s in segs]
        _out(res if len(res) > 1 else res[0])
    elif a.cmd == "extract":
        segs = list(config.SEGMENTS) if a.segment == "all" else [a.segment]
        res = [extract_segment(s, a.window) for s in segs]
        _out(res if len(res) > 1 else res[0])
    elif a.cmd == "cards":
        conn = db.connect()
        rows = conn.execute(
            "SELECT c.seq, m.newsletter, c.headline, c.what, c.links_json, c.extractor "
            "FROM story_cards c JOIN messages m ON m.gmail_id=c.gmail_id "
            "WHERE c.segment=? ORDER BY m.newsletter, c.seq LIMIT ?",
            (a.segment, a.limit)).fetchall()
        _out([{"source": r["newsletter"], "headline": r["headline"],
               "what": r["what"][:140],
               "links": len(json.loads(r["links_json"])), "by": r["extractor"]}
              for r in rows])
    elif a.cmd == "generate":
        from .generate import generate
        _out(generate(a.segment, a.date, a.template))
    elif a.cmd == "stats":
        conn = db.connect()
        _out(db.counts(conn))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
