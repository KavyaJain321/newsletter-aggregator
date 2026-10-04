import json
from dataclasses import replace

import pytest

from pipeline.llm.client import LLMClient, MockProvider
from pipeline.llm.host_monitor import (HostMonitor, HostSnapshot, HostUnsafe, Thresholds, assess,
                                       describe, parse_probe)
from pipeline.llm.remote_ollama import RemoteOllama
from pipeline.llm.session import llm_session
from tests.unit.test_remote_ollama import FakeSsh, FakeTunnel, _probe

TH = Thresholds()


def snap(**kw) -> HostSnapshot:
    base = dict(ts="t", ok_read=True, gpu_temp_c=60, gpu_util_pct=40, vram_used_mb=1600, vram_total_mb=12288,
                power_w=200, power_limit_w=300, fan_pct=50, hw_thermal_slowdown=False,
                sw_thermal_slowdown=False, cores=24, load1=2.0, mem_avail_gb=40, swap_used_gb=0,
                disk_free_gb=500)
    base.update(kw)
    return HostSnapshot(**base)


# ------------------------------------------------------------------ parsing
def test_parse_probe_real_shape():
    s = parse_probe("gpu=72, 70, 2290, 12288, 249.98, 300.00, 66, Not Active, Not Active\ncores=24\n"
                    "load=2.16\nmem_avail_kb=45539088\nswap_used_kb=0\ndisk_free_kb=548618128\n", 0)
    assert s.ok_read and s.gpu_temp_c == 72 and s.vram_free_mb == 9998 and s.power_w == 249.98
    assert s.hw_thermal_slowdown is False and abs(s.load_per_core - 0.09) < 0.001
    assert s.mem_avail_gb == 43.43 and s.disk_free_gb == 523.2


def test_parse_probe_na_fields_and_failure():
    s = parse_probe("gpu=70, 50, 1000, 12288, [N/A], [N/A], [N/A], Not Active, Not Active\ncores=8\nload=1\n"
                    "mem_avail_kb=1\nswap_used_kb=0\ndisk_free_kb=1\n", 0)
    assert s.ok_read and s.power_w is None and s.fan_pct is None
    assert "n/a" in describe(s)                       # describe() must not crash on N/A
    bad = parse_probe("ssh: connect timed out", 255)
    assert not bad.ok_read and "timed out" in bad.error


# ------------------------------------------------------------- start gate
@pytest.mark.parametrize("kw,reason", [
    ({"gpu_temp_c": 80}, "GPU 80C >= 80C"),
    ({"sw_thermal_slowdown": True}, "thermal slowdown"),
    ({"hw_thermal_slowdown": True}, "thermal slowdown"),
    ({"vram_used_mb": 3000}, "GPU free 9288 MB"),
    ({"load1": 20.0}, "CPU load/core"),
    ({"mem_avail_gb": 5}, "RAM available"),
    ({"swap_used_gb": 3}, "swap in use"),
    ({"disk_free_gb": 10}, "disk free"),
])
def test_start_refusals(kw, reason):
    level, reasons = assess(snap(**kw), TH, "start")
    assert level == "refuse" and any(reason in r for r in reasons)


def test_start_ok_and_unreadable():
    assert assess(snap(), TH, "start") == ("ok", [])
    assert assess(HostSnapshot(ts="t", ok_read=False, error="x"), TH, "start")[0] == "refuse"


# --------------------------------------------------------------- run levels
@pytest.mark.parametrize("kw,level", [
    ({}, "ok"),
    ({"gpu_temp_c": 82}, "warn"),
    ({"sw_thermal_slowdown": True}, "warn"),
    ({"load1": 22.0}, "warn"),
    ({"gpu_temp_c": 87}, "critical"),
    ({"hw_thermal_slowdown": True}, "critical"),
    ({"mem_avail_gb": 1.5}, "critical"),
    ({"swap_used_gb": 5}, "critical"),
    ({"vram_used_mb": 11800}, "ok"),     # our own loaded model fills VRAM: fine during a run
])
def test_run_levels(kw, level):
    assert assess(snap(**kw), TH, "run", model_loaded=True)[0] == level


# ------------------------------------------------------------ the monitor
class Seq:
    """Probe returning snapshots in order (last one repeats)."""
    def __init__(self, *snaps):
        self.snaps, self.i = list(snaps), 0

    def __call__(self):
        s = self.snaps[min(self.i, len(self.snaps) - 1)]
        self.i += 1
        return s


def test_hysteresis_holds_until_resume_temp(settings):
    m = HostMonitor(settings, probe=Seq(snap(gpu_temp_c=83), snap(gpu_temp_c=80), snap(gpu_temp_c=77)))
    assert m.check_once().level == "warn"
    st = m.check_once()
    assert st.level == "warn" and "cooling" in st.reasons[0]     # 80C: still cooling (> 78C)
    assert m.check_once().level == "ok"                          # 77C: resume


