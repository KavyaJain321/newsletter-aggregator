"""Command-line entry point:  python -m pipeline.cli <command>

  doctor [--deep]   check config, Gmail (read-only), LLM providers, DB and paths.
                    --deep also runs one tiny live JSON completion (starting and then
                    stopping the on-demand remote Ollama if OLLAMA_REMOTE_SSH is set).
  ollama status|up|down   manual control of the on-demand remote Ollama.
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
from .llm.remote_ollama import RemoteOllama, RemoteOllamaError
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
            remote = RemoteOllama(settings) if (settings.ollama_remote_ssh and llm is None) else None
            try:
                if remote is not None:
                    checks.append(Check("ollama: on-demand start", "OK", remote.up()))
                checks.append(_live_json_check(client))
            except RemoteOllamaError as e:
                checks.append(Check("ollama: on-demand start", "FAIL", str(e)))
            finally:
                if remote is not None and remote.owned:
                    try:
                        checks.append(Check("ollama: on-demand stop", "OK", remote.down()))
                    except RemoteOllamaError as e:
                        checks.append(Check("ollama: on-demand stop", "FAIL", str(e)))

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


def _live_json_check(client: LLMClient) -> Check:
    try:
        r = client.complete(system="Reply with JSON only.", user='Return exactly {"ok": true} as JSON.',
                            purpose="doctor@v1", json_mode=True, expect="object", think=False, max_tokens=64)
    except NoProviderAvailable as e:
        return Check("llm: live JSON round-trip", "FAIL", str(e))
    good = r.data == {"ok": True}
    return Check("llm: live JSON round-trip", "OK" if good else "FAIL",
                 f"{r.provider}:{r.model} in {r.latency_ms:.0f} ms -> {r.data}")


def _ollama_cmd(settings: Settings, action: str) -> int:
    if not settings.ollama_remote_ssh:
        print("OLLAMA_REMOTE_SSH is not set: no on-demand host configured")
        return 2
    ro = RemoteOllama(settings)
    try:
        if action == "status":
            st = ro.status()
            print(f"host={settings.ollama_remote_ssh} reachable={st.reachable} server_up={st.server_up} "
                  f"ours_pid={st.ours_pid} gpu_free_mb={st.vram_free_mb} host_time={st.host_weekday} {st.host_time} "
                  f"binary_ok={st.binary_ok} model_present={st.model_present} {st.detail}")
        elif action == "up":
            print(ro.up())
        else:
            ro.owned = False  # down() re-checks ownership on the host before stopping anything
            print(ro.down())
    except RemoteOllamaError as e:
        print(f"ERROR: {e}")
        return 1
    return 0


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
    oll = sub.add_parser("ollama", help="control the on-demand remote Ollama (OLLAMA_REMOTE_SSH)")
    oll.add_argument("action", choices=["status", "up", "down"])
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # never crash on a non-ASCII detail (Windows consoles)
        sys.stdout.reconfigure(errors="replace")
    if args.command == "doctor":
        return _print(run_checks(load_settings(), deep=args.deep))
    if args.command == "ollama":
        return _ollama_cmd(load_settings(), args.action)
    return 2


if __name__ == "__main__":
    sys.exit(main())
