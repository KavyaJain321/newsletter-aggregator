from dataclasses import replace

import pytest

from pipeline.llm.remote_ollama import (TAG, RemoteOllama, RemoteOllamaError, allowed_minutes,
                                        parse_status, remote_health)
from tests.conftest import FakeResp, FakeSession


def _status(server="down", ours="none", vram="1600,12288", clock="7 21:30", binary="ok", model="ok"):
    return (0, f"ours={ours}\nserver={server}\nvram={vram}\nclock={clock}\nbinary={binary}\nmodel={model}\n")


class FakeSsh:
    """Routes scripts by their content: status / start / stop."""
    def __init__(self, status=None, start=(0, "started=4242\n"), stop=(0, "result=stopped\n")):
        self.status_reply = status or _status()
        self.start_reply, self.stop_reply = start, stop
        self.scripts: list[str] = []

    def __call__(self, host, script):
        self.scripts.append(script)
        if "nohup" in script:
            return self.start_reply
        if "kill -TERM" in script:
            return self.stop_reply
        return self.status_reply


@pytest.fixture
def rs(settings):
    return replace(settings, ollama_remote_ssh="gpuuser@gpu-host.test",
                   ollama_base_url="http://gpu-host.test:11435")


def _api(up=True):
    sess = FakeSession()
    sess.add("GET", "/api/version", *([FakeResp(200, {"version": "0.31.2"})] * 5 if up else []))
    sess.add("POST", "/api/generate", FakeResp(200, {}))
    return sess


# ------------------------------------------------------------ blackout maths
@pytest.mark.parametrize("weekday,hhmm,expected", [
    (7, "21:30", 90),   # Sunday evening: no shutdown tonight-relevant beyond cap
    (2, "02:30", 80),   # Tue 02:30: must end by 03:50
    (1, "05:00", 0),    # inside the power-off window
    (1, "03:45", 5),    # too close to the window
    (6, "03:00", 50),   # Saturday early morning
    (6, "23:30", 90),   # Saturday night -> Sunday has no shutdown
    (7, "03:00", 90),   # Sunday stays on
    (5, "23:00", 90),   # Fri 23:00 -> Sat 03:50 is far away
])
def test_allowed_minutes(rs, weekday, hhmm, expected):
    assert allowed_minutes(rs, weekday, hhmm) == expected


def test_allowed_minutes_evening_before_blackout_day(rs):
    s = replace(rs, ollama_remote_max_minutes=600)
    assert allowed_minutes(s, 7, "23:00") == 60 + 230   # Sun 23:00 -> must stop by Mon 03:50


# ------------------------------------------------------------------- status
def test_parse_status_full():
    st = parse_status(_status(server="up", ours="777", vram="2000,12288", clock="3 19:05")[1], 0)
    assert st.reachable and st.server_up and st.ours_pid == 777
    assert st.vram_free_mb == 10288 and st.host_weekday == 3 and st.host_time == "19:05"


def test_parse_status_unreachable():
    st = parse_status("ssh: connect to host x port 22: Connection timed out", 255)
    assert not st.reachable and "timed out" in st.detail


# ---------------------------------------------------------------------- up
def test_up_starts_with_safe_settings(rs):
    ssh = FakeSsh()
    ro = RemoteOllama(rs, ssh=ssh, http=_api(), sleep=lambda _: None)
    msg = ro.up()
    assert ro.owned and "pid 4242" in msg and "auto-stop in 90 min" in msg
    start = next(s for s in ssh.scripts if "nohup" in s)
    assert f"exec -a {TAG} timeout --signal=TERM --kill-after=30 5400" in start
    assert "OLLAMA_HOST=127.0.0.1:11434" in start
    assert "OLLAMA_NUM_PARALLEL=1" in start and "OLLAMA_MAX_LOADED_MODELS=1" in start


def test_up_refuses_low_vram(rs):
    ro = RemoteOllama(rs, ssh=FakeSsh(status=_status(vram="5000,12288")), http=_api())
    with pytest.raises(RemoteOllamaError, match="GPU has 7288 MB free"):
        ro.up()
    assert not ro.owned


def test_up_refuses_in_blackout(rs):
    ro = RemoteOllama(rs, ssh=FakeSsh(status=_status(clock="2 05:10")), http=_api())
    with pytest.raises(RemoteOllamaError, match="power-off window"):
        ro.up()


