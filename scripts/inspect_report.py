"""QA + Data Inspector report across ALL captured newsletters.

For every source, picks its most-recent captured issue and renders:
 - what we COLLECTED (cleaned text)  vs  the STORY CARDS we broke it into
 - automated QA flags (gibberish / ad-leak / empty / low-fact / heuristic)
 - a top summary table with a per-source verdict.

Run:  python scripts/inspect_report.py  ->  writes an HTML report + opens it.
"""
from __future__ import annotations
import json, html, re, sqlite3, sys, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "index.db"
OUT = Path.home() / "Desktop" / "newsletter-demo-2026-09-09" / "5-QA-ALL-SOURCES.html"
esc = html.escape

AD = re.compile(r"sponsor|presented by|from our partners|register now|save your (seat|spot)|"
                r"book a demo|buysellads|advertise|/ads/", re.I)
NOISE = re.compile(r"view image|follow image link|caption:|unsubscribe|\[link\]\(|\]\(http", re.I)


def qa_card(cd: dict) -> list[str]:
    flags = []
    h, w = cd["headline"] or "", cd["what"] or ""
    facts = json.loads(cd["facts_json"])
    if len(h.strip()) < 4:
        flags.append("empty-headline")
    if h.startswith(("http", "[")) or "](" in h or "[link]" in h:
        flags.append("gibberish-headline")
    if "�" in h + w:
        flags.append("encoding-garble")
    if NOISE.search(h + " " + w):
        flags.append("render-noise")
    if AD.search(h + " " + w):
        flags.append("ad-leak")
    if cd["extractor"].startswith("heuristic"):
        flags.append("heuristic")
    if not w.strip() and not facts:
        flags.append("thin")
    return flags


def scrape_health(text: str) -> tuple[str, str]:
    wc = len(re.findall(r"\w+", text))
    garble = text.count("�") / max(1, len(text))
    if garble > 0.01:
        return "GARBLE", f"encoding issues ({wc}w)"
    if wc < 40:
        return "SHORT", f"only {wc} words (teaser?)"
    return "CLEAN", f"{wc} words, readable"


def verdict(cards: list[dict]) -> tuple[str, str]:
    if not cards:
        return "EMPTY", "breakdown empty — heuristic couldn't parse this format (LLM needed)"
    bad = sum(1 for c in cards if set(qa_card(c)) & {"gibberish-headline", "ad-leak",
              "render-noise", "encoding-garble", "empty-headline"})
    llm = sum(1 for c in cards if c["extractor"].startswith("llm"))
    ratio = bad / len(cards)
    if ratio == 0 and llm:
        return "CLEAN", f"{len(cards)} cards, all LLM, 0 issues"
    if ratio <= 0.2:
        return "OK", f"{len(cards)} cards, {bad} minor flag(s), {'LLM' if llm else 'heuristic'}"
    return "REVIEW", f"{len(cards)} cards, {bad} flagged ({int(ratio*100)}%)"


