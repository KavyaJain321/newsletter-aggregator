"""Scrape viewer: the collected clean text for ALL sources, one per newsletter,
grouped by segment, collapsible. Pure collection view (no breakdown) so you can
judge whether the scraping itself is clean.

Run: python scripts/scrape_view.py
"""
from __future__ import annotations
import html, re, sqlite3, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "index.db"
OUT = Path.home() / "Desktop" / "newsletter-demo-2026-09-09" / "6-SCRAPE-ALL.html"
esc = html.escape
SEG_ORDER = ["tech", "biz", "legal", "hr", "github", "indie", "satire", "smallcap", "news"]


def health(text: str) -> tuple[str, int]:
    wc = len(re.findall(r"\w+", text))
    if text.count("�") / max(1, len(text)) > 0.01:
        return "GARBLE", wc
    if wc < 40:
        return "SHORT", wc
    return "CLEAN", wc


def main() -> None:
    c = sqlite3.connect(str(DB)); c.row_factory = sqlite3.Row
    issues = c.execute("""SELECT * FROM messages m WHERE m.is_issue=1 AND internal_ts =
        (SELECT MAX(internal_ts) FROM messages WHERE source_id=m.source_id AND is_issue=1)
        GROUP BY source_id""").fetchall()
    by_seg: dict[str, list] = {}
    for m in issues:
        by_seg.setdefault(m["segment"], []).append(m)

    clr = {"CLEAN": "#3fb950", "SHORT": "#d0a215", "GARBLE": "#f0616d"}
    blocks, n_clean = [], 0
    for seg in SEG_ORDER:
        rows = sorted(by_seg.get(seg, []), key=lambda r: r["newsletter"].lower())
        if not rows:
            continue
        blocks.append(f"<h2>{esc(seg)} · {len(rows)} sources</h2>")
        for m in rows:
            text = (ROOT / m["clean_text_path"]).read_text(encoding="utf-8")
            v, wc = health(text)
            n_clean += v == "CLEAN"
            preview = esc(re.sub(r"\s+", " ", text[:160]))
            blocks.append(
                f"<details><summary><span class=vd style='color:{clr[v]}'>{v}</span> "
                f"<b>{esc(m['newsletter'])}</b> <span class=meta>· {esc(m['sent_date'][:16])} · {wc}w · "
                f"{esc(m['subject'][:60])}</span><div class=pv>{preview}…</div></summary>"
                f"<pre>{esc(text)}</pre></details>")

    css = """*{box-sizing:border-box}body{margin:0;background:#0e1116;color:#e6edf3;font:15px/1.55 -apple-system,Segoe UI,Roboto,sans-serif}
    @media(prefers-color-scheme:light){body{background:#f5f6f8;color:#1a1f26}details{background:#fff}pre{background:#f0f2f4!important}}
    .wrap{max-width:900px;margin:0 auto;padding:26px 18px 60px}h1{font-size:24px;margin:0 0 4px}
    .dek{color:#9aa7b4;margin:0 0 20px}h2{font-size:14px;text-transform:uppercase;letter-spacing:.08em;color:#f5c518;margin:26px 0 8px;border-bottom:1px solid #2a323c;padding-bottom:4px}
    details{border:1px solid #2a323c;border-radius:9px;margin:7px 0;padding:9px 12px;background:#161b22}
    summary{cursor:pointer;list-style:none}summary::-webkit-details-marker{display:none}
    .vd{font-weight:800;font-size:11px;margin-right:6px}.meta{color:#9aa7b4;font-size:13px}
    .pv{color:#8b949e;font-size:12.5px;margin-top:4px;padding-left:2px}
    details[open] .pv{display:none}
    pre{white-space:pre-wrap;word-break:break-word;font:12px/1.5 ui-monospace,Consolas,monospace;background:#0b0e13;border:1px solid #2a323c;border-radius:8px;padding:11px;margin:10px 0 2px;max-height:600px;overflow:auto}"""
    HTML = (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Scrape — all sources</title><style>{css}</style></head><body><div class=wrap>"
            f"<h1>📥 Scrape — collected text for all {len(issues)} sources</h1>"
            f"<p class=dek>{n_clean}/{len(issues)} clean. Click any row to expand the exact text we scraped &amp; stored. "
            f"Ads/footers/tracking already stripped.</p>{''.join(blocks)}</div></body></html>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HTML, encoding="utf-8")
    print(f"wrote {OUT} | {len(issues)} sources, {n_clean} clean")
    webbrowser.open(OUT.as_uri())


if __name__ == "__main__":
    main()
