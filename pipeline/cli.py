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
from .llm.host_monitor import Thresholds, assess, describe
from .llm.remote_ollama import RemoteOllama, RemoteOllamaError
from .llm.session import llm_session
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
            if settings.ollama_remote_ssh and llm is None:
                # Full guarded session: health gate -> start -> monitor -> test -> stop.
                try:
                    with llm_session(settings) as session_client:
                        checks.append(_live_json_check(session_client))
                    checks.append(Check("ollama: on-demand session", "OK",
                                        "health-gated start, monitored, stopped"))
                except RemoteOllamaError as e:
                    checks.append(Check("ollama: on-demand session", "FAIL", str(e)))
            else:
                checks.append(_live_json_check(client))

    # 3b. Shared GPU host health (read-only)
    if settings.ollama_remote_ssh and llm is None:
        try:
            snap = RemoteOllama(settings).probe()
            level, reasons = assess(snap, Thresholds.from_settings(settings), "start")
            checks.append(Check("host health", "OK" if level == "ok" else "WARN",
                                describe(snap) + ("" if level == "ok" else " | would refuse: " + "; ".join(reasons)),
                                required=False))
        except RemoteOllamaError as e:
            checks.append(Check("host health", "WARN", str(e), required=False))

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
            print(f"host={settings.ollama_remote_ssh} reachable={st.reachable} "
                  f"our_private_server(:{settings.ollama_remote_port})_up={st.server_up} ours_pid={st.ours_pid} "
                  f"shared_port_11434_up={st.shared_port_up} gpu_free_mb={st.vram_free_mb} "
                  f"host_time={st.host_weekday} {st.host_time} binary_ok={st.binary_ok} "
                  f"model_present={st.model_present} {st.detail}")
        elif action == "up":
            # Manual start only (no tunnel: this process exits). Runs use llm_session().
            print(ro.up(open_tunnel=False))
        else:
            ro.owned = False  # down() re-checks ownership on the host before stopping anything
            print(ro.down())
    except RemoteOllamaError as e:
        print(f"ERROR: {e}")
        return 1
    return 0


def _host_cmd(settings: Settings, action: str, interval: float, count: int) -> int:
    if not settings.ollama_remote_ssh:
        print("OLLAMA_REMOTE_SSH is not set: no shared GPU host configured")
        return 2
    import time
    ro, th = RemoteOllama(settings), Thresholds.from_settings(settings)
    n = 1 if action == "status" else count
    worst = "ok"
    for i in range(n):
        snap = ro.probe()
        start_level, start_reasons = assess(snap, th, "start")
        run_level, run_reasons = assess(snap, th, "run", model_loaded=True)
        stamp = snap.ts[11:19] + "Z"
        print(f"[{stamp}] {describe(snap)}")
        print(f"           start: {start_level.upper()}{' - ' + '; '.join(start_reasons) if start_reasons else ''}"
              f" | during a run: {run_level.upper()}{' - ' + '; '.join(run_reasons) if run_reasons else ''}")
        worst = max(worst, run_level, key=["ok", "warn", "critical"].index)
        if i < n - 1:
            time.sleep(interval)
    return 0 if worst == "ok" else 1


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
    host = sub.add_parser("host", help="read-only health of the shared GPU host (heat, load, memory)")
    host.add_argument("action", choices=["status", "watch"])
    host.add_argument("--interval", type=float, default=30.0, help="seconds between samples (watch)")
    host.add_argument("--count", type=int, default=10, help="number of samples (watch)")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # never crash on a non-ASCII detail (Windows consoles)
        sys.stdout.reconfigure(errors="replace")
    if args.command == "doctor":
        return _print(run_checks(load_settings(), deep=args.deep))
    if args.command == "ollama":
        return _ollama_cmd(load_settings(), args.action)
    if args.command == "host":
        return _host_cmd(load_settings(), args.action, args.interval, args.count)
    return 2


if __name__ == "__main__":
    sys.exit(main())
