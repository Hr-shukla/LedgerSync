"""Mocked (never live) tests for the three-provider Tier 4 setup: priority
order, FORCE_AI_PROVIDER override, and that Groq's OpenAI-compatible
tool-call response gets normalized into the exact same structured shape
Claude/Gemini already produce -- so orchestrator.py never has to know which
provider actually answered.

No network calls happen here: requests.post is monkeypatched throughout.
Per the brief for this change, there is deliberately no live/opt-in Groq
test (unlike Gemini's) -- live verification is done manually.
"""
import json
from types import SimpleNamespace

from pipeline.ai_tier import AITier


def _clear_all_provider_keys(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "FORCE_AI_PROVIDER"):
        monkeypatch.delenv(var, raising=False)


class _FakeResponse:
    def __init__(self, status_code=200, json_body=None, headers=None):
        self.status_code = status_code
        self._json_body = json_body or {}
        self.headers = headers or {}

    def json(self):
        return self._json_body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _groq_tool_call_response(match=True, matched_ids=("C1",), confidence=0.9, reasoning="looks right"):
    args = json.dumps({"match": match, "matched_ids": list(matched_ids), "confidence": confidence, "reasoning": reasoning})
    return _FakeResponse(200, {
        "choices": [{
            "message": {
                "role": "assistant",
                "tool_calls": [{"id": "call_1", "type": "function",
                                 "function": {"name": "resolve_match", "arguments": args}}],
            },
            "finish_reason": "tool_calls",
        }],
    })


_CASE = {
    "record_id": "B1", "source": "bank", "amount": 1000.0, "date": "2026-01-05",
    "reference": "UTR1", "note": "test", "candidates": [{"id": "C1", "amount": 1000.0, "date": "2026-01-05"}],
}


def test_groq_activates_when_only_groq_key_present(monkeypatch):
    _clear_all_provider_keys(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fake_test_key")
    ai = AITier()
    assert ai.available is True
    assert ai.provider == "groq"


def test_groq_resolve_returns_same_shape_as_other_providers(monkeypatch):
    _clear_all_provider_keys(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fake_test_key")
    ai = AITier()

    monkeypatch.setattr("requests.post", lambda *a, **k: _groq_tool_call_response())
    result = ai.resolve(_CASE)

    assert set(result.keys()) >= {"match", "matched_ids", "confidence", "reasoning", "unavailable", "provider"}
    assert result["match"] is True
    assert result["matched_ids"] == ["C1"]
    assert result["confidence"] == 0.9
    assert result["unavailable"] is False
    assert result["provider"] == "groq"


def test_priority_order_anthropic_wins_when_multiple_keys_set(monkeypatch):
    _clear_all_provider_keys(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    ai = AITier()
    assert ai.provider == "anthropic"


def test_priority_order_gemini_wins_over_groq_when_no_anthropic(monkeypatch):
    _clear_all_provider_keys(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    ai = AITier()
    assert ai.provider == "gemini"


def test_force_ai_provider_env_var_overrides_priority_order(monkeypatch):
    _clear_all_provider_keys(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    monkeypatch.setenv("FORCE_AI_PROVIDER", "groq")
    ai = AITier()
    assert ai.provider == "groq"


def test_force_ai_provider_with_no_matching_key_is_unavailable(monkeypatch):
    _clear_all_provider_keys(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    monkeypatch.setenv("FORCE_AI_PROVIDER", "groq")
    ai = AITier()
    assert ai.available is False


def test_groq_api_key_never_leaks_into_error_message(monkeypatch):
    _clear_all_provider_keys(monkeypatch)
    secret = "gsk_super_secret_do_not_leak"
    monkeypatch.setenv("GROQ_API_KEY", secret)
    ai = AITier()

    def _boom(*a, **k):
        raise RuntimeError(f"connection failed for key={secret}")
    monkeypatch.setattr("requests.post", _boom)

    result = ai.resolve(_CASE)
    assert result["unavailable"] is True
    assert secret not in result["reasoning"]
    assert "REDACTED" in result["reasoning"]


def test_groq_429_with_long_retry_after_falls_back_to_next_model(monkeypatch):
    _clear_all_provider_keys(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fake_test_key")
    ai = AITier()

    calls = []

    def _fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json["model"])
        if json["model"] == ai.model:
            return _FakeResponse(429, {"error": {"message": "rate limited"}}, headers={"retry-after": "120"})
        return _groq_tool_call_response(match=False, matched_ids=[], confidence=0.2, reasoning="fallback model answered")

    monkeypatch.setattr("requests.post", _fake_post)
    result = ai.resolve(_CASE)

    assert len(calls) == 2, "should try the primary model once, then fall back -- not retry the exhausted one"
    assert result["unavailable"] is False
    assert result["reasoning"] == "fallback model answered"
