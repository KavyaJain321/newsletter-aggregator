"""Health monitoring of the shared GPU host (trijya-3) while the pipeline uses it.

One read-only SSH probe collects GPU heat/load/power/VRAM, the GPU's own thermal-slowdown
flags, CPU load, RAM, swap and disk. `assess()` turns a snapshot into a decision:

  phase "start":  ok | refuse          (never start on a hot, busy or starved host)
  phase "run":    ok | warn | critical (warn = back off until cool; critical = stop our Ollama)

`HostMonitor` polls in a background thread while our server is up, logs every sample to
data/host_monitor/YYYY-MM-DD.jsonl, gates each LLM call (`before_call`), and on critical
stops our own Ollama through the supplied callback. It never touches anyone else's process.
CPU temperature is not readable from WSL, so CPU load stands in for it.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable

from ..config.settings import Settings

PROBE_SCRIPT = r"""
NV=$(command -v nvidia-smi || echo /usr/lib/wsl/lib/nvidia-smi)
G=$($NV --query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,power.limit,fan.speed,clocks_event_reasons.hw_thermal_slowdown,clocks_event_reasons.sw_thermal_slowdown --format=csv,noheader,nounits 2>/dev/null | head -1)
echo "gpu=$G"
echo "cores=$(nproc)"
echo "load=$(cut -d' ' -f1 /proc/loadavg)"
awk '/MemAvailable/{a=$2}/SwapTotal/{t=$2}/SwapFree/{f=$2}END{printf "mem_avail_kb=%d\nswap_used_kb=%d\n",a,t-f}' /proc/meminfo
echo "disk_free_kb=$(df -Pk / | awk 'NR==2{print $4}')"
"""


class HostUnsafe(RuntimeError):
    """Raised to stop LLM work on the shared host (critical health or monitor gave up)."""


@dataclass
class HostSnapshot:
    ts: str
    ok_read: bool
    gpu_temp_c: float | None = None
    gpu_util_pct: float | None = None
    vram_used_mb: int | None = None
    vram_total_mb: int | None = None
    power_w: float | None = None
    power_limit_w: float | None = None
    fan_pct: float | None = None
    hw_thermal_slowdown: bool | None = None
    sw_thermal_slowdown: bool | None = None
    cores: int | None = None
    load1: float | None = None
    mem_avail_gb: float | None = None
    swap_used_gb: float | None = None
    disk_free_gb: float | None = None
    error: str | None = None

    @property
    def vram_free_mb(self) -> int | None:
        if self.vram_used_mb is None or self.vram_total_mb is None:
            return None
        return self.vram_total_mb - self.vram_used_mb

    @property
    def load_per_core(self) -> float | None:
        if self.load1 is None or not self.cores:
            return None
        return self.load1 / self.cores


def _num(v: str) -> float | None:
    v = v.strip()
    try:
        return float(v)
    except ValueError:
        return None  # "[N/A]", "[Not Supported]" …


def parse_probe(out: str, code: int) -> HostSnapshot:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    kv = {}
    for line in out.splitlines():
        k, sep, v = line.strip().partition("=")
        if sep:
            kv[k] = v
    gpu = [x.strip() for x in kv.get("gpu", "").split(",")]
    if code != 0 or len(gpu) < 9 or "cores" not in kv:
        return HostSnapshot(ts=ts, ok_read=False, error=(out.strip().splitlines() or ["probe failed"])[-1][:200])
    t, u, used, total, pw, pl, fan, hw, sw = gpu[:9]

    def kb_gb(key: str) -> float | None:
        n = _num(kv.get(key, ""))
        return None if n is None else round(n / 1024 / 1024, 2)

    return HostSnapshot(
        ts=ts, ok_read=True,
        gpu_temp_c=_num(t), gpu_util_pct=_num(u),
        vram_used_mb=int(_num(used)) if _num(used) is not None else None,
        vram_total_mb=int(_num(total)) if _num(total) is not None else None,
        power_w=_num(pw), power_limit_w=_num(pl), fan_pct=_num(fan),
        hw_thermal_slowdown=(hw.lower() == "active") if hw else None,
        sw_thermal_slowdown=(sw.lower() == "active") if sw else None,
        cores=int(_num(kv["cores"]) or 0) or None, load1=_num(kv.get("load", "")),
        mem_avail_gb=kb_gb("mem_avail_kb"), swap_used_gb=kb_gb("swap_used_kb"),
        disk_free_gb=kb_gb("disk_free_kb"),
    )


@dataclass(frozen=True)
class Thresholds:
    start_gpu_temp_c: float = 80
    warn_gpu_temp_c: float = 82
    resume_gpu_temp_c: float = 78
    critical_gpu_temp_c: float = 87
    min_free_vram_mb: int = 10000
    start_load_per_core: float = 0.80
    warn_load_per_core: float = 0.90
    start_min_mem_gb: float = 6.0
    critical_min_mem_gb: float = 2.0
    start_max_swap_gb: float = 2.0
    critical_max_swap_gb: float = 4.0
    min_disk_free_gb: float = 20.0

    @classmethod
    def from_settings(cls, s: Settings) -> "Thresholds":
        return cls(min_free_vram_mb=s.ollama_min_free_vram_mb,
                   start_gpu_temp_c=s.host_start_gpu_temp_c, warn_gpu_temp_c=s.host_warn_gpu_temp_c,
                   resume_gpu_temp_c=s.host_resume_gpu_temp_c, critical_gpu_temp_c=s.host_critical_gpu_temp_c)


def assess(snap: HostSnapshot, th: Thresholds, phase: str, *, model_loaded: bool = False) -> tuple[str, list[str]]:
    """Return (level, reasons). phase "start" -> ok|refuse; phase "run" -> ok|warn|critical."""
    if not snap.ok_read:
        return ("refuse" if phase == "start" else "warn"), [f"cannot read host: {snap.error}"]
    reasons: list[str] = []
    t, lpc = snap.gpu_temp_c, snap.load_per_core
    if phase == "start":
        if t is not None and t >= th.start_gpu_temp_c:
            reasons.append(f"GPU {t:.0f}C >= {th.start_gpu_temp_c:.0f}C")
        if snap.hw_thermal_slowdown or snap.sw_thermal_slowdown:
            reasons.append("GPU thermal slowdown active")
        free = snap.vram_free_mb
        if not model_loaded and (free is None or free < th.min_free_vram_mb):
            reasons.append(f"GPU free {free} MB < {th.min_free_vram_mb} MB")
        if lpc is not None and lpc >= th.start_load_per_core:
            reasons.append(f"CPU load/core {lpc:.2f} >= {th.start_load_per_core}")
        if snap.mem_avail_gb is not None and snap.mem_avail_gb < th.start_min_mem_gb:
            reasons.append(f"RAM available {snap.mem_avail_gb} GB < {th.start_min_mem_gb} GB")
        if snap.swap_used_gb is not None and snap.swap_used_gb > th.start_max_swap_gb:
            reasons.append(f"swap in use {snap.swap_used_gb} GB > {th.start_max_swap_gb} GB")
        if snap.disk_free_gb is not None and snap.disk_free_gb < th.min_disk_free_gb:
            reasons.append(f"disk free {snap.disk_free_gb} GB < {th.min_disk_free_gb} GB")
        return ("refuse" if reasons else "ok"), reasons
    critical: list[str] = []
    if t is not None and t >= th.critical_gpu_temp_c:
        critical.append(f"GPU {t:.0f}C >= {th.critical_gpu_temp_c:.0f}C")
    if snap.hw_thermal_slowdown:
        critical.append("GPU hardware thermal slowdown active")
    if snap.mem_avail_gb is not None and snap.mem_avail_gb < th.critical_min_mem_gb:
        critical.append(f"RAM available {snap.mem_avail_gb} GB < {th.critical_min_mem_gb} GB")
    if snap.swap_used_gb is not None and snap.swap_used_gb > th.critical_max_swap_gb:
        critical.append(f"swap in use {snap.swap_used_gb} GB > {th.critical_max_swap_gb} GB")
    if critical:
        return "critical", critical
    if t is not None and t >= th.warn_gpu_temp_c:
        reasons.append(f"GPU {t:.0f}C >= {th.warn_gpu_temp_c:.0f}C")
    if snap.sw_thermal_slowdown:
        reasons.append("GPU software thermal slowdown active")
    if lpc is not None and lpc >= th.warn_load_per_core:
        reasons.append(f"CPU load/core {lpc:.2f} >= {th.warn_load_per_core}")
    return ("warn" if reasons else "ok"), reasons


def describe(snap: HostSnapshot) -> str:
    if not snap.ok_read:
        return f"unreadable ({snap.error})"

    def f(v, spec: str = "", unit: str = "") -> str:
        return "n/a" if v is None else f"{v:{spec}}{unit}"

    return (f"GPU {f(snap.gpu_temp_c, '.0f', 'C')} {f(snap.gpu_util_pct, '.0f', '%')} "
            f"{f(snap.power_w, '.0f')}/{f(snap.power_limit_w, '.0f', 'W')} fan {f(snap.fan_pct, '.0f', '%')} "
            f"VRAM free {f(snap.vram_free_mb, '', ' MB')} | CPU load/core {f(snap.load_per_core, '.2f')} "
            f"| RAM avail {f(snap.mem_avail_gb, '', ' GB')} swap {f(snap.swap_used_gb, '', ' GB')} "
            f"| disk free {f(snap.disk_free_gb, '', ' GB')}")


@dataclass
class MonitorState:
    level: str = "ok"
    reasons: list[str] = field(default_factory=list)
    last: HostSnapshot | None = None
    consecutive_failures: int = 0
    aborted: bool = False


class HostMonitor:
    """Background watcher for the shared host. Thread-safe; use as a context manager."""

    WARN_AFTER_FAILURES = 2
    ABORT_AFTER_FAILURES = 5

    def __init__(self, settings: Settings, probe: Callable[[], HostSnapshot],
                 on_critical: Callable[[list[str]], None] | None = None,
                 interval_s: float | None = None, max_cooldown_s: float | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        self.s = settings
        self.th = Thresholds.from_settings(settings)
        self.probe = probe
        self.on_critical = on_critical
        self.interval = interval_s if interval_s is not None else settings.host_monitor_interval_s
        self.max_cooldown = max_cooldown_s if max_cooldown_s is not None else settings.host_max_cooldown_s
        self.sleep = sleep
        self.state = MonitorState()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -------------------------------------------------------------- sampling
    def check_once(self) -> MonitorState:
        snap = self.probe()
        with self._lock:
            st = self.state
            st.last = snap
            if snap.ok_read:
                st.consecutive_failures = 0
                was_cooling = st.level == "warn"
                st.level, st.reasons = assess(snap, self.th, "run", model_loaded=True)
                # Hysteresis: once backing off, stay off until the GPU is at/below the resume
                # temperature, so we don't flap at the warn threshold.
                t = snap.gpu_temp_c
                if was_cooling and st.level == "ok" and t is not None and t > self.th.resume_gpu_temp_c:
                    st.level = "warn"
                    st.reasons = [f"cooling: GPU {t:.0f}C > resume {self.th.resume_gpu_temp_c:.0f}C"]
            else:
                st.consecutive_failures += 1
                if st.consecutive_failures >= self.ABORT_AFTER_FAILURES:
                    st.level, st.reasons = "critical", [f"host unreadable {st.consecutive_failures}x: {snap.error}"]
                elif st.consecutive_failures >= self.WARN_AFTER_FAILURES:
                    st.level, st.reasons = "warn", [f"host unreadable {st.consecutive_failures}x: {snap.error}"]
            level, reasons = st.level, list(st.reasons)
            fire = level == "critical" and not st.aborted
            if fire:
                st.aborted = True
        self._log(snap, level, reasons)
        if fire and self.on_critical is not None:
            self.on_critical(reasons)
        return self.state

    def _log(self, snap: HostSnapshot, level: str, reasons: list[str]) -> None:
        d = self.s.data_dir / "host_monitor"
        d.mkdir(parents=True, exist_ok=True)
        rec = {**asdict(snap), "level": level, "reasons": reasons}
        with (d / f"{datetime.now(timezone.utc):%Y-%m-%d}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.check_once()
            except Exception as e:  # noqa: BLE001 — the watcher must never die silently
                with self._lock:
                    self.state.consecutive_failures += 1
                    self.state.reasons = [f"monitor error: {e}"]

    def start(self) -> "HostMonitor":
        self.check_once()
        self._thread = threading.Thread(target=self._loop, name="host-monitor", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval + 5)

    def __enter__(self) -> "HostMonitor":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    # ------------------------------------------------------------- LLM gate
    def before_call(self) -> None:
        """Gate for each LLM request: raise if aborted/critical; wait while warm, up to max_cooldown."""
        waited = 0.0
        while True:
            with self._lock:
                level, reasons, aborted = self.state.level, list(self.state.reasons), self.state.aborted
            if aborted or level == "critical":
                raise HostUnsafe("shared host unsafe, stopped our work: " + "; ".join(reasons))
            if level == "ok":
                return
            if waited >= self.max_cooldown:
                raise HostUnsafe(f"host still not cool after {waited:.0f}s: " + "; ".join(reasons))
            step = min(30.0, self.max_cooldown - waited)
            self.sleep(step)
            waited += step
            self.check_once()  # re-measure now rather than waiting for the poller
