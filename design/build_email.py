# Build send-ready sample issues from design/issues/*.json with the pipeline's real renderer.
#   .venv/Scripts/python design/build_email.py design/issues/finance_2026-10-05.json [...]
# Writes to design/samples/:
#   <name>.email.html   the email exactly as sent (tables + inline styles, ESP merge tags)
#   <name>.txt          plain-text alternative part
#   <name>.html / .pdf  review page (inbox preview on top) and its single-page PDF
import json
import pathlib
import sys

here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent))
from pipeline.compose.schema import Issue  # noqa: E402
from pipeline.render.email import check_size, render_html, render_text  # noqa: E402

import export  # noqa: E402  (design/export.py)

out = here / "samples"
out.mkdir(exist_ok=True)
for arg in sys.argv[1:]:
    src = pathlib.Path(arg)
    issue = Issue.model_validate(json.loads(src.read_text(encoding="utf-8")))
    email = render_html(issue)
    size = check_size(email)
    (out / f"{src.stem}.email.html").write_text(email, encoding="utf-8")
    (out / f"{src.stem}.txt").write_text(render_text(issue), encoding="utf-8")
    page = out / f"{src.stem}.html"
    page.write_text(render_html(issue, preview=True), encoding="utf-8")
    print(f"{src.stem}: email {size / 1024:.1f} KB (Gmail limit 102 KB)")
    export.export(page)