def main() -> None:
    c = sqlite3.connect(str(DB)); c.row_factory = sqlite3.Row
    # most-recent issue per source
    issues = c.execute("""
        SELECT * FROM messages m WHERE m.is_issue=1 AND internal_ts =
          (SELECT MAX(internal_ts) FROM messages WHERE source_id = m.source_id AND is_issue=1)
        GROUP BY source_id ORDER BY segment, newsletter""").fetchall()

    CLR = {"CLEAN": "#3fb950", "OK": "#d0a215", "REVIEW": "#f0616d", "EMPTY": "#8b949e",
           "SHORT": "#d0a215", "GARBLE": "#f0616d"}
    summ, sections = [], []
    for m in issues:
        cards = [dict(r) for r in c.execute(
            "SELECT * FROM story_cards WHERE gmail_id=? ORDER BY seq", (m["gmail_id"],))]
        text = (ROOT / m["clean_text_path"]).read_text(encoding="utf-8")
        sh, shnote = scrape_health(text)
        v, note = verdict(cards)
        vc = CLR[v]
        summ.append(f"<tr><td>{esc(m['segment'])}</td><td><b>{esc(m['newsletter'])}</b></td>"
                    f"<td class=n>{m['word_count']}</td>"
                    f"<td style='color:{CLR[sh]};font-weight:700'>{sh}</td>"
                    f"<td class=n>{len(cards)}</td>"
                    f"<td style='color:{vc};font-weight:700'>{v}</td><td class=note>{esc(note)}</td></tr>")

        ch = []
        for cd in cards:
            fl = qa_card(cd)
            facts = json.loads(cd["facts_json"]); links = json.loads(cd["links_json"])
            fli = "".join(f"<li>{esc(x)}</li>" for x in facts)
            flag = "".join(f"<span class=flag>{esc(f)}</span>" for f in fl)
            ch.append(f"<div class=card><div class=chd>{esc(cd['headline']) or '<i>(empty)</i>'}</div>"
                      + (f"<div class=cw>{esc(cd['what'])}</div>" if cd['what'] else "")
                      + (f"<ul class=cf>{fli}</ul>" if facts else "")
                      + f"<div class=cl>🔗 {len(links)} · {esc(cd['extractor'])} {flag}</div></div>")
        sections.append(f"""<section><div class=ih><span class=seg>{esc(m['segment'])}</span>
          <b>{esc(m['newsletter'])}</b> · {esc(m['sent_date'][:16])} · {m['word_count']} words → {len(cards)} stories
          <span class=v style='color:{vc}'>{v}</span><br><span class=sub>{esc(m['subject'])}</span></div>
          <div class=cols><div class=col><div class=lbl>① COLLECTED (clean text)</div>
          <pre class=raw>{esc(text)}</pre></div>
          <div class=col><div class=lbl>② STORY CARDS + QA</div>{''.join(ch) or '<i>no cards</i>'}</div></div></section>""")

    css = """*{box-sizing:border-box}body{margin:0;background:#0e1116;color:#e6edf3;font:15px/1.55 -apple-system,Segoe UI,Roboto,sans-serif}
    @media(prefers-color-scheme:light){body{background:#f5f6f8;color:#1a1f26}pre.raw{background:#fff!important}.card{background:#fff!important}section{background:#fff!important}table{background:#fff!important}}
    .wrap{max-width:1120px;margin:0 auto;padding:26px 18px 60px}h1{font-size:25px;margin:0 0 4px}.dek{color:#9aa7b4;margin:0 0 18px}
    table{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:26px}th,td{border-bottom:1px solid #2a323c;padding:7px 8px;text-align:left}
    th{color:#9aa7b4;font-size:11px;text-transform:uppercase;letter-spacing:.06em}td.n{text-align:center;color:#9aa7b4}td.note{color:#9aa7b4;font-size:12px}
    section{border:1px solid #2a323c;border-radius:12px;padding:15px;margin:14px 0}.ih{margin-bottom:10px}.sub{color:#9aa7b4}.v{font-weight:800;margin-left:8px}
    .seg{font-size:11px;background:#21262d;color:#9aa7b4;padding:1px 7px;border-radius:20px;margin-right:6px}
    .cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:800px){.cols{grid-template-columns:1fr}}
    .lbl{font-size:11px;font-weight:700;color:#f5c518;margin-bottom:6px;letter-spacing:.05em}
    pre.raw{white-space:pre-wrap;word-break:break-word;font:12px/1.5 ui-monospace,Consolas,monospace;background:#0b0e13;border:1px solid #2a323c;border-radius:8px;padding:10px;max-height:480px;overflow:auto;margin:0}
    .card{border:1px solid #2a323c;border-radius:8px;padding:9px 11px;margin-bottom:8px}.chd{font-weight:700;color:#5eb1ff}.cw{margin:4px 0;font-size:13.5px}
    .cf{margin:5px 0;padding-left:17px;font-size:12.5px;color:#3fb950}.cl{font-size:11.5px;color:#9aa7b4}
    .flag{display:inline-block;background:#3d1418;color:#f0616d;border-radius:20px;padding:0 7px;margin-left:5px;font-size:10.5px;font-weight:700}"""

    clean = sum(1 for s in summ if ">CLEAN<" in s); rev = sum(1 for s in summ if ">REVIEW<" in s)
    HTML = (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>QA — all sources</title><style>{css}</style></head><body><div class=wrap>"
            f"<h1>🔬 QA — every newsletter, collected & broken into stories</h1>"
            f"<p class=dek>{len(issues)} sources. <b>SCRAPE</b> = is the collected text clean (the real question). "
            f"<b>BREAKDOWN</b> = did we split it into story cards (EMPTY = offline heuristic can't parse that format; the LLM can). "
            f"Left column = exactly what we scraped.</p>"
            f"<table><tr><th>Segment</th><th>Newsletter</th><th>Words</th><th>Scrape</th><th>Stories</th><th>Breakdown</th><th>Note</th></tr>{''.join(summ)}</table>"
            f"{''.join(sections)}</div></body></html>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HTML, encoding="utf-8")
    print(f"wrote {OUT} | sources: {len(issues)} | CLEAN {clean} | REVIEW {rev}")
    webbrowser.open(OUT.as_uri())


if __name__ == "__main__":
    main()
