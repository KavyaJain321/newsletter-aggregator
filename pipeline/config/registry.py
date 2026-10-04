"""Load and validate sources.yaml + editions.yaml; resolve a sender to a source.

Validation is strict on purpose: a wrong match silently mis-routes newsletters,
so bad config must fail loudly at load time (and in `pipeline doctor`).
"""
from __future__ import annotations

import re
from email.utils import parseaddr
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .settings import CONFIG_DIR

EditionId = Literal["tech", "finance"]
Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# A full address is required on every matcher. Many newsletters share a domain
# (substack.com, axios.com, morningbrew.com, semafor.com, news.bloomberg.com …),
# so a domain-level match would silently pull in unrelated mail.
_ADDRESS_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Matcher(_Strict):
    address: str
    name_regex: str | None = None
    series: str | None = None

    @field_validator("address")
    @classmethod
    def _check_address(cls, v: str) -> str:
        v = v.strip().lower()
        if not _ADDRESS_RE.match(v):
            raise ValueError(f"match.address must be a full email address, got {v!r}")
        return v

    @field_validator("name_regex")
    @classmethod
    def _check_regex(cls, v: str | None) -> str | None:
        if v is not None:
            re.compile(v)
        return v

    def matches(self, display_name: str, address: str) -> bool:
        if address != self.address:
            return False
        return self.name_regex is None or re.search(self.name_regex, display_name.strip()) is not None


class Brand(_Strict):
    label: str


class Source(_Strict):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    brand: str
    editions: list[EditionId] = Field(min_length=1)
    match: list[Matcher] = Field(min_length=1)
    cadence: Literal["daily", "weekdays", "mwf", "weekly", "irregular"]
    expected_send_et: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    paywall_mode: Literal["none", "preview", "partial"] = "none"
    html_only: bool = False
    disclosure: str | None = None
    verified: bool = True
    active: bool = True
    notes: str | None = None


class Range(_Strict):
    min: int = Field(ge=0)
    max: int = Field(ge=0)

    @model_validator(mode="after")
    def _ordered(self) -> "Range":
        if self.min > self.max:
            raise ValueError("slot range min > max")
        return self


class Slots(_Strict):
    big_one: int = Field(ge=1, le=1)
    splits: Range
    hype_check: Range
    quick_hits: Range
    number_of_day: int = Field(ge=0, le=1)
    modules: list[str]


class Window(_Strict):
    mode: Literal["since_last_run"]
    first_run_hours: int = Field(gt=0)
    weekly_lookback_days: int = Field(ge=0)
    weekly_lookback_weekdays: list[Weekday]


class Schedule(_Strict):
    weekdays: list[Weekday] = Field(min_length=1)
    send_time_et: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class Edition(_Strict):
    label: str
    accent: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    schedule: Schedule
    window: Window
    roster: list[str] = Field(min_length=1)
    roster_labels: dict[str, str] = {}
    count_by: Literal["brand"]
    slots: Slots
    weights: dict[Literal["coverage", "relevance", "freshness", "source_quality", "split_bonus"], float]
    reading_wpm: int = Field(gt=0)
    max_email_kb: int = Field(gt=0)

    @field_validator("weights")
    @classmethod
    def _weights_sum(cls, v: dict[str, float]) -> dict[str, float]:
        if any(w < 0 for w in v.values()):
            raise ValueError("weights must be non-negative")
        if abs(sum(v.values()) - 1.0) > 1e-9:
            raise ValueError(f"weights must sum to 1.0, got {sum(v.values())}")
        return v


class Registry(_Strict):
    timezone: str
    brands: dict[str, Brand]
    sources: list[Source]
    editions: dict[EditionId, Edition]

    @model_validator(mode="after")
    def _cross_check(self) -> "Registry":
        errors: list[str] = []
        ids = [s.id for s in self.sources]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            errors.append(f"duplicate source ids: {sorted(dupes)}")
        for s in self.sources:
            if s.brand not in self.brands:
                errors.append(f"source {s.id}: unknown brand {s.brand!r}")
        # Every matcher on an address shared by 2+ matchers must disambiguate by name.
        by_addr: dict[str, list[tuple[str, Matcher]]] = {}
        for s in self.sources:
            for m in s.match:
                by_addr.setdefault(m.address, []).append((s.id, m))
        for addr, ms in by_addr.items():
            if len(ms) > 1 and any(m.name_regex is None for _, m in ms):
                errors.append(f"address {addr} is shared by {[sid for sid, _ in ms]}: all need name_regex")
        for ed_id, ed in self.editions.items():
            for b in ed.roster:
                if b not in self.brands:
                    errors.append(f"edition {ed_id}: roster brand {b!r} is not defined")
            if len(set(ed.roster)) != len(ed.roster):
                errors.append(f"edition {ed_id}: roster has duplicates")
            brands_in_edition = {s.brand for s in self.sources if ed_id in s.editions and s.active}
            missing = brands_in_edition - set(ed.roster)
            extra = set(ed.roster) - brands_in_edition
            if missing:
                errors.append(f"edition {ed_id}: active brands missing from roster: {sorted(missing)}")
            if extra:
                errors.append(f"edition {ed_id}: roster brands with no active source in this edition: {sorted(extra)}")
            for b in ed.roster_labels:
                if b not in ed.roster:
                    errors.append(f"edition {ed_id}: roster_labels key {b!r} not in roster")
        if errors:
            raise ValueError("; ".join(errors))
        return self

    # ---- lookups -----------------------------------------------------------
    def source(self, source_id: str) -> Source:
        for s in self.sources:
            if s.id == source_id:
                return s
        raise KeyError(source_id)

    def sources_for(self, edition: EditionId) -> list[Source]:
        return [s for s in self.sources if s.active and edition in s.editions]

    def roster_labels(self, edition: EditionId) -> list[tuple[str, str]]:
        ed = self.editions[edition]
        return [(b, ed.roster_labels.get(b, self.brands[b].label)) for b in ed.roster]

    def match_sender(self, from_header: str) -> tuple[Source, Matcher] | None:
        """Resolve a raw From header to (source, matcher), or None if unknown.

        A matcher with name_regex beats an address-only matcher; more than one
        equally specific hit is a config error and raises.
        """
        display, address = parseaddr(from_header)
        address = address.strip().lower()
        hits = [(s, m) for s in self.sources if s.active for m in s.match if m.matches(display, address)]
        if not hits:
            return None
        named = [h for h in hits if h[1].name_regex is not None]
        pool = named or hits
        if len(pool) > 1:
            raise ValueError(f"ambiguous sender {from_header!r}: {[s.id for s, _ in pool]}")
        return pool[0]


def load_registry(config_dir: Path = CONFIG_DIR) -> Registry:
    sources = yaml.safe_load((config_dir / "sources.yaml").read_text(encoding="utf-8"))
    editions = yaml.safe_load((config_dir / "editions.yaml").read_text(encoding="utf-8"))
    return Registry(
        timezone=editions["timezone"],
        brands=sources["brands"],
        sources=sources["sources"],
        editions=editions["editions"],
    )
