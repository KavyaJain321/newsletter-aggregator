import copy

import pytest
import yaml

from pipeline.config.registry import Registry, load_registry
from pipeline.config.settings import CONFIG_DIR


@pytest.fixture(scope="module")
def reg() -> Registry:
    return load_registry()


def _raw():
    s = yaml.safe_load((CONFIG_DIR / "sources.yaml").read_text(encoding="utf-8"))
    e = yaml.safe_load((CONFIG_DIR / "editions.yaml").read_text(encoding="utf-8"))
    return s, e


def _build(s, e) -> Registry:
    return Registry(timezone=e["timezone"], brands=s["brands"], sources=s["sources"], editions=e["editions"])


def test_real_config_loads(reg):
    assert set(reg.editions) == {"tech", "finance"}
    assert len(reg.sources_for("tech")) >= 10
    assert len(reg.sources_for("finance")) >= 10


@pytest.mark.parametrize("header,expected,series", [
    ("TLDR <dan@tldrnewsletter.com>", "tldr", None),
    ("TLDR Dev <dan@tldrnewsletter.com>", "tldr_dev", None),
    ("Matt Levine <noreply@news.bloomberg.com>", "money_stuff", None),
    ("Bloomberg Businessweek <noreply@news.bloomberg.com>", "businessweek_daily", None),
    ("The Pragmatic Engineer <pragmaticengineer+deepdives@substack.com>", "pragmatic_engineer", "deepdive"),
    ("The Pragmatic Engineer <pragmaticengineer+the-pulse@substack.com>", "pragmatic_engineer", "pulse"),
    ("The Pragmatic Engineer <pragmaticengineer@substack.com>", "pragmatic_engineer", "podcast"),
    ('"Azeem Azhar, Exponential View" <exponentialview@substack.com>', "exponential_view", None),
    ("Finks <joe@readthejoe.com>", "finks_daily", None),
    ("The Average Joe (Finks) <joe@readthejoe.com>", "finks_daily", None),
    ("Semafor DC <washingtondc@semafor.com>", "semafor_dc", None),
    ("Superhuman – Zain Kahn <SUPERHUMAN@mail.joinsuperhuman.ai>", "superhuman", None),
])
def test_match_sender_real_headers(reg, header, expected, series):
    hit = reg.match_sender(header)
    assert hit is not None, header
    src, m = hit
    assert src.id == expected
    assert m.series == series


@pytest.mark.parametrize("header", [
    "Bloomberg <noreply@news.bloomberg.com>",            # welcome / promo, not an issue sender
    "Brew Markets <crew@community.morningbrew.com>",    # community mail, not the newsletter
    "Retirement Upside <team@retirement.thedailyupside.com>",
    "Substack <no-reply@substack.com>",
    "TLDR AI <dan@tldrnewsletter.com>",                 # edition we don't take
    "KPR <notifyy1008@gmail.com>",
])
def test_match_sender_ignores_unknown(reg, header):
    assert reg.match_sender(header) is None


def test_semafor_editions_share_one_brand(reg):
    brands = {s.brand for s in reg.sources if s.id.startswith("semafor_")}
    assert brands == {"semafor"}


def test_roster_labels_override(reg):
    labels = dict(reg.roster_labels("finance"))
    assert labels["semafor"] == "Semafor Business"
    assert dict(reg.roster_labels("tech"))["semafor"] == "Semafor"


def test_rejects_bare_domain():
    s, e = _raw()
    s = copy.deepcopy(s)
    s["sources"][0]["match"] = [{"address": "substack.com"}]
    with pytest.raises(ValueError, match="full email address"):
        _build(s, e)


def test_rejects_shared_address_without_name_regex():
    s, e = _raw()
    s = copy.deepcopy(s)
    tldr_dev = next(x for x in s["sources"] if x["id"] == "tldr_dev")
    tldr_dev["match"] = [{"address": "dan@tldrnewsletter.com"}]
    with pytest.raises(ValueError, match="all need name_regex"):
        _build(s, e)


def test_rejects_duplicate_ids():
    s, e = _raw()
    s = copy.deepcopy(s)
    s["sources"].append(copy.deepcopy(s["sources"][0]))
    with pytest.raises(ValueError, match="duplicate source ids"):
        _build(s, e)


def test_rejects_roster_brand_without_source():
    s, e = _raw()
    e = copy.deepcopy(e)
    e["editions"]["tech"]["roster"].append("doomberg")  # finance-only brand
    with pytest.raises(ValueError, match="no active source in this edition"):
        _build(s, e)


def test_rejects_active_brand_missing_from_roster():
    s, e = _raw()
    e = copy.deepcopy(e)
    e["editions"]["finance"]["roster"].remove("snacks")
    with pytest.raises(ValueError, match="missing from roster"):
        _build(s, e)


def test_rejects_weights_not_summing_to_one():
    s, e = _raw()
    e = copy.deepcopy(e)
    e["editions"]["tech"]["weights"]["coverage"] = 0.9
    with pytest.raises(ValueError, match="sum to 1.0"):
        _build(s, e)


def test_rejects_unknown_field():
    s, e = _raw()
    s = copy.deepcopy(s)
    s["sources"][0]["typo_field"] = True
    with pytest.raises(ValueError):
        _build(s, e)