def test_unreadable_escalates_and_fires_once(settings):
    fired = []
    bad = HostSnapshot(ts="t", ok_read=False, error="timeout")
    m = HostMonitor(settings, probe=Seq(bad), on_critical=fired.append)
    levels = [m.check_once().level for _ in range(7)]
    assert levels == ["ok", "warn", "warn", "warn", "critical", "critical", "critical"]
    assert len(fired) == 1 and "unreadable" in fired[0][0]


def test_critical_fires_stop_callback(settings):
    fired = []
    m = HostMonitor(settings, probe=Seq(snap(gpu_temp_c=88)), on_critical=fired.append)
    assert m.check_once().level == "critical" and fired


def test_samples_are_logged(settings):
    HostMonitor(settings, probe=Seq(snap())).check_once()
    files = list((settings.data_dir / "host_monitor").glob("*.jsonl"))
    rec = json.loads(files[0].read_text(encoding="utf-8").splitlines()[0])
    assert rec["level"] == "ok" and rec["gpu_temp_c"] == 60


def test_gate_waits_for_cooling_then_passes(settings):
    sleeps = []
    m = HostMonitor(settings, probe=Seq(snap(gpu_temp_c=84), snap(gpu_temp_c=79), snap(gpu_temp_c=76)),
                    sleep=sleeps.append, max_cooldown_s=600)
    m.check_once()
    m.before_call()                       # waits (79C still cooling), then 76C -> passes
    assert sleeps == [30.0, 30.0]


def test_gate_gives_up_after_max_cooldown(settings):
    m = HostMonitor(settings, probe=Seq(snap(gpu_temp_c=84)), sleep=lambda _: None, max_cooldown_s=60)
    m.check_once()
    with pytest.raises(HostUnsafe, match="not cool after 60s"):
        m.before_call()


def test_gate_refuses_when_critical(settings):
    m = HostMonitor(settings, probe=Seq(snap(gpu_temp_c=90)))
    m.check_once()
    with pytest.raises(HostUnsafe, match="unsafe"):
        m.before_call()


def test_unsafe_host_falls_back_to_next_provider(settings):
    def gate():
        raise HostUnsafe("GPU 90C")
    a, b = MockProvider(["never"]), MockProvider(['{"ok": true}'])
    a.name, b.name = "ollama", "groq"
    r = LLMClient(settings, providers=[a, b], before_call={"ollama": gate}).complete(
        system="s", user="u", purpose="t", json_mode=True)
    assert r.provider == "groq" and a.calls == []         # the hot host never got the request


# ------------------------------------------------------- full guarded session
def _remote(settings, probe_reply):
    rs = replace(settings, ollama_remote_ssh="gpuuser@gpu-host.test", ollama_base_url="http://gpu-host.test:11435",
                 host_monitor_interval_s=3600)
    ssh = FakeSsh(probe=probe_reply)
    tunnel = FakeTunnel()
    return rs, ssh, RemoteOllama(rs, ssh=ssh, sleep=lambda _: None, tunnel_factory=lambda: tunnel), tunnel


def test_session_starts_monitors_and_always_stops(settings):
    rs, ssh, ro, tunnel = _remote(settings, _probe())
    prov = MockProvider(['{"ok": true}'])
    prov.name = "ollama"
    with llm_session(rs, remote=ro, providers=[prov]) as llm:
        assert llm.s.ollama_base_url == "http://127.0.0.1:11437"   # our tunnel, not the shared proxy
        assert llm.complete(system="s", user="u", purpose="t", json_mode=True).data == {"ok": True}
    assert any("nohup" in s for s in ssh.scripts) and any("kill -TERM" in s for s in ssh.scripts)
    assert tunnel.opened and tunnel.closed and not ssh.running


def test_session_stops_ours_when_body_raises(settings):
    rs, ssh, ro, tunnel = _remote(settings, _probe())
    with pytest.raises(ValueError):
        with llm_session(rs, remote=ro, providers=[MockProvider()]):
            raise ValueError("boom")
    assert tunnel.closed and not ssh.running


def test_session_refuses_hot_host_without_starting(settings):
    rs, ssh, ro, _ = _remote(settings, _probe(temp=85))
    from pipeline.llm.remote_ollama import RemoteOllamaError
    with pytest.raises(RemoteOllamaError, match="host not healthy"):
        with llm_session(rs, remote=ro, providers=[MockProvider()]):
            pass
    assert not any("nohup" in s for s in ssh.scripts)
