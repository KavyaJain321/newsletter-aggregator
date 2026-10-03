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
- **Signature:** the **coverage strip** — one square per newsletter in the edition's roster, filled when that newsletter covered the story, plus "N of M". It encodes the product's core idea; keep it on every story.

## Components (map 1:1 to the issue JSON in `instruction.md` Step 8)
Masthead + meta line · roster legend · number of the day · "today" list · story (eyebrow tag, coverage
strip, read time, badges, headline, highlighted so-what, body, read-the-original links, source line) ·
**ledger** ("What we actually know": Confirmed / Claimed / Unclear) · **split** (2–3 sides) · quick hits ·
markets table + movers grid (Finance) · retail flow · take worth stealing · term of the day · calendar ·
try-this · builders list · morsels · poll · "How this issue was made" · footer.

**Badges:** `Reported` (single-source/leaked) · `Sources differ` (conflict) · `Self-reported` (vendor claim) · `Paywalled`.

## Not yet email-safe
These samples use modern CSS (grid, flex, `color-mix`, `text-wrap`) that browsers and PDF render
but Gmail/Outlook don't. The production template must be **table-based with inlined CSS** (premailer),
keeping the same look — see `instruction.md` Step 10. Keep the email under 102 KB (Gmail clipping).
