"""Provider-agnostic LLM wrapper (OpenAI-compatible) + a mock, + call logging.

Per PROJECT brief §14: never hard-code a provider; log model/provider/prompt-
version/tokens/latency/input-ids for every call. Swap providers by changing
base_url/model/key in .env. `get_llm()` returns a real client if a key is set,
else the MockLLM so downstream stages run offline.
"""
from __future__ import annotations
import json
import time
import urllib.request
from dataclasses import dataclass

from . import config

LOG_PATH = config.LOGS / "llm_calls.jsonl"


def _log(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


@dataclass
class LLMResult:
    text: str
    meta: dict


class BaseLLM:
    name = "base"

    def complete(self, system: str, user: str, *, prompt_version: str,
                 input_ids: list[str] | None = None, model: str | None = None,
                 temperature: float = 0.2) -> LLMResult:
        raise NotImplementedError

    def _record(self, *, provider, model, prompt_version, input_ids,
                latency_ms, usage, text) -> dict:
        meta = {
            "provider": provider, "model": model, "prompt_version": prompt_version,
            "input_ids": input_ids or [], "latency_ms": round(latency_ms, 1),
            "usage": usage, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        _log({**meta, "output_preview": text[:280]})
        return meta


class OpenAICompatibleLLM(BaseLLM):
    """Works with Groq, OpenAI, Together, local Ollama (/v1), etc."""
    name = "openai-compatible"

    def __init__(self, base_url: str, model: str, api_key: str,
                 reasoning_effort: str | None = None, no_think: bool = False):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        # reasoning models (e.g. local gpt-oss) over-think extraction; "low"
        # keeps them fast + on-topic. Ignored by providers that don't use it.
        self.reasoning_effort = reasoning_effort
        # qwen3 thinking mode is slow for mechanical extraction; "/no_think"
        # in the prompt turns it off. Harmless text for non-qwen models.
        self.no_think = no_think

    def complete(self, system, user, *, prompt_version, input_ids=None,
                 model=None, temperature=0.2) -> LLMResult:
        model = model or self.model
        body = {
            "model": model, "temperature": temperature,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        if self.no_think:
            body["think"] = False   # ollama-native switch (qwen3 etc.)
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=payload,
            headers={"Authorization": "Bearer " + self.api_key,
                     "Content-Type": "application/json",
                     # Groq sits behind Cloudflare; the default urllib UA gets
                     # blocked with error 1010. A real UA clears it.
                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                   "newsletter-aggregator/0.1"})
        t0 = time.time()
        data = None
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req) as resp:
                    data = json.load(resp)
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503):
                    ra = e.headers.get("retry-after")
                    wait = float(ra) if ra and ra.replace(".", "").isdigit() else 3.0 * (attempt + 1)
                    time.sleep(min(wait, 30.0))
                    continue
                raise
        if data is None:
            raise RuntimeError("LLM call failed after retries (rate limit?)")
        latency = (time.time() - t0) * 1000
        text = data["choices"][0]["message"]["content"]
        meta = self._record(provider=self.base_url, model=model,
                            prompt_version=prompt_version, input_ids=input_ids,
                            latency_ms=latency, usage=data.get("usage", {}), text=text)
        return LLMResult(text=text, meta=meta)


class MockLLM(BaseLLM):
    """Offline stand-in. Returns a deterministic sentinel so callers fall back
    to the heuristic path; still logs the call for parity."""
    name = "mock"

    def complete(self, system, user, *, prompt_version, input_ids=None,
                 model=None, temperature=0.2) -> LLMResult:
        meta = self._record(provider="mock", model="mock", prompt_version=prompt_version,
                            input_ids=input_ids, latency_ms=0.0, usage={}, text="[MOCK]")
        return LLMResult(text="[MOCK]", meta=meta)


def get_llm() -> BaseLLM:
    s = config.llm_settings()
    if s["api_key"]:
        return OpenAICompatibleLLM(s["base_url"], s["model"], s["api_key"],
                                   reasoning_effort=s.get("reasoning_effort"),
                                   no_think=s.get("no_think", False))
    return MockLLM()


def available() -> bool:
    return bool(config.llm_settings()["api_key"])
