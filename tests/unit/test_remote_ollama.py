from dataclasses import replace

import pytest

from pipeline.llm.remote_ollama import (TAG, RemoteOllama, RemoteOllamaError, allowed_minutes,
                                        parse_status, remote_health)


def _probe(temp=60, vram_used=1600, load=2.0, mem_kb=40_000_000, swap_kb=0, disk_kb=500_000_000,
           hw="Not Active", sw="Not Active"):
    return (0, f"gpu={temp}, 40, {vram_used}, 12288, 200.0, 300.0, 50, {hw}, {sw}\ncores=24\nload={load}\n"
               f"mem_avail_kb={mem_kb}\nswap_used_kb={swap_kb}\ndisk_free_kb={disk_kb}\n")


class FakeSsh:
    """Stateful fake host. Routes scripts by content: probe / status / start / stop."""

    def __init__(self, probe=None, start=(0, "started=4242\n"), stop=(0, "result=stopped\n"),
                 comes_up=True, ours_running=False, foreign_on_private=False,
                 clock="7 21:30", vram="1600,12288", binary="ok", model="ok", shared="down", reachable=True):
        self.probe_reply = probe or _probe()
        self.start_reply, self.stop_reply = start, stop
        self.comes_up, self.running, self.foreign = comes_up, ours_running, foreign_on_private
        self.clock, self.vram, self.binary, self.model, self.shared = clock, vram, binary, model, shared
        self.reachable = reachable
        self.scripts: list[str] = []

    def __call__(self, host, script):
        self.scripts.append(script)
        if "nohup" in script:
            if self.start_reply[0] == 0 and self.comes_up:
                self.running = True
            return self.start_reply
        if "kill -TERM" in script:
            if "result=stopped" in self.stop_reply[1]:
                self.running = False
            return self.stop_reply
        if "cores=$(nproc)" in script:
            return self.probe_reply
        if not self.reachable:
            return (255, "ssh: connect to host x port 22: Connection timed out")
        up = "up" if (self.running or self.foreign) else "down"
        ours = "4242" if self.running else "none"
        return (0, f"ours={ours}\nserver={up}\nshared={self.shared}\nvram={self.vram}\nclock={self.clock}\n"
                   f"binary={self.binary}\nmodel={self.model}\n")


class FakeTunnel:
    url = "http://127.0.0.1:11437"

    def __init__(self, fail=False):
        self.fail, self.opened, self.closed = fail, False, False

    def open(self):
        if self.fail:
            raise RemoteOllamaError("SSH tunnel exited: bind failed")
        self.opened = True

    def close(self):
        self.closed = True


@pytest.fixture
def rs(settings):
    return replace(settings, ollama_remote_ssh="gpuuser@gpu-host.test")


def _ro(rs, ssh, tunnel=None):
    t = tunnel or FakeTunnel()
    ro = RemoteOllama(rs, ssh=ssh, sleep=lambda _: None, tunnel_factory=lambda: t)
    return ro, t


# ------------------------------------------------------------ blackout maths
@pytest.mark.parametrize("weekday,hhmm,expected", [
    (7, "21:30", 90), (2, "02:30", 80), (1, "05:00", 0), (1, "03:45", 5),
    (6, "03:00", 50), (6, "23:30", 90), (7, "03:00", 90), (5, "23:00", 90),
])
def test_allowed_minutes(rs, weekday, hhmm, expected):
    assert allowed_minutes(rs, weekday, hhmm) == expected


def test_allowed_minutes_evening_before_blackout_day(rs):
    assert allowed_minutes(replace(rs, ollama_remote_max_minutes=600), 7, "23:00") == 60 + 230


# ------------------------------------------------------------------- status
def test_parse_status_full():
    st = parse_status("ours=777\nserver=up\nshared=up\nvram=2000,12288\nclock=3 19:05\nbinary=ok\nmodel=ok\n", 0)
    assert st.reachable and st.server_up and st.ours_pid == 777 and st.shared_port_up
    assert st.vram_free_mb == 10288 and st.host_weekday == 3 and st.host_time == "19:05"


def test_parse_status_unreachable():
    st = parse_status("ssh: connect to host x port 22: Connection timed out", 255)
    assert not st.reachable and "timed out" in st.detail


# ---------------------------------------------------------------------- up
def test_up_starts_isolated_private_instance(rs):
    ssh = FakeSsh()
    ro, t = _ro(rs, ssh)
    msg = ro.up()
    assert ro.owned and "pid 4242" in msg and "port 11436" in msg and "auto-stop in 90 min" in msg
    start = next(s for s in ssh.scripts if "nohup" in s)
    assert "OLLAMA_HOST=127.0.0.1:11436" in start and "11434" not in start   # never the shared port
    assert f"exec -a {TAG} timeout --signal=TERM --kill-after=30 5400" in start
    assert "OLLAMA_NUM_PARALLEL=1" in start and "OLLAMA_MAX_LOADED_MODELS=1" in start
    assert t.opened and ro.base_url == "http://127.0.0.1:11437"


def test_status_checks_private_port(rs):
    ssh = FakeSsh()
    RemoteOllama(rs, ssh=ssh).status()
    assert "127.0.0.1:11436/api/version" in ssh.scripts[-1]


def test_up_refuses_low_vram(rs):
    ro, _ = _ro(rs, FakeSsh(probe=_probe(vram_used=5000)))
    with pytest.raises(RemoteOllamaError, match="GPU free 7288 MB < 10000 MB"):
        ro.up()
    assert not ro.owned


