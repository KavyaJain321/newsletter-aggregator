import json

import pytest
import requests

from pipeline.llm.client import (EmptyOutput, GroqProvider, LLMClient, MockProvider,
                                 NoProviderAvailable, OllamaProvider, ProviderUnavailable,
                                 USER_AGENT)
from tests.conftest import FakeResp, FakeSession


def _ollama_ok(content: str, model: str = "qwen3:14b") -> FakeResp:
    return FakeResp(200, {"model": model, "message": {"content": content}, "prompt_eval_count": 5, "eval_count": 7})


def _groq_ok(content: str) -> FakeResp:
    return FakeResp(200, {"model": "qwen/qwen3-32b", "choices": [{"message": {"content": content}}],
                          "usage": {"total_tokens": 12}})


def _client(settings, sess, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    o = OllamaProvider(settings, session=sess, sleep=sleeps.append)
    g = GroqProvider(settings, session=sess, sleep=sleeps.append)
    return LLMClient(settings, providers=[o, g])


def _read_logs(settings):
    files = list(settings.llm_log_dir.glob("*.jsonl"))
    return [json.loads(l) for f in files for l in f.read_text(encoding="utf-8").splitlines()]


def test_ollama_primary_json(settings):
    sess = FakeSession().add("POST", "/api/chat", _ollama_ok('{"ok": true}'))
    r = _client(settings, sess).complete(system="s", user="u", purpose="t@v1", json_mode=True, expect="object")
    assert r.provider == "ollama" and r.data == {"ok": True}
    body = sess.calls[0]["json"]
    assert body["format"] == "json" and body["think"] is True and body["stream"] is False


def test_schema_passed_as_ollama_format(settings):
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    sess = FakeSession().add("POST", "/api/chat", _ollama_ok('{"ok": false}'))
    _client(settings, sess).complete(system="s", user="u", purpose="t", schema=schema)
    assert sess.calls[0]["json"]["format"] == schema


def test_falls_back_to_groq_when_ollama_down(settings):
    sess = FakeSession().add("POST", "/api/chat", requests.ConnectionError("refused")) \
                        .add("POST", "/chat/completions", _groq_ok('{"ok": true}'))
    r = _client(settings, sess).complete(system="s", user="u", purpose="t", json_mode=True)
    assert r.provider == "groq" and r.data == {"ok": True}
    groq_call = sess.calls[-1]
    assert groq_call["headers"]["User-Agent"] == USER_AGENT
    assert groq_call["json"]["response_format"] == {"type": "json_object"}


def test_ollama_model_missing_falls_back(settings):
    sess = FakeSession().add("POST", "/api/chat", FakeResp(404, {"error": "model not found"})) \
                        .add("POST", "/chat/completions", _groq_ok("hello"))
    assert _client(settings, sess).complete(system="s", user="u", purpose="t").provider == "groq"


def test_think_unsupported_retries_without_think(settings):
    sess = FakeSession().add("POST", "/api/chat",
                             FakeResp(400, {"error": "x"}, text='{"error":"model does not support thinking"}'),
                             _ollama_ok("plain answer"))
    r = _client(settings, sess).complete(system="s", user="u", purpose="t")
    assert r.text == "plain answer"
    assert "think" in sess.calls[0]["json"] and "think" not in sess.calls[1]["json"]


def test_reasoning_stripped_from_content(settings):
    sess = FakeSession().add("POST", "/api/chat", _ollama_ok("<think>hmm</think>final"))
    assert _client(settings, sess).complete(system="s", user="u", purpose="t").text == "final"


def test_rate_limit_retry_honours_retry_after(settings):
    sleeps: list[float] = []
    sess = FakeSession().add("POST", "/api/chat", FakeResp(429, {"e": 1}, headers={"retry-after": "1.5"}),
                             _ollama_ok("ok"))
    r = _client(settings, sess, sleeps).complete(system="s", user="u", purpose="t")
    assert r.text == "ok" and sleeps == [1.5]


def test_empty_output_retries_then_falls_back(settings):
    sess = FakeSession().add("POST", "/api/chat", _ollama_ok("   "), _ollama_ok("<think>only</think>")) \
                        .add("POST", "/chat/completions", _groq_ok("real"))
    r = _client(settings, sess).complete(system="s", user="u", purpose="t")
    assert r.provider == "groq" and r.attempts == 3


def test_bad_json_retries_then_falls_back(settings):
    sess = FakeSession().add("POST", "/api/chat", _ollama_ok("not json"), _ollama_ok("still not")) \
                        .add("POST", "/chat/completions", _groq_ok('{"a": 1}'))
    r = _client(settings, sess).complete(system="s", user="u", purpose="t", json_mode=True)
    assert r.provider == "groq" and r.data == {"a": 1}


def test_groq_drops_json_mode_if_rejected(settings):
    sess = FakeSession().add("POST", "/api/chat", requests.ConnectionError()) \
                        .add("POST", "/chat/completions", FakeResp(400, {"error": "response_format unsupported"}),
                             _groq_ok('{"a": 2}'))
    r = _client(settings, sess).complete(system="s", user="u", purpose="t", json_mode=True)
    assert r.data == {"a": 2}
    assert "response_format" not in sess.calls[-1]["json"]


def test_all_fail_raises_no_silent_mock(settings):
    sess = FakeSession().add("POST", "/api/chat", requests.ConnectionError()) \
                        .add("POST", "/chat/completions", FakeResp(401, {"error": "bad key"}))
    with pytest.raises(NoProviderAvailable, match="ollama.*groq"):
        _client(settings, sess).complete(system="s", user="u", purpose="t")


def test_groq_without_key_is_unavailable(settings):
    from dataclasses import replace
    s = replace(settings, groq_api_key=None)
    with pytest.raises(ProviderUnavailable, match="GROQ_API_KEY"):
        GroqProvider(s, session=FakeSession()).chat([], json_mode=False, schema=None, think=None,
                                                    temperature=0, max_tokens=8)


def test_logs_written_without_secrets(settings):
    sess = FakeSession().add("POST", "/api/chat", requests.ConnectionError()) \
                        .add("POST", "/chat/completions", _groq_ok("hi"))
    _client(settings, sess).complete(system="s", user="u", purpose="extract_card@v1", input_ids=["msg1"])
    logs = _read_logs(settings)
    assert [l["provider"] for l in logs] == ["ollama", "groq"]
    assert logs[0]["ok"] is False and logs[1]["ok"] is True
    assert logs[1]["purpose"] == "extract_card@v1" and logs[1]["input_ids"] == ["msg1"]
    raw = "".join(f.read_text(encoding="utf-8") for f in settings.llm_log_dir.glob("*.jsonl"))
    assert "SECRET_VALUE" not in raw and "Bearer" not in raw


def test_settings_repr_masks_key(settings):
    assert "SECRET_VALUE" not in repr(settings)


def test_health_checks(settings):
    sess = FakeSession().add("GET", "/api/tags", FakeResp(200, {"models": [{"name": "llama3.1:8b"}]})) \
                        .add("GET", "/models", FakeResp(200, {"data": [{"id": "qwen/qwen3-32b"}]}))
    h = _client(settings, sess).health()
    assert h["ollama"][0] is False and "not pulled" in h["ollama"][1]
    assert h["groq"][0] is True


def test_unknown_provider_rejected(settings):
    from dataclasses import replace
    with pytest.raises(ValueError, match="unknown providers"):
        LLMClient(replace(settings, llm_provider_order=("mock",)))


def test_mock_provider_injection(settings):
    m = MockProvider(['{"x": 1}'])
    r = LLMClient(settings, providers=[m]).complete(system="s", user="u", purpose="t", json_mode=True)
    assert r.data == {"x": 1} and m.calls[0]["json_mode"] is True


def test_empty_output_is_llm_error():
    assert issubclass(EmptyOutput, Exception)


def test_remote_mode_never_calls_the_shared_port(settings):
    from dataclasses import replace
    s = replace(settings, ollama_remote_ssh="gpuuser@gpu-host.test", ollama_base_url="http://gpu-host.test:11434")
    sess = FakeSession()
    with pytest.raises(ProviderUnavailable, match="llm_session"):
        OllamaProvider(s, session=sess).chat([{"role": "user", "content": "x"}], json_mode=False, schema=None,
                                             think=False, temperature=0, max_tokens=8)
    assert sess.calls == []
