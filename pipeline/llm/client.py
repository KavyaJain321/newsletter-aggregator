"""One LLM interface over local Ollama (primary) and Groq (fallback). Never Anthropic.

Transport per provider:
  - Ollama: native /api/chat - exposes Qwen3's `think` switch (thinking returned
    separately) and JSON-schema-constrained output via `format`.
  - Groq:   OpenAI-compatible /chat/completions with a real User-Agent
    (Cloudflare blocks default client UAs with error 1010).

Behaviour:
  - providers are tried in settings.llm_provider_order; an unavailable provider
    (down, bad key, model missing) is skipped immediately
  - 429/5xx/timeouts retry with backoff, honouring Retry-After
  - empty output (after stripping reasoning) retries once, then falls back
  - JSON requests are parsed with json_repair; unrecoverable JSON falls back
  - there is NO silent mock fallback: if nothing works, NoProviderAvailable is raised
  - every attempt is logged to settings.llm_log_dir (JSONL, git-ignored); no keys/headers
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

import requests

from ..config.settings import Settings
from .json_repair import JSONRepairError, parse_json, strip_reasoning

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) newsletter-aggregator-pipeline/0.1"
RETRY_STATUS = {429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    pass


class ProviderUnavailable(LLMError):
    """Provider can't serve this request (down, auth, model missing, bad request) — try the next."""


class EmptyOutput(LLMError):
    pass


class NoProviderAvailable(LLMError):
    pass


@dataclass
class ChatResult:
    text: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str
    data: Any
    provider: str
    model: str
    latency_ms: float
    usage: dict[str, Any]
    attempts: int


class Provider(Protocol):
    name: str
    model: str

    def chat(self, messages: list[dict[str, str]], *, json_mode: bool, schema: dict | None,
             think: bool | None, temperature: float, max_tokens: int) -> ChatResult: ...

    def health(self) -> tuple[bool, str]: ...


def _retry_after(resp: requests.Response, attempt: int) -> float:
    ra = resp.headers.get("retry-after", "")
    try:
        return min(float(ra), 30.0)
    except ValueError:
        return min(2.0 ** attempt, 30.0)


