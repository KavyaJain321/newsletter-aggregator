"""Command-line entry point:  python -m pipeline.cli <command>

  doctor [--deep]   check config, Gmail (read-only), LLM providers, DB and paths.
                    --deep also runs one tiny live JSON completion.
Exit code 0 when every required check passes, 1 otherwise.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config.registry import load_registry
from .config.settings import Settings, load_settings
from .ingest.gmail import GmailClient
from .llm.client import LLMClient, NoProviderAvailable
from .store.db import check_writable


@dataclass
class Check:
    name: str
    status: str  # OK | FAIL | WARN | INFO
    detail: str
    required: bool = True


def _dir_writable(path: Path) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, prefix=".doctor-", delete=True):
            pass
    except OSError as e:
        return False, f"{path}: {e}"
    return True, str(path)


def run_checks(settings: Settings, deep: bool = False, gmail: GmailClient | None = None,
               llm: LLMClient | None = None) -> list[Check]:
    checks: list[Check] = []

    # 1. Config
    try:
        reg = load_registry()
        parts = [f"{ed}: {len(reg.sources_for(ed))} sources / {len(reg.editions[ed].roster)} brands"
                 for ed in reg.editions]
        checks.append(Check("config", "OK", " | ".join(parts)))
        unverified = [s.id for s in reg.sources if s.active and not s.verified]
        if unverified:
            checks.append(Check("config: unverified senders", "WARN",
                                f"{', '.join(unverified)} - confirm the address on first issue", required=False))
    except Exception as e:  # noqa: BLE001 — any config error must surface verbatim
        checks.append(Check("config", "FAIL", str(e)))

    # 2. Gmail (read-only)
    ok, detail = (gmail or GmailClient(settings)).check()
    checks.append(Check("gmail", "OK" if ok else "FAIL", detail))

    # 3. LLM providers — at least one must be healthy
    client = llm
    if client is None:
        try:
            client = LLMClient(settings)
        except ValueError as e:
            checks.append(Check("llm", "FAIL", str(e)))
    if client is not None:
        health = client.health()
        for name, (pok, pdetail) in health.items():
            checks.append(Check(f"llm: {name}", "OK" if pok else "WARN", pdetail, required=False))
        any_ok = any(pok for pok, _ in health.values())
        checks.append(Check("llm: at least one provider", "OK" if any_ok else "FAIL",
                            "ready" if any_ok else "no provider is usable - see lines above"))
        if deep and any_ok:
            try:
                r = client.complete(system="Reply with JSON only.",
                                    user='Return exactly {"ok": true} as JSON.',
                                    purpose="doctor@v1", json_mode=True, expect="object",
                                    think=False, max_tokens=64)
                good = r.data == {"ok": True}
                checks.append(Check("llm: live JSON round-trip", "OK" if good else "FAIL",
                                    f"{r.provider}:{r.model} in {r.latency_ms:.0f} ms -> {r.data}"))
            except NoProviderAvailable as e:
                checks.append(Check("llm: live JSON round-trip", "FAIL", str(e)))

    # 4. Storage
    ok, detail = check_writable(settings.db_path)
    checks.append(Check("database", "OK" if ok else "FAIL", detail))
    for name, path in (("out dir", settings.out_dir), ("llm log dir", settings.llm_log_dir),
                       ("archive dir", settings.archive_dir)):
        ok, detail = _dir_writable(path)
        checks.append(Check(name, "OK" if ok else "FAIL", detail))
    fx = settings.fixtures_dir
    checks.append(Check("fixtures dir", "OK" if fx.is_dir() else "INFO",
                        str(fx) if fx.is_dir() else f"{fx} not found (golden tests will be skipped)",
                        required=False))
    return checks


def _print(checks: list[Check]) -> int:
    width = max(len(c.name) for c in checks)
    for c in checks:
        print(f"[{c.status:<4}] {c.name:<{width}}  {c.detail}")
    failed = [c for c in checks if c.required and c.status == "FAIL"]
    print()
    print("RESULT: all required checks passed" if not failed
          else f"RESULT: {len(failed)} required check(s) failed: {', '.join(c.name for c in failed)}")
    return 0 if not failed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    doc = sub.add_parser("doctor", help="check config, Gmail, LLMs, DB and paths")
    doc.add_argument("--deep", action="store_true", help="also run one live JSON completion")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # never crash on a non-ASCII detail (Windows consoles)
        sys.stdout.reconfigure(errors="replace")
    if args.command == "doctor":
        return _print(run_checks(load_settings(), deep=args.deep))
    return 2


if __name__ == "__main__":
    sys.exit(main())
