"""On-demand Ollama on a shared remote GPU host over SSH (approved option A).

Ollama on the host is NOT always-on (its autostart was disabled on request), so the
pipeline starts it only for a run and stops it afterwards. Safety rules:

  - only start when the GPU has >= ollama_min_free_vram_mb free
  - never start inside the host's power-off window (remote_blackout on
    remote_blackout_days, host time zone); cap the lifetime so the server exits
    before the window begins, and never longer than ollama_remote_max_minutes
  - the server runs under `timeout`, so it dies on schedule even if this client crashes
  - our process is tagged (argv[0] = TAG) and its PID recorded; we only ever stop a
    process that is still tagged as ours. A server we did not start is used, never stopped.
  - bound to 127.0.0.1 on the host: reachable only through the team's Tailscale proxy
  - conservative server settings: 1 loaded model, 1 parallel request, short keep-alive
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

import requests

from ..config.settings import Settings

TAG = "nlp-ollama-serve"
WORKDIR = "$HOME/.newsletter-pipeline"

SshRunner = Callable[[str, str], tuple[int, str]]  # (host, bash script) -> (exit code, stdout+stderr)


class RemoteOllamaError(RuntimeError):
    pass


SSH_OPTS = [
    "-o", "BatchMode=yes",              # key-based only: never prompt for a password
    "-o", "ConnectTimeout=15",
    "-o", "ServerAliveInterval=10",     # notice a dead connection within ~30s
    "-o", "ServerAliveCountMax=3",
    # The post-quantum default (sntrup761) sends one large handshake packet that is
    # dropped on some Tailscale direct paths (MTU), hanging at KEX_ECDH_REPLY. Classic
    # curve25519 KEX is unaffected. Verified against trijya-3-1 on 2026-10-04.
    "-o", "KexAlgorithms=curve25519-sha256,curve25519-sha256@libssh.org",
]


def run_ssh(host: str, script: str, timeout: float = 90.0) -> tuple[int, str]:
    """Run a bash script on `host` via stdin. Returns (124, msg) if it times out."""
    # Send bytes, not text: on Windows, text-mode stdin turns LF into CRLF and remote
    # bash then sees "then<CR>" (syntax error). Normalise any CRLF in the script too.
    data = script.replace("\r\n", "\n").encode("utf-8")
    try:
        proc = subprocess.run(["ssh", *SSH_OPTS, host, "bash -s"],
                              input=data, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, f"ssh to {host} timed out after {timeout:.0f}s"
    out = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    return proc.returncode, out


@dataclass
class RemoteStatus:
    reachable: bool
    server_up: bool
    ours_pid: int | None
    vram_used_mb: int | None
    vram_total_mb: int | None
    host_weekday: int | None        # ISO 1=Mon … 7=Sun
    host_time: str | None           # HH:MM in remote_tz
    binary_ok: bool
    model_present: bool
    detail: str = ""

    @property
    def vram_free_mb(self) -> int | None:
        if self.vram_used_mb is None or self.vram_total_mb is None:
            return None
        return self.vram_total_mb - self.vram_used_mb


def _status_script(s: Settings) -> str:
    model, _, tag = s.ollama_model.partition(":")
    tag = tag or "latest"
    return f"""
