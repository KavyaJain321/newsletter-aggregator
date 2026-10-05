# design/ — approved issue design ("Twenty to One", working name)

The visual spec for the pipeline's **render step** (`instruction.md` Step 10). The two sample issues
were hand-built from real newsletter issues received Oct 1–2, 2026, and are the target layout and the
initial **style exemplars** for the compose step (Step 8).

| File | What |
|---|---|
| `nl.css` | Design tokens and components shared by both editions |
| `tech.src.html`, `finance.src.html` | Source of the two sample issues (with `[[STRIP:n:…]]` placeholders) |
| `build.py` | Expands coverage-strip placeholders and inlines the CSS → self-contained HTML |
| `export.py` | HTML → single continuous-page PDF via headless Edge/Chrome |
| `samples/` | Built HTML + PDF of both issues (Oct 2, 2026) |

Build and export:
```bash
cd design && python build.py tech.src.html finance.src.html
python export.py tech.html finance.html
```

## Design system
- **Type:** Schibsted Grotesk (headlines, masthead) · Source Serif 4 (reading text) · IBM Plex Mono (numbers, labels, counts)
- **Colour:** ink `#15181F`, paper `#E6E9EE`, card `#FFFFFF`, rule `#E3E6EB` · highlighter `#FFE45C` (only on "so what") · up `#0E8A5F` / down `#C8372D`
- **Edition accents:** Tech `#D4471F` (vermilion) · Finance `#0A6B4C` (market green)
- **Signature (updated 2026-10-05):** the coverage strip, roster legend and newsletter credits are
  **retired**: readers must never see which newsletters we read (instruction.md rule 11). The
  signature is now the **"So what"** highlight, the **"What we actually know"** ledger
  (confirmed / claimed / unclear), **splits** when reports disagree, **hype checks**, and a
  checked-numbers promise in "How we work". The Oct 2 samples below predate this decision.

## Components (map 1:1 to the issue JSON in `instruction.md` Step 8)
Masthead + meta line · roster legend · number of the day · "today" list · story (eyebrow tag, coverage
strip, read time, badges, headline, highlighted so-what, body, read-the-original links, source line) ·
**ledger** ("What we actually know": Confirmed / Claimed / Unclear) · **split** (2–3 sides) · quick hits ·
markets table + movers grid (Finance) · retail flow · take worth stealing · term of the day · calendar ·
try-this · builders list · morsels · poll · "How this issue was made" · footer.

**Badges:** `Reported` (single-source/leaked) · `Sources differ` (conflict) · `Self-reported` (vendor claim) · `Paywalled`.

## Send-ready samples (Oct 5, 2026): the real render step
`issues/*.json` are complete issues in the compose contract (`pipeline/compose/schema.py`, the
JSON the compose step must output). `build_email.py` renders them with the pipeline's own
renderer (`pipeline/render/email.py`):

```bash
.venv/Scripts/python design/build_email.py design/issues/tech_2026-10-05.json design/issues/finance_2026-10-05.json
```
| Output (`samples/`) | What |
|---|---|
| `<name>.email.html` | The email as sent: nested tables, every style inline, 640px, mobile stacking via one media query, MSO fixes, hidden preheader, under 102 KB (Tech 66 KB, Finance 87 KB) |
| `<name>.txt` | Plain-text alternative part |
| `<name>.html` / `.pdf` | Review page with the inbox row on top, and its single-page PDF |

ESP merge tags to fill at send time: `{{web_url}}`, `{{unsubscribe_url}}`, `{{preferences_url}}`,
`{{subscribe_url}}`, `{{feedback_url}}`, `{{postal_address}}`.

- **Tech, Monday Oct 5:** 13 issues from 7 newsletters, Friday 9:30 ET to early Monday.
- **Markets, Monday Oct 5 (week ahead):** 16 issues from 12 newsletters, covering Friday's close,
  the weekend reads and this week's calendar.
- Every number was checked against the exact sentence in the source email (story inventories
  are kept locally, outside git).

## Not yet email-safe (the Oct 2 samples only)
These samples use modern CSS (grid, flex, `color-mix`, `text-wrap`) that browsers and PDF render
but Gmail/Outlook don't. The production template must be **table-based with inlined CSS** (premailer),
keeping the same look — see `instruction.md` Step 10. Keep the email under 102 KB (Gmail clipping).
