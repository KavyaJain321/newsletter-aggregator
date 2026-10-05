import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.compose.schema import Issue
from pipeline.render.email import MAX_BYTES, check_size, render_html, render_text

SAMPLES = sorted((Path(__file__).resolve().parents[2] / "design" / "issues").glob("*.json"))


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: p.stem)
def test_sample_issues_validate_and_render_send_ready(path):
    issue = Issue.model_validate(_load(path))
    html = render_html(issue)
    assert check_size(html) < MAX_BYTES                      # Gmail clips above ~102 KB
    for tag in ("{{unsubscribe_url}}", "{{preferences_url}}", "{{postal_address}}", "{{web_url}}"):
        assert tag in html                                    # ESP fills these at send time
    assert issue.preheader[:30] in html and "display:none" in html
    assert "<link" in html and re.search(r"@media \(max-width:620px\)", html)
    for banned in ("display:grid", "display:flex", "var(--", "color-mix"):   # not email-safe
        assert banned not in html
    text = render_text(issue)
    assert issue.number_of_day.value in text and "{{unsubscribe_url}}" in text
    for block in issue.blocks:
        if hasattr(block, "headline"):
            assert block.headline.replace("**", "") in text


def test_samples_exist():
    assert {p.stem.split("_")[0] for p in SAMPLES} == {"tech", "finance"}


def test_coverage_must_come_from_the_roster():
    d = _load(SAMPLES[0])
    d["blocks"][1] = {**d["blocks"][1], "coverage": ["not_a_brand"]}
    with pytest.raises(ValidationError, match="not in this issue's roster"):
        Issue.model_validate(d)


def test_unknown_fields_are_rejected():
    d = _load(SAMPLES[0])
    d["blocks"][1] = {**d["blocks"][1], "html": "<script>"}
    with pytest.raises(ValidationError):
        Issue.model_validate(d)


def test_text_is_escaped_and_only_bold_survives():
    d = _load(SAMPLES[0])
    d["today"][0] = "<script>alert(1)</script> **bold** & more"
    html = render_html(Issue.model_validate(d))
    assert "<script>alert" not in html and "&lt;script&gt;" in html
    assert "<b>bold</b> &amp; more" in html


def _brand_words():
    from pipeline.config.registry import load_registry
    reg = load_registry()
    return sorted({b.label for b in reg.brands.values()} | {"newsletter", "newsletters"}, key=len, reverse=True)


@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: p.stem)
def test_readers_never_see_which_newsletters_we_read(path):
    """Owner decision 2026-10-05: no source newsletter names, links, coverage counts or rosters."""
    issue = Issue.model_validate(_load(path))
    out = render_html(issue) + render_text(issue) + render_html(issue, preview=True)
    leaked = [w for w in _brand_words() if re.search(r"\b" + re.escape(w) + r"\b", out, flags=re.I)]
    assert leaked == []
    for r in issue.roster:
        if r.url:
            assert str(r.url).rstrip("/") not in out
    assert not re.search(r"\d+ of \d+", out)            # no "5 of 12" coverage counts


def test_provenance_fields_are_never_rendered():
    d = _load(SAMPLES[0])
    d["blocks"][1]["sources"] = [{"name": "SECRET-SOURCE-NAME"}]
    d["number_of_day"]["via"] = "SECRET-VIA"
    out = render_html(Issue.model_validate(d))
    assert "SECRET-SOURCE-NAME" not in out and "SECRET-VIA" not in out


def test_oversized_email_is_refused():
    with pytest.raises(ValueError, match="Gmail clips"):
        check_size("x" * (MAX_BYTES + 1))


def test_preview_adds_inbox_row_only_in_preview():
    issue = Issue.model_validate(_load(SAMPLES[0]))
    assert "How it lands in your inbox" in render_html(issue, preview=True)
    assert "How it lands in your inbox" not in render_html(issue)
