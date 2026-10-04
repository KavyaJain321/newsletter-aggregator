"""run_ssh transport: LF-only bytes, safe options, and timeouts that don't raise."""
import subprocess

from pipeline.llm import remote_ollama


def test_run_ssh_sends_lf_only_bytes(monkeypatch):
    """Regression: on Windows, text-mode stdin turned LF into CRLF and broke remote bash."""
    seen = {}

    def fake_run(cmd, input, capture_output, timeout):
        seen["cmd"], seen["input"] = cmd, input
        return subprocess.CompletedProcess(cmd, 0, stdout=b"ok\n", stderr=b"")

    monkeypatch.setattr(remote_ollama.subprocess, "run", fake_run)
    code, out = remote_ollama.run_ssh("h", "if true; then\r\n echo ok\nfi\n")
    assert isinstance(seen["input"], bytes)
    assert b"\r" not in seen["input"]
    assert seen["input"] == b"if true; then\n echo ok\nfi\n"
    assert (code, out) == (0, "ok\n")


def test_run_ssh_options(monkeypatch):
    """Never prompt for a password; classic KEX (post-quantum KEX hung on a Tailscale direct path)."""
    seen = {}
    monkeypatch.setattr(remote_ollama.subprocess, "run",
                        lambda cmd, **kw: seen.setdefault("cmd", cmd) and subprocess.CompletedProcess(cmd, 0, b"", b""))
    remote_ollama.run_ssh("user@host", "true")
    cmd = " ".join(seen["cmd"])
    assert "BatchMode=yes" in cmd
    assert "KexAlgorithms=curve25519-sha256" in cmd and "sntrup761" not in cmd
    assert "ServerAliveInterval=10" in cmd
    assert seen["cmd"][-2:] == ["user@host", "bash -s"]


def test_run_ssh_timeout_returns_124(monkeypatch):
    def boom(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))
    monkeypatch.setattr(remote_ollama.subprocess, "run", boom)
    code, out = remote_ollama.run_ssh("h", "sleep 999", timeout=5)
    assert code == 124 and "timed out after 5s" in out
