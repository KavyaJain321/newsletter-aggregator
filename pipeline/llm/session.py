"""One way to get an LLM client for a pipeline run, with the shared-host guards wired in.

    with llm_session(settings) as llm:
        llm.complete(...)

If OLLAMA_REMOTE_SSH is set (shared trijya-3 GPU box):
  1. RemoteOllama.up(): blackout window + full health gate (heat, VRAM, CPU, RAM, swap, disk)
  2. HostMonitor watches the host for the whole session (logs every sample)
  3. every Ollama request passes monitor.before_call(): waits while the GPU is warm,
     refuses when critical (then the client falls back to Groq if configured)
  4. on critical health the monitor stops OUR Ollama immediately
  5. on exit (normal or error): monitor stopped, our Ollama stopped
Otherwise it just yields a plain LLMClient.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import replace
from typing import Iterator

from ..config.settings import Settings
from .client import LLMClient
from .host_monitor import HostMonitor
from .remote_ollama import RemoteOllama, RemoteOllamaError

log = logging.getLogger(__name__)


@contextmanager
def llm_session(settings: Settings, remote: RemoteOllama | None = None,
                providers: list | None = None) -> Iterator[LLMClient]:
    """`remote` / `providers` are injection points for tests."""
    if not settings.ollama_remote_ssh:
        yield LLMClient(settings, providers=providers)
        return

    ro = remote or RemoteOllama(settings)
    ro.up()  # raises RemoteOllamaError if the host is unhealthy or in its power-off window

    def stop_ours(reasons: list[str]) -> None:
        log.error("shared host critical (%s): stopping our Ollama", "; ".join(reasons))
        try:
            ro.down()
        except RemoteOllamaError as e:  # its built-in timeout still bounds it
            log.error("stop after critical health failed: %s", e)

    # Our client talks to OUR private instance through the SSH tunnel, never the shared proxy.
    session_settings = replace(settings, ollama_base_url=ro.base_url or settings.ollama_base_url)
    monitor = HostMonitor(settings, probe=ro.probe, on_critical=stop_ours)
    try:
        monitor.start()
        yield LLMClient(session_settings, providers=providers, before_call={"ollama": monitor.before_call})
    finally:
        monitor.stop()
        if ro.owned:
            try:
                ro.down()
            except RemoteOllamaError as e:  # don't mask an error raised inside the session
                log.error("stopping our Ollama failed: %s (its built-in timeout still bounds it)", e)