def test_up_refuses_hot_gpu(rs):
    ssh = FakeSsh(probe=_probe(temp=81))
    ro, _ = _ro(rs, ssh)
    with pytest.raises(RemoteOllamaError, match="host not healthy: GPU 81C >= 80C"):
        ro.up()
    assert not any("nohup" in s for s in ssh.scripts)


@pytest.mark.parametrize("kw,match", [
    ({"clock": "2 05:10"}, "power-off window"),
    ({"clock": ""}, "host clock"),
    ({"model": "missing"}, "present=False"),
    ({"reachable": False}, "unreachable"),
])
def test_up_refusals(rs, kw, match):
    ro, _ = _ro(rs, FakeSsh(**kw))
    with pytest.raises(RemoteOllamaError, match=match):
        ro.up()
    assert not ro.owned


def test_private_port_held_by_someone_else_is_refused(rs):
    ssh = FakeSsh(foreign_on_private=True)
    ro, _ = _ro(rs, ssh)
    with pytest.raises(RemoteOllamaError, match="not ours"):
        ro.up()
    assert not any("nohup" in s or "kill -TERM" in s for s in ssh.scripts)


def test_reuses_our_running_instance(rs):
    ssh = FakeSsh(ours_running=True)
    ro, t = _ro(rs, ssh)
    assert "already running (pid 4242)" in ro.up() and ro.owned and t.opened
    assert not any("nohup" in s for s in ssh.scripts)


def test_shared_port_server_is_irrelevant(rs):
    # Someone's Ollama on the shared port neither blocks nor gets used by us.
    ro, _ = _ro(rs, FakeSsh(shared="up"))
    assert "started private instance" in ro.up()


def test_never_healthy_is_cleaned_up(rs):
    ssh = FakeSsh(comes_up=False)
    ro, _ = _ro(rs, ssh)
    with pytest.raises(RemoteOllamaError, match="did not become healthy"):
        ro.up(wait_s=0.01)
    assert any("kill -TERM" in s for s in ssh.scripts) and not ro.owned


def test_tunnel_failure_stops_our_instance(rs):
    ssh = FakeSsh()
    ro, _ = _ro(rs, ssh, tunnel=FakeTunnel(fail=True))
    with pytest.raises(RemoteOllamaError, match="tunnel"):
        ro.up()
    assert any("kill -TERM" in s for s in ssh.scripts) and not ssh.running and not ro.owned


def test_start_reply_lost_triggers_cleanup(rs):
    ssh = FakeSsh(start=(124, "ssh timed out"))
    ssh.running = False

    def flaky(host, script):           # the start actually happened on the host
        out = ssh(host, script)
        if "nohup" in script:
            ssh.running = True
        return out
    ro = RemoteOllama(rs, ssh=flaky, sleep=lambda _: None, tunnel_factory=FakeTunnel)
    with pytest.raises(RemoteOllamaError, match="start failed"):
        ro.up()
    assert any("kill -TERM" in s for s in ssh.scripts) and not ssh.running


# -------------------------------------------------------------------- down
def test_down_closes_tunnel_unloads_and_stops_only_tagged(rs):
    ssh = FakeSsh()
    ro, t = _ro(rs, ssh)
    ro.up()
    assert ro.down() == "stopped" and not ro.owned and t.closed and ro.base_url is None
    stop = next(s for s in ssh.scripts if "kill -TERM" in s)
    assert f"grep -q '^{TAG} '" in stop                         # ownership verified before kill
    assert "127.0.0.1:11436/api/generate" in stop and '"keep_alive":0' in stop


def test_down_unconfirmed_raises(rs):
    ro, _ = _ro(rs, FakeSsh(stop=(124, "ssh to x timed out after 90s")))
    ro.up()
    with pytest.raises(RemoteOllamaError, match="stop not confirmed.*built-in timeout"):
        ro.down()


def test_down_cleans_leftover_from_crashed_run(rs):
    ro, _ = _ro(rs, FakeSsh(ours_running=True))
    assert ro.down() == "stopped"


def test_down_with_nothing_of_ours(rs):
    ssh = FakeSsh()
    ro, _ = _ro(rs, ssh)
    assert ro.down() == "nothing of ours to stop"
    assert not any("kill -TERM" in s for s in ssh.scripts)


def test_context_manager_stops_on_error(rs):
    ssh = FakeSsh()
    with pytest.raises(ValueError):
        with RemoteOllama(rs, ssh=ssh, sleep=lambda _: None, tunnel_factory=FakeTunnel):
            raise ValueError("boom")
    assert any("kill -TERM" in s for s in ssh.scripts) and not ssh.running


def test_requires_configuration(settings):
    with pytest.raises(RemoteOllamaError, match="OLLAMA_REMOTE_SSH"):
        RemoteOllama(settings)


# ------------------------------------------------------------------ health
def test_remote_health_states(rs):
    ok, d = remote_health(rs, ssh=FakeSsh())
    assert ok and "stopped, starts per run" in d and "private :11436" in d
    ok, d = remote_health(rs, ssh=FakeSsh(vram="3000,12288"))
    assert not ok and "cannot start now" in d
    ok, d = remote_health(rs, ssh=FakeSsh(foreign_on_private=True))
    assert not ok and "port busy (not ours)" in d
    ok, d = remote_health(rs, ssh=FakeSsh(reachable=False))
    assert not ok and "unreachable" in d
