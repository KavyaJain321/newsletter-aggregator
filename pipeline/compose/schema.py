"""The issue contract: what the compose step (Step 8) must output and the render step (Step 10)
turns into an email. Strict on purpose: an LLM-written issue that doesn't fit is rejected,
never "best-effort" rendered.

Text fields are plain text. The only inline markup allowed is **bold**.

PUBLIC vs INTERNAL (owner decision 2026-10-05): readers never see which newsletters we read.
  - `roster`, `coverage`, `sources`, `cite`/`source` provenance fields are INTERNAL: they keep
    every fact traceable and drive ranking, but the renderer never prints them.
  - What readers see is credited to PRIMARY sources only (companies, agencies, named analysts,
    original reports) via `read_original` / `link` / `credit` fields and the text itself.
  - A newsletter's own opinion or analysis is not republished (not even unattributed).
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Link(_M):
    text: str
    url: HttpUrl


class Source(_M):
    name: str
    url: HttpUrl | None = None


class RosterEntry(_M):
    id: str                       # brand id from editions.yaml roster
    label: str
    url: HttpUrl | None = None


Badge = Literal["reported", "differ", "self", "paywalled"]


class LedgerRow(_M):
    status: Literal["ok", "claimed", "unclear"]
    label: str                    # "Confirmed", "Claimed", "Unclear", "Real", "Caveat" ...
    text: str


class Ledger(_M):
    title: str = "What we actually know"
    rows: list[LedgerRow] = Field(min_length=1, max_length=4)


class SideItem(_M):
    text: str
    cite: str = ""                # INTERNAL provenance (newsletter); never rendered
    credit: str | None = None     # PUBLIC attribution to a primary source/person, e.g. "Jefferies"


class Side(_M):
    kicker: str                   # "Side A", "Reading 1"
    title: str
    items: list[SideItem] = Field(min_length=1, max_length=4)


class Story(_M):
    kind: Literal["story"] = "story"
    tag: str                      # "The big one", "The split", "Hype check"
    tag_style: Literal["solid", "outline"] = "solid"
    coverage: list[str] = Field(min_length=1)
    read_time: str
    headline: str
    size: Literal["lead", "normal"] = "normal"
    sowhat: str | None = None
    paragraphs: list[str] = []
    ledger: Ledger | None = None
    split: list[Side] = Field(default=[], max_length=3)
    after: list[str] = []         # paragraphs after the ledger/split
    note: str | None = None
    badges: list[Badge] = []
    read_original: list[Link] = []           # PUBLIC: primary-source links only
    sources: list[Source] = Field(min_length=1)   # INTERNAL provenance; never rendered

    @model_validator(mode="after")
    def _split_sides(self) -> "Story":
        if self.split and len(self.split) < 2:
            raise ValueError("a split needs 2 or 3 sides")
        return self


class Hit(_M):
    coverage: list[str] = Field(min_length=1)
    badges: list[Badge] = []
    headline: str
    text: str
    sources: list[str] = Field(min_length=1)   # INTERNAL provenance; never rendered
    read_time: str = "1 min"
    link: Link | None = None                    # PUBLIC: primary-source link


class Hits(_M):
    kind: Literal["hits"] = "hits"
    label: str = "Everything else that mattered"
    items: list[Hit] = Field(min_length=1)


class MarketRow(_M):
    name: str
    value: str
    change: str                   # "+0.3%", "-12 bp"
    direction: Literal["up", "down", "flat"]


class Mover(_M):
    ticker: str
    change: str
    direction: Literal["up", "down"]
    why: str


class Markets(_M):
    kind: Literal["markets"] = "markets"
    label: str = "The close"
    asof: str                     # "Friday, Oct. 2 close"
    rows: list[MarketRow] = Field(min_length=1)
    movers: list[Mover] = []
    note: str | None = None
    sources: list[str] = Field(min_length=1)   # INTERNAL provenance; never rendered


class Entry(_M):
    key: str                      # left column: "Paper", "Repo", "Mon Oct 5", ...
    title: str
    text: str = ""
    badges: list[Badge] = []
    source: str | None = None     # INTERNAL provenance; never rendered
    link: Link | None = None


class Compact(_M):
    kind: Literal["compact"] = "compact"
    label: str                    # "For builders", "The week ahead"
    items: list[Entry] = Field(min_length=1)


class Callout(_M):
    """Try-this, term of the day, take worth stealing: a boxed block."""
    kind: Literal["callout"] = "callout"
    label: str
    title: str
    paragraphs: list[str] = Field(min_length=1)
    prompt: str | None = None     # monospace box (try-this prompt, formula)
    source: str | None = None     # INTERNAL provenance; never rendered
    credit: str | None = None     # PUBLIC attribution to a primary source/person
    link: Link | None = None


class Prose(_M):
    kind: Literal["prose"] = "prose"
    label: str
    paragraphs: list[str] = Field(min_length=1)
    sources: list[Source] = []    # INTERNAL provenance; never rendered
    links: list[Link] = []        # PUBLIC: primary-source links


class Morsel(_M):
    text: str
    source: str                   # INTERNAL provenance; never rendered


class Morsels(_M):
    kind: Literal["morsels"] = "morsels"
    label: str = "Three things to bring up at dinner"
    items: list[Morsel] = Field(min_length=2, max_length=6)


Block = Annotated[Union[Story, Hits, Markets, Compact, Callout, Prose, Morsels], Field(discriminator="kind")]


class NumberOfDay(_M):
    value: str
    text: str
    via: str                      # INTERNAL provenance; never rendered
    credit: str | None = None     # PUBLIC primary source, e.g. "US Labor Department"


class Issue(_M):
    edition: Literal["tech", "finance"]
    edition_label: str            # "Tech", "Markets"
    date_label: str               # "Monday, October 5, 2026"
    issue_no: str
    subject: str
    preheader: str
    tagline: str
    send_time: str                # inbox preview, e.g. "9:30 AM"
    roster: list[RosterEntry] = Field(min_length=1)   # brands that delivered in the window (M)
    issues_read: int
    read_minutes: int
    ads_removed: int
    number_of_day: NumberOfDay
    today: list[str] = Field(min_length=2, max_length=4)
    blocks: list[Block] = Field(min_length=3)
    made: str                     # "How we work" (public; must not mention source newsletters)
    window_note: str              # footer line (public)

    @model_validator(mode="after")
    def _coverage_in_roster(self) -> "Issue":
        ids = {r.id for r in self.roster}
        for b in self.blocks:
            covs = [b.coverage] if isinstance(b, Story) else [h.coverage for h in b.items] if isinstance(b, Hits) else []
            for cov in covs:
                bad = [c for c in cov if c not in ids]
                if bad:
                    raise ValueError(f"coverage lists brands not in this issue's roster: {bad}")
                if len(set(cov)) != len(cov):
                    raise ValueError(f"duplicate brand in coverage: {cov}")
        return self
