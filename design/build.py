# Build static, self-contained HTML from *.src.html:
#  - expands [[STRIP:n:1,2,5]] into coverage-strip markup (n squares, listed positions filled)
#  - inlines nl.css so the file stands alone
import re, sys, pathlib

here = pathlib.Path(__file__).parent
css = (here / "nl.css").read_text(encoding="utf-8")

def strip(m):
    n = int(m.group(1))
    on = {int(x) for x in m.group(2).split(",") if x.strip()}
    cells = "".join('<i class="on"></i>' if i in on else "<i></i>" for i in range(1, n + 1))
    return f'<span class="strip" aria-label="Covered by {len(on)} of {n}">{cells}</span>'

for src in sys.argv[1:]:
    p = here / src
    html = p.read_text(encoding="utf-8")
    html = re.sub(r"\[\[STRIP:(\d+):([\d,]+)\]\]", strip, html)
    html = html.replace('<link rel="stylesheet" href="nl.css">', f"<style>\n{css}\n</style>")
    out = here / src.replace(".src.html", ".html")
    out.write_text(html, encoding="utf-8")
    left = re.findall(r"\[\[STRIP[^\]]*\]\]", html)
    print("built", out.name, "| unexpanded placeholders:", len(left))
