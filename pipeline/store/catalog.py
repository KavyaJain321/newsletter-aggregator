"""Mirror the newsletter registry (config/sources.yaml) into the `sources` table.

The YAML stays the source of truth for newsletters; the table makes them joinable in SQL
(documents.source_id, items.source_id) next to non-newsletter sources (RSS/API feeds) that
other pipelines register directly. Idempotent: run before every ingest.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from ..config.registry import Registry
from .db import Db


def sync_sources(db: Db, reg: Registry) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with db.transaction():
        for s in reg.sources:
            config = {"match": [m.model_dump(exclude_none=True) for m in s.match], "cadence": s.cadence,
                      "expected_send_et": s.expected_send_et, "paywall_mode": s.paywall_mode,
                      "html_only": s.html_only, "disclosure": s.disclosure, "verified": s.verified}
            db.execute(
                "INSERT INTO sources (id, kind, name, brand, editions, config, active, updated_at) "
                "VALUES (?, 'newsletter', ?, ?, ?, ?, ?, ?) ON CONFLICT (id) DO UPDATE SET "
                "name = excluded.name, brand = excluded.brand, editions = excluded.editions, "
                "config = excluded.config, active = excluded.active, updated_at = excluded.updated_at",
                (s.id, reg.brands[s.brand].label, s.brand, json.dumps(list(s.editions)),
                 json.dumps(config, sort_keys=True), s.active, now))
    return len(reg.sources)