class _HTTPProvider:
    name = "http"

    def __init__(self, settings: Settings, session: requests.Session | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        self.s = settings
        self.session = session or requests.Session()
        self.sleep = sleep
        self.timeout = (10.0, settings.llm_timeout_s)

    def _request(self, method: str, url: str, **kw: Any) -> requests.Response:
        last: Exception | None = None
        for attempt in range(self.s.llm_max_retries + 1):
            try:
                resp = self.session.request(method, url, timeout=self.timeout, **kw)
            except requests.ConnectionError as e:
                raise ProviderUnavailable(f"{self.name}: cannot connect ({e.__class__.__name__})") from e
            except requests.Timeout as e:
                last = e
                if attempt < self.s.llm_max_retries:
                    self.sleep(min(2.0 ** attempt, 30.0))
                    continue
                raise ProviderUnavailable(f"{self.name}: timed out after {attempt + 1} attempts") from e
            if resp.status_code in RETRY_STATUS and attempt < self.s.llm_max_retries:
                self.sleep(_retry_after(resp, attempt))
                continue
            return resp
        raise ProviderUnavailable(f"{self.name}: retries exhausted ({last})")


class OllamaProvider(_HTTPProvider):
    name = "ollama"

    def __init__(self, settings: Settings, **kw: Any):
        super().__init__(settings, **kw)
        self.base = settings.ollama_base_url
        self.model = settings.ollama_model

    def chat(self, messages, *, json_mode, schema, think, temperature, max_tokens) -> ChatResult:
        body: dict[str, Any] = {
            "model": self.model, "messages": messages, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if schema is not None:
            body["format"] = schema
        elif json_mode:
            body["format"] = "json"
        if think is not None:
            body["think"] = think
        resp = self._request("POST", f"{self.base}/api/chat", json=body)
        if resp.status_code == 400 and "think" in body and "think" in resp.text.lower():
            body = {k: v for k, v in body.items() if k != "think"}  # model can't think: retry without
            resp = self._request("POST", f"{self.base}/api/chat", json=body)
        if resp.status_code == 404:
            raise ProviderUnavailable(f"ollama: model {self.model!r} not found on {self.base}")
        if resp.status_code != 200:
            raise ProviderUnavailable(f"ollama: HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        text = strip_reasoning((data.get("message") or {}).get("content") or "")
        usage = {"prompt_tokens": data.get("prompt_eval_count"), "completion_tokens": data.get("eval_count")}
        return ChatResult(text=text, model=data.get("model", self.model), usage=usage)

    def health(self) -> tuple[bool, str]:
        try:
            resp = self.session.get(f"{self.base}/api/tags", timeout=(3.0, 10.0))
        except requests.RequestException as e:
            if self.s.ollama_remote_ssh:  # on-demand host: stopped between runs by design
                from .remote_ollama import remote_health
                return remote_health(self.s)
            return False, f"not reachable at {self.base} ({e.__class__.__name__})"
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code} from {self.base}/api/tags"
        names = {m.get("name", "") for m in resp.json().get("models", [])}
        wanted = self.model if ":" in self.model else f"{self.model}:latest"
        if wanted not in names:
            have = ", ".join(sorted(names)) or "none"
            return False, f"reachable, but model {self.model!r} is not pulled (have: {have})"
        return True, f"{self.base} | {self.model}"


class GroqProvider(_HTTPProvider):
    name = "groq"

    def __init__(self, settings: Settings, **kw: Any):
        super().__init__(settings, **kw)
        self.base = settings.groq_base_url
        self.model = settings.groq_model

    def _headers(self) -> dict[str, str]:
        if not self.s.groq_api_key:
            raise ProviderUnavailable("groq: GROQ_API_KEY not set")
        return {"Authorization": f"Bearer {self.s.groq_api_key}", "User-Agent": USER_AGENT,
                "Content-Type": "application/json"}

    def chat(self, messages, *, json_mode, schema, think, temperature, max_tokens) -> ChatResult:
        headers = self._headers()
        body: dict[str, Any] = {"model": self.model, "messages": messages,
                                "temperature": temperature, "max_tokens": max_tokens}
        if json_mode or schema is not None:
            body["response_format"] = {"type": "json_object"}
        resp = self._request("POST", f"{self.base}/chat/completions", headers=headers, json=body)
        if resp.status_code == 400 and "response_format" in body:
            body = {k: v for k, v in body.items() if k != "response_format"}  # JSON mode rejected: rely on json_repair
            resp = self._request("POST", f"{self.base}/chat/completions", headers=headers, json=body)
        if resp.status_code in (401, 403):
            raise ProviderUnavailable(f"groq: HTTP {resp.status_code} (check GROQ_API_KEY)")
        if resp.status_code == 404:
            raise ProviderUnavailable(f"groq: model {self.model!r} not available")
        if resp.status_code != 200:
            raise ProviderUnavailable(f"groq: HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        text = strip_reasoning(data["choices"][0]["message"].get("content") or "")
        return ChatResult(text=text, model=data.get("model", self.model), usage=data.get("usage", {}))

    def health(self) -> tuple[bool, str]:
        if not self.s.groq_api_key:
            return False, "GROQ_API_KEY not set"
        try:
            resp = self.session.get(f"{self.base}/models", headers=self._headers(), timeout=(5.0, 15.0))
        except requests.RequestException as e:
            return False, f"not reachable ({e.__class__.__name__})"
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code} from {self.base}/models"
        ids = {m.get("id", "") for m in resp.json().get("data", [])}
        if self.model not in ids:
            return False, f"key OK, but model {self.model!r} is not offered"
        return True, f"{self.base} | {self.model}"


class MockProvider:
    """Test double, only ever passed in explicitly via LLMClient(providers=[...]).

    It is deliberately not selectable through LLM_PROVIDER_ORDER, so a missing
    model can never be papered over with fake output in a real run.
    """
    name = "mock"
    model = "mock"

    def __init__(self, replies: list[str | Exception] | None = None):
        self.replies = list(replies or [])
        self.calls: list[dict[str, Any]] = []

    def chat(self, messages, *, json_mode, schema, think, temperature, max_tokens) -> ChatResult:
        self.calls.append({"messages": messages, "json_mode": json_mode, "schema": schema, "think": think})
        if not self.replies:
            raise ProviderUnavailable("mock: no scripted replies left")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(text=strip_reasoning(reply), model="mock")

    def health(self) -> tuple[bool, str]:
        return True, "mock provider"


PROVIDERS: dict[str, Callable[..., Provider]] = {"ollama": OllamaProvider, "groq": GroqProvider}


class LLMClient:
    def __init__(self, settings: Settings, providers: list[Provider] | None = None):
        self.s = settings
        if providers is None:
            unknown = [p for p in settings.llm_provider_order if p not in PROVIDERS]
            if unknown:
                raise ValueError(f"unknown providers in LLM_PROVIDER_ORDER: {unknown}")
            providers = [PROVIDERS[p](settings) for p in settings.llm_provider_order]
        if not providers:
            raise ValueError("no LLM providers configured")
        self.providers = providers

    # ------------------------------------------------------------------ public
    def complete(self, *, system: str, user: str, purpose: str, input_ids: list[str] | None = None,
                 json_mode: bool = False, schema: dict | None = None, expect: str | None = None,
                 think: bool | None = None, temperature: float = 0.2, max_tokens: int = 4096) -> LLMResponse:
        """Run one completion. `purpose` names the prompt + version (e.g. "extract_card@v1")."""
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        think = self.s.llm_think if think is None else think
        want_json = json_mode or schema is not None
        failures: list[str] = []
        attempts = 0
        for provider in self.providers:
            for try_no in range(2):  # one extra try for empty output / unparseable JSON
                attempts += 1
                t0 = time.perf_counter()
                try:
                    res = provider.chat(messages, json_mode=want_json, schema=schema, think=think,
                                        temperature=temperature, max_tokens=max_tokens)
                    if not res.text.strip():
                        raise EmptyOutput(f"{provider.name}: empty output")
                    data = parse_json(res.text, expect=expect) if want_json else None
                except ProviderUnavailable as e:
                    self._log(purpose, input_ids, provider, None, t0, think, want_json, messages, None, str(e))
                    failures.append(str(e))
                    break  # next provider
                except (EmptyOutput, JSONRepairError) as e:
                    self._log(purpose, input_ids, provider, None, t0, think, want_json, messages, None, str(e))
                    failures.append(f"{provider.name}: {e}")
                    continue  # retry once on the same provider, then next provider
                latency = (time.perf_counter() - t0) * 1000
                self._log(purpose, input_ids, provider, res, t0, think, want_json, messages, res.text, None)
                return LLMResponse(text=res.text, data=data, provider=provider.name, model=res.model,
                                   latency_ms=round(latency, 1), usage=res.usage, attempts=attempts)
        raise NoProviderAvailable("all LLM providers failed: " + " | ".join(failures))

    def health(self) -> dict[str, tuple[bool, str]]:
        return {p.name: p.health() for p in self.providers}

    # ----------------------------------------------------------------- logging
    def _log(self, purpose, input_ids, provider, res, t0, think, want_json, messages, output, error) -> None:
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "purpose": purpose, "input_ids": list(input_ids or []),
            "provider": provider.name, "model": res.model if res else provider.model,
            "ok": error is None, "error": error,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "usage": res.usage if res else None, "think": think, "json": want_json,
            "output_chars": len(output) if output else 0,
        }
        if self.s.llm_log_text:
            record["messages"] = messages
            record["output"] = output
        log_dir: Path = self.s.llm_log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"{datetime.now(timezone.utc):%Y-%m-%d}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
