"""On-demand, ISOLATED Ollama on a shared remote GPU host over SSH (approved option A).

Ollama on the host is NOT always-on (its autostart was disabled on request), so the
pipeline starts its own private instance only for a run and stops it afterwards.

Isolation (learned live 2026-10-04): an instance on the shared port 11434 is picked up
immediately by other team services through the host's Tailscale proxy - re-enabling Ollama
for everyone and competing with our run. So ours listens on a PRIVATE port
(ollama_remote_port, default 11436) that the proxy does not forward, and we reach it
through an SSH tunnel that only this process holds. Other services keep seeing Ollama "off".

Safety rules:
  - start only if the host is healthy (heat, VRAM, CPU, RAM, swap, disk; host_monitor.assess)
  - never start inside the host's power-off window; cap the lifetime to end before it,
    and never longer than ollama_remote_max_minutes
  - the server runs under `timeout`, so it dies on schedule even if this client crashes
  - our process is tagged (argv[0] = TAG) and its PID recorded; only a process still
    carrying our tag is ever stopped
  - 1 loaded model, 1 parallel request, short keep-alive; model unloaded before stopping
"""
from __future__ import annotations

import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Protocol

from ..config.settings import Settings
from .host_monitor import PROBE_SCRIPT, HostSnapshot, Thresholds, assess, parse_probe

TAG = "nlp-ollama-serve"
WORKDIR = "$HOME/.newsletter-pipeline"

SshRunner = Callable[[str, str], tuple[int, str]]  # (host, bash script) -> (exit code, output)

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


class RemoteOllamaError(RuntimeError):
    pass


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


# ------------------------------------------------------------------- tunnel
class Tunnel(Protocol):
    url: str

    def open(self) -> None: ...

    def close(self) -> None: ...


class SshTunnel:
    """`ssh -N -L 127.0.0.1:<local>:127.0.0.1:<remote> host`, held by this process only."""

    def __init__(self, host: str, local_port: int, remote_port: int, wait_s: float = 20.0):
        self.host, self.local_port, self.remote_port, self.wait_s = host, local_port, remote_port, wait_s
        self.url = f"http://127.0.0.1:{local_port}"
        self._proc: subprocess.Popen | None = None

    def open(self) -> None:
        if _port_open(self.local_port):
            raise RemoteOllamaError(f"local port {self.local_port} already in use (set OLLAMA_TUNNEL_PORT)")
        self._proc = subprocess.Popen(
            ["ssh", *SSH_OPTS, "-o", "ExitOnForwardFailure=yes", "-N",
             "-L", f"127.0.0.1:{self.local_port}:127.0.0.1:{self.remote_port}", self.host],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        deadline = time.monotonic() + self.wait_s
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                err = (self._proc.stderr.read() or b"").decode("utf-8", "replace").strip()
                raise RemoteOllamaError(f"SSH tunnel exited: {err[-200:] or 'no detail'}")
            if _port_open(self.local_port):
                return
            time.sleep(0.25)
        self.close()
        raise RemoteOllamaError(f"SSH tunnel did not come up within {self.wait_s:.0f}s")

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


# ------------------------------------------------------------------- status
@dataclass
class RemoteStatus:
    reachable: bool
    server_up: bool                 # our private port answers
    ours_pid: int | None
    vram_used_mb: int | None
    vram_total_mb: int | None
    host_weekday: int | None        # ISO 1=Mon … 7=Sun
    host_time: str | None           # HH:MM in remote_tz
    binary_ok: bool
    model_present: bool
    shared_port_up: bool = False    # someone's Ollama on the shared port (info only)
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
if curl -s -m 3 http://127.0.0.1:{s.ollama_remote_port}/api/version >/dev/null; then echo server=up; else echo server=down; fi
if curl -s -m 3 http://127.0.0.1:11434/api/version >/dev/null; then echo shared=up; else echo shared=down; fi
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
        if sep and k in {"ours", "server", "shared", "vram", "clock", "binary", "model"}:
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
                        kv.get("binary") == "ok", kv.get("model") == "ok",
                        shared_port_up=kv.get("shared") == "up")


# ----------------------------------------------------------- time windows
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