P={WORKDIR}/ollama.pid
OURS=none
if [ -f "$P" ]; then PID=$(cat "$P"); if kill -0 "$PID" 2>/dev/null && tr '\\0' ' ' < /proc/$PID/cmdline | grep -q '^{TAG} '; then OURS=$PID; fi; fi
echo "ours=$OURS"
if curl -s -m 3 http://127.0.0.1:11434/api/version >/dev/null; then echo server=up; else echo server=down; fi
NV=$(command -v nvidia-smi || echo /usr/lib/wsl/lib/nvidia-smi)
echo "vram=$($NV --query-gpu=memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')"
echo "clock=$(TZ={s.remote_tz} date '+%u %H:%M')"
[ -x {s.ollama_remote_bin} ] && echo binary=ok || echo binary=missing
[ -f "$HOME/.ollama/models/manifests/registry.ollama.ai/library/{model}/{tag}" ] && echo model=ok || echo model=missing
"""


def parse_status(out: str, code: int) -> RemoteStatus:
    kv: dict[str, str] = {}
    for line in out.splitlines():
        k, sep, v = line.strip().partition("=")
        if sep and k in {"ours", "server", "vram", "clock", "binary", "model"}:
            kv[k] = v.strip()
    if code != 0 or "server" not in kv:
        return RemoteStatus(False, False, None, None, None, None, None, False, False,
                            detail=(out.strip().splitlines() or ["ssh failed"])[-1])
    used = total = None
    if "," in kv.get("vram", ""):
        a, b = kv["vram"].split(",", 1)
        used, total = int(a), int(b)
    wd = hm = None
    if " " in kv.get("clock", ""):
        d, hm = kv["clock"].split(" ", 1)
        wd = int(d)
    ours = None if kv.get("ours", "none") == "none" else int(kv["ours"])
    return RemoteStatus(True, kv["server"] == "up", ours, used, total, wd, hm,
                        kv.get("binary") == "ok", kv.get("model") == "ok")


def _parse_range(text: str) -> tuple[int, int]:
    a, _, b = text.partition("-")
    return int(a), int(b or a)


def _minutes(hm: str) -> int:
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def allowed_minutes(s: Settings, weekday: int, hhmm: str) -> int:
    """Minutes the server may run from host-local `weekday hh:mm`, given the blackout. 0 = refuse."""
    cap = s.ollama_remote_max_minutes
    d0, d1 = _parse_range(s.remote_blackout_days)
    start_s, _, end_s = s.remote_blackout.partition("-")
    b_start, b_end = _minutes(start_s), _minutes(end_s)
    now = _minutes(hhmm)
    if d0 <= weekday <= d1:
        if b_start <= now < b_end:
            return 0
        if now < b_start:
            cap = min(cap, b_start - now)
    # A run that starts late on the evening before a blackout day must end by its start.
    next_day = weekday % 7 + 1
    if d0 <= next_day <= d1 and now >= b_end:
        cap = min(cap, (24 * 60 - now) + b_start)
    return max(cap, 0)


class RemoteOllama:
    def __init__(self, settings: Settings, ssh: SshRunner | None = None,
                 http: requests.Session | None = None, sleep: Callable[[float], None] = time.sleep):
        if not settings.ollama_remote_ssh:
            raise RemoteOllamaError("OLLAMA_REMOTE_SSH is not set")
        self.s = settings
        self.host = settings.ollama_remote_ssh
        self.ssh = ssh or (lambda h, sc: run_ssh(h, sc))
        self.http = http or requests.Session()
        self.sleep = sleep
        self.owned = False

    # ------------------------------------------------------------------ state
    def status(self) -> RemoteStatus:
        code, out = self.ssh(self.host, _status_script(self.s))
        return parse_status(out, code)

    def _api_up(self) -> bool:
        try:
            return self.http.get(f"{self.s.ollama_base_url}/api/version", timeout=(5, 10)).status_code == 200
        except requests.RequestException:
            return False

    # ------------------------------------------------------------------ start
    def up(self, wait_s: float = 120.0) -> str:
        st = self.status()
        if not st.reachable:
            raise RemoteOllamaError(f"{self.host} unreachable: {st.detail}")
        if not (st.binary_ok and st.model_present):
            raise RemoteOllamaError(f"binary ok={st.binary_ok}, model {self.s.ollama_model} present={st.model_present}")
        if st.server_up:
            self.owned = st.ours_pid is not None
            return f"server already running ({'ours' if self.owned else 'NOT ours - will use it but never stop it'})"
        if st.host_weekday is None or not st.host_time:
            raise RemoteOllamaError("refusing to start: could not read the host clock")
        minutes = allowed_minutes(self.s, st.host_weekday, st.host_time)
        if minutes < 10:
            raise RemoteOllamaError(f"refusing to start: {st.host_time} is in/near the host power-off window")
        free = st.vram_free_mb
        if free is None or free < self.s.ollama_min_free_vram_mb:
            raise RemoteOllamaError(f"refusing to start: GPU has {free} MB free, need {self.s.ollama_min_free_vram_mb} MB")
        seconds = minutes * 60
        script = f"""
