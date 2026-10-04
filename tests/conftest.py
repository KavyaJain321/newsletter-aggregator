"""Shared test helpers: isolated settings and a scripted fake HTTP session."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

import pytest
import requests

from pipeline.config.settings import Settings, load_settings


class FakeResp:
    def __init__(self, status: int = 200, data: Any = None, text: str | None = None,
                 headers: dict[str, str] | None = None):
        self.status_code = status
        self._data = data
        self.text = text if text is not None else (json.dumps(data) if data is not None else "")
        self.headers = {"content-type": "application/json", **(headers or {})}

    def json(self) -> Any:
        if self._data is None:
            raise ValueError("no JSON body")
        return self._data


class FakeSession:
    """Scripted responses: add(method, url_substring, FakeResp | Exception), consumed in order."""

    def __init__(self) -> None:
        self.routes: list[tuple[str, str, deque]] = []
        self.calls: list[dict[str, Any]] = []

    def add(self, method: str, url_part: str, *replies: Any) -> "FakeSession":
        self.routes.append((method.upper(), url_part, deque(replies)))
        return self

    def request(self, method: str, url: str, **kw: Any) -> FakeResp:
        self.calls.append({"method": method.upper(), "url": url, **kw})
        for m, part, q in self.routes:
            if m == method.upper() and part in url and q:
                reply = q.popleft()
                if isinstance(reply, Exception):
                    raise reply
                return reply
        raise requests.ConnectionError(f"no scripted reply for {method} {url}")

    def get(self, url: str, **kw: Any) -> FakeResp:
        return self.request("GET", url, **kw)

    def post(self, url: str, **kw: Any) -> FakeResp:
        return self.request("POST", url, **kw)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    env = {
        "PIPELINE_DATA_DIR": str(tmp_path / "data"),
        "PIPELINE_OUT_DIR": str(tmp_path / "out"),
        "FIXTURES_DIR": str(tmp_path / "fixtures"),
        "GMAIL_TOKEN_PATH": str(tmp_path / "token.json"),
        "GMAIL_CLIENT_PATH": str(tmp_path / "client.json"),
        "OLLAMA_BASE_URL": "http://ollama.test:11434",
        "OLLAMA_MODEL": "qwen3:14b",
        "GROQ_API_KEY": "gsk_test_SECRET_VALUE",
        "GROQ_MODEL": "qwen/qwen3-32b",
        "LLM_MAX_RETRIES": "2",
    }
    return load_settings(env=env, dotenv_path=tmp_path / "absent.env")


@pytest.fixture
def no_sleep() -> list[float]:
    return []