def test_up_refuses_unknown_clock(rs):
    ro = RemoteOllama(rs, ssh=FakeSsh(status=_status(clock="")), http=_api())
    with pytest.raises(RemoteOllamaError, match="host clock"):
        ro.up()


def test_up_refuses_missing_model(rs):
    ro = RemoteOllama(rs, ssh=FakeSsh(status=_status(model="missing")), http=_api())
    with pytest.raises(RemoteOllamaError, match="present=False"):
        ro.up()


def test_existing_foreign_server_is_used_never_stopped(rs):
    ssh = FakeSsh(status=_status(server="up", ours="none"))
    ro = RemoteOllama(rs, ssh=ssh, http=_api())
    assert "NOT ours" in ro.up() and not ro.owned
    assert ro.down() == "nothing of ours to stop"
    assert not any("kill -TERM" in s for s in ssh.scripts)
    assert not any("nohup" in s for s in ssh.scripts)


def test_unhealthy_start_is_cleaned_up(rs):
    ssh = FakeSsh()
    ro = RemoteOllama(rs, ssh=ssh, http=_api(up=False), sleep=lambda _: None)
    with pytest.raises(RemoteOllamaError, match="did not become healthy"):
        ro.up(wait_s=0.01)
    assert any("kill -TERM" in s for s in ssh.scripts) and not ro.owned


# -------------------------------------------------------------------- down
def test_down_only_kills_tagged_process(rs):
    ssh = FakeSsh()
    http = _api()
    ro = RemoteOllama(rs, ssh=ssh, http=http, sleep=lambda _: None)
    ro.up()
    assert ro.down() == "stopped" and not ro.owned
    stop = next(s for s in ssh.scripts if "kill -TERM" in s)
    assert f"grep -q '^{TAG} '" in stop          # ownership verified on the host before kill
    unload = [c for c in http.calls if c["url"].endswith("/api/generate")]
    assert unload and unload[0]["json"]["keep_alive"] == 0


def test_down_cleans_leftover_from_crashed_run(rs):
    ssh = FakeSsh(status=_status(server="up", ours="999"))
    ro = RemoteOllama(rs, ssh=ssh, http=_api())
    assert ro.down() == "stopped"


def test_context_manager_stops_on_error(rs):
    ssh = FakeSsh()
    with pytest.raises(ValueError):
        with RemoteOllama(rs, ssh=ssh, http=_api(), sleep=lambda _: None):
            raise ValueError("boom")
    assert any("kill -TERM" in s for s in ssh.scripts)


def test_requires_configuration(settings):
    with pytest.raises(RemoteOllamaError, match="OLLAMA_REMOTE_SSH"):
        RemoteOllama(settings)


# ------------------------------------------------------------------ health
def test_remote_health_states(rs):
    ok, d = remote_health(rs, ssh=FakeSsh())
    assert ok and "stopped, starts per run" in d
    ok, d = remote_health(rs, ssh=FakeSsh(status=_status(vram="9000,12288")))
    assert not ok and "too little to start now" in d
    ok, d = remote_health(rs, ssh=lambda h, s: (255, "Connection timed out"))
    assert not ok and "unreachable" in d


# ------------------------------------------------------- failure paths
def test_down_unconfirmed_raises_instead_of_claiming_success(rs):
    ssh = FakeSsh(stop=(124, "ssh to x timed out after 90s"))
    ro = RemoteOllama(rs, ssh=ssh, http=_api(), sleep=lambda _: None)
    ro.up()
    with pytest.raises(RemoteOllamaError, match="stop not confirmed.*built-in timeout"):
        ro.down()
    assert not ro.owned


def test_start_reply_lost_triggers_cleanup(rs):
    # Start may have succeeded on the host even though the reply was lost.
    ssh = FakeSsh(start=(124, "ssh timed out"), status=_status())
    calls = {"n": 0}

    def ssh_after_start(host, script):
        if "nohup" not in script and "kill -TERM" not in script and calls["n"] > 0:
            return _status(server="up", ours="555")  # status after the lost start shows ours
        if "nohup" in script:
            calls["n"] += 1
        return ssh(host, script)

    ro = RemoteOllama(rs, ssh=ssh_after_start, http=_api(), sleep=lambda _: None)
    with pytest.raises(RemoteOllamaError, match="start failed"):
        ro.up()
    assert any("kill -TERM" in s for s in ssh.scripts)   # our leftover was stopped