mkdir -p {WORKDIR} && cd {WORKDIR}
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 OLLAMA_KEEP_ALIVE={self.s.ollama_keep_alive} \\
  nohup bash -c 'exec -a {TAG} timeout --signal=TERM --kill-after=30 {seconds} {self.s.ollama_remote_bin} serve' \\
  >> ollama.log 2>&1 < /dev/null &
echo $! > ollama.pid
echo "started=$!"
"""
        code, out = self.ssh(self.host, script)
        if code != 0 or "started=" not in out:
            # The server may have started even though we didn't get the reply: clean up ours.
            try:
                self.down()
            except RemoteOllamaError:
                pass  # its built-in timeout still bounds it
            raise RemoteOllamaError(f"start failed: {out.strip()[-300:]}")
        self.owned = True
        deadline = time.monotonic() + wait_s
        while time.monotonic() < deadline:
            if self._api_up():
                return f"started (pid {out.split('started=')[1].split()[0]}, auto-stop in {minutes} min)"
            self.sleep(2.0)
        self.down()
        raise RemoteOllamaError(f"server did not become healthy within {wait_s:.0f}s (stopped it again)")

    # ------------------------------------------------------------------- stop
    def down(self) -> str:
        if not self.owned:
            st = self.status()
            if st.ours_pid is None:
                return "nothing of ours to stop"
        try:  # free VRAM promptly (best effort)
            self.http.post(f"{self.s.ollama_base_url}/api/generate",
                           json={"model": self.s.ollama_model, "keep_alive": 0}, timeout=(5, 30))
        except requests.RequestException:
            pass
        script = f"""
P={WORKDIR}/ollama.pid
if [ ! -f "$P" ]; then echo result=none; exit 0; fi
PID=$(cat "$P")
if kill -0 "$PID" 2>/dev/null && tr '\\0' ' ' < /proc/$PID/cmdline | grep -q '^{TAG} '; then
  kill -TERM "$PID"
  for i in $(seq 1 40); do kill -0 "$PID" 2>/dev/null || break; sleep 1; done
  if kill -0 "$PID" 2>/dev/null; then echo result=still-running; else echo result=stopped; rm -f "$P"; fi
else
  echo result=gone; rm -f "$P"
fi
"""
        code, out = self.ssh(self.host, script)
        self.owned = False
        if "result=still-running" in out:
            raise RemoteOllamaError("our ollama did not exit within 40s (its built-in timeout will still stop it)")
        if "result=" not in out:
            raise RemoteOllamaError(f"stop not confirmed ({out.strip()[-160:]}); "
                                    "our server still exits on its built-in timeout")
        return out.split("result=")[-1].strip()

    # ------------------------------------------------------- context manager
    def __enter__(self) -> "RemoteOllama":
        self.up()
        return self

    def __exit__(self, *exc) -> None:
        if self.owned:
            self.down()


def remote_health(settings: Settings, ssh: SshRunner | None = None) -> tuple[bool, str]:
    """Doctor view of an on-demand host: usable if reachable, model present and VRAM allows a start."""
    try:
        st = RemoteOllama(settings, ssh=ssh).status()
    except (RemoteOllamaError, subprocess.SubprocessError, OSError) as e:
        return False, str(e)
    if not st.reachable:
        return False, f"on-demand host {settings.ollama_remote_ssh} unreachable: {st.detail}"
    if not (st.binary_ok and st.model_present):
        return False, f"on-demand host: binary ok={st.binary_ok}, model {settings.ollama_model} present={st.model_present}"
    state = "running" + (" (ours)" if st.ours_pid else " (not ours)") if st.server_up else "stopped, starts per run"
    free = st.vram_free_mb
    ok_vram = free is not None and free >= settings.ollama_min_free_vram_mb
    detail = f"on-demand {settings.ollama_remote_ssh} | {settings.ollama_model} | {state} | GPU free {free} MB"
    return (st.server_up or ok_vram), detail + ("" if (st.server_up or ok_vram) else " (too little to start now)")
