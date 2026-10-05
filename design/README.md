# design/ — issue design ("Twenty to One", working name)

The visual spec and send-ready samples for the pipeline's **render step** (`instruction.md` Step 10).
The samples are also the **style exemplars** for the compose step (Step 8).

**Readers never see which newsletters we read** (`instruction.md` rule 11). No newsletter names,
links, coverage counts or source lists appear in any issue; a unit test enforces it.

| File | What |
|---|---|
| `issues/*.json` | Complete sample issues in the compose contract (`pipeline/compose/schema.py`) |
| `build_email.py` | Renders them with the pipeline's own renderer (`pipeline/render/email.py`) |
| `export.py` | HTML → single continuous-page PDF via headless Edge/Chrome (needs Pillow) |
| `nl.css` | Original design tokens (reference; the email renderer inlines its own) |
| `samples/` | Built outputs of the Oct 5, 2026 issues |

```bash
.venv/Scripts/python design/build_email.py design/issues/tech_2026-10-05.json design/issues/finance_2026-10-05.json
```
| Output (`samples/`) | What |
|---|---|
| `<name>.email.html` | The email as sent: nested tables, every style inline, 640px, mobile stacking via one media query, MSO fixes, hidden preheader, under 102 KB (Tech 43 KB, Finance 52 KB) |
| `<name>.txt` | Plain-text alternative part |
| `<name>.html` / `.pdf` | Review page with the inbox row on top, and its single-page PDF |

ESP merge tags to fill at send time: `{{web_url}}`, `{{unsubscribe_url}}`, `{{preferences_url}}`,
`{{subscribe_url}}`, `{{feedback_url}}`, `{{postal_address}}`.

## Design system
- **Type:** Schibsted Grotesk (headlines, masthead) · Source Serif 4 (reading text) · IBM Plex Mono (numbers, labels)
- **Colour:** ink `#15181F`, paper `#E6E9EE`, card `#FFFFFF`, rule `#E3E6EB` · highlighter `#FFE45C` (only on "so what") · up `#0E8A5F` / down `#C8372D`
- **Edition accents:** Tech `#D4471F` (vermilion) · Markets `#0A6B4C` (market green)
- **Signature:** the **"So what"** highlight, the **"What we actually know"** ledger
  (confirmed / claimed / unclear), **splits** when reports disagree, **hype checks**, and the
  checked-numbers promise in "How we work".

## Components (map 1:1 to the issue JSON)
Masthead + meta line (read time · stories · no ads) · number of the day (primary-source credit) ·
"today" list · story (tag, read time, badges, headline, highlighted so-what, body, ledger, split,
read-more links to primary sources) · quick hits · markets table + movers (Markets) · the big picture ·
term of the day · retail flow · week ahead · try-this · builders list · career · morsels · poll ·
"How we work" · footer.

**Badges:** `Reported` (single-source/leaked) · `Reports differ` (conflict) · `Self-reported` (vendor claim) · `Paywalled`.

Every number in the samples was checked against the exact sentence in its source email (the
story inventories stay local, outside git).