# -------------------------------------------------------------- controller
class RemoteOllama:
    def __init__(self, settings: Settings, ssh: SshRunner | None = None,
                 sleep: Callable[[float], None] = time.sleep,
                 tunnel_factory: Callable[[], Tunnel] | None = None):
        if not settings.ollama_remote_ssh:
            raise RemoteOllamaError("OLLAMA_REMOTE_SSH is not set")
        self.s = settings
        self.host = settings.ollama_remote_ssh
        self.ssh = ssh or (lambda h, sc: run_ssh(h, sc))
        self.sleep = sleep
        self.tunnel_factory = tunnel_factory or (lambda: SshTunnel(
            self.host, settings.ollama_tunnel_port, settings.ollama_remote_port))
        self.tunnel: Tunnel | None = None
        self.owned = False

    @property
    def base_url(self) -> str | None:
        """Where our client reaches OUR Ollama (the tunnel), or None if no tunnel is open."""
        return self.tunnel.url if self.tunnel is not None else None

    # ------------------------------------------------------------------ state
    def status(self) -> RemoteStatus:
        code, out = self.ssh(self.host, _status_script(self.s))
        return parse_status(out, code)

    def probe(self) -> HostSnapshot:
        """Read-only health snapshot of the host (GPU heat/load/VRAM, CPU, RAM, swap, disk)."""
        code, out = self.ssh(self.host, PROBE_SCRIPT)
        return parse_probe(out, code)

    # ------------------------------------------------------------------ start
    def up(self, open_tunnel: bool = True, wait_s: float = 120.0) -> str:
        st = self.status()
        if not st.reachable:
            raise RemoteOllamaError(f"{self.host} unreachable: {st.detail}")
        if not (st.binary_ok and st.model_present):
            raise RemoteOllamaError(f"binary ok={st.binary_ok}, model {self.s.ollama_model} present={st.model_present}")
        if st.server_up and st.ours_pid is None:
            raise RemoteOllamaError(f"private port {self.s.ollama_remote_port} is used by a process that is not ours")
        if st.server_up:
            msg = f"our server already running (pid {st.ours_pid})"
            self.owned = True
        else:
            if st.host_weekday is None or not st.host_time:
                raise RemoteOllamaError("refusing to start: could not read the host clock")
            minutes = allowed_minutes(self.s, st.host_weekday, st.host_time)
            if minutes < 10:
                raise RemoteOllamaError(f"refusing to start: {st.host_time} is in/near the host power-off window")
            snap = self.probe()
            level, reasons = assess(snap, Thresholds.from_settings(self.s), "start")
            if level != "ok":
                raise RemoteOllamaError("refusing to start, host not healthy: " + "; ".join(reasons))
            msg = self._start(minutes, wait_s)
        if open_tunnel:
            tunnel = self.tunnel_factory()
            try:
                tunnel.open()
            except RemoteOllamaError:
                if self.owned:
                    self._stop_quietly()
                raise
            self.tunnel = tunnel
        return msg

    def _start(self, minutes: int, wait_s: float) -> str:
        script = f"""
mkdir -p {WORKDIR} && cd {WORKDIR}
OLLAMA_HOST=127.0.0.1:{self.s.ollama_remote_port} OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 OLLAMA_KEEP_ALIVE={self.s.ollama_keep_alive} \\
  nohup bash -c 'exec -a {TAG} timeout --signal=TERM --kill-after=30 {minutes * 60} {self.s.ollama_remote_bin} serve' \\
  >> ollama.log 2>&1 < /dev/null &
echo $! > ollama.pid
echo "started=$!"
"""
        code, out = self.ssh(self.host, script)
        if code != 0 or "started=" not in out:
            self._stop_quietly()  # it may have started even though the reply was lost
            raise RemoteOllamaError(f"start failed: {out.strip()[-300:]}")
        self.owned = True
        pid = out.split("started=")[1].split()[0]
        deadline = time.monotonic() + wait_s
        while time.monotonic() < deadline:
            if self.status().server_up:
                return f"started private instance (pid {pid}, port {self.s.ollama_remote_port}, auto-stop in {minutes} min)"
            self.sleep(2.0)
        self._stop_quietly()
        raise RemoteOllamaError(f"server did not become healthy within {wait_s:.0f}s (stopped it again)")

    # ------------------------------------------------------------------- stop
    def _stop_quietly(self) -> None:
        try:
            self.down()
        except RemoteOllamaError:
            pass  # its built-in timeout still bounds it

    def down(self) -> str:
        if self.tunnel is not None:
            self.tunnel.close()
            self.tunnel = None
        if not self.owned:
            st = self.status()
            if st.ours_pid is None:
                return "nothing of ours to stop"
        script = f"""
P={WORKDIR}/ollama.pid
if [ ! -f "$P" ]; then echo result=none; exit 0; fi
PID=$(cat "$P")
if kill -0 "$PID" 2>/dev/null && tr '\\0' ' ' < /proc/$PID/cmdline | grep -q '^{TAG} '; then
  curl -s -m 20 -X POST http://127.0.0.1:{self.s.ollama_remote_port}/api/generate \\
    -d '{{"model":"{self.s.ollama_model}","keep_alive":0}}' >/dev/null 2>&1
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
        if self.owned or self.tunnel is not None:
            self.down()


def remote_health(settings: Settings, ssh: SshRunner | None = None) -> tuple[bool, str]:
    """Doctor view of the on-demand host: usable if reachable, model present and healthy enough to start."""
    try:
        ro = RemoteOllama(settings, ssh=ssh)
        st = ro.status()
    except (RemoteOllamaError, subprocess.SubprocessError, OSError) as e:
        return False, str(e)
    if not st.reachable:
        return False, f"on-demand host {settings.ollama_remote_ssh} unreachable: {st.detail}"
    if not (st.binary_ok and st.model_present):
        return False, f"on-demand host: binary ok={st.binary_ok}, model {settings.ollama_model} present={st.model_present}"
    state = ("running (ours)" if st.ours_pid else "port busy (not ours)") if st.server_up else "stopped, starts per run"
    free = st.vram_free_mb
    ok_vram = free is not None and free >= settings.ollama_min_free_vram_mb
    detail = (f"on-demand {settings.ollama_remote_ssh} | {settings.ollama_model} | private :{settings.ollama_remote_port} "
              f"| {state} | GPU free {free} MB")
    usable = (st.server_up and st.ours_pid is not None) or (not st.server_up and ok_vram)
    return usable, detail + ("" if usable else " (cannot start now)")
