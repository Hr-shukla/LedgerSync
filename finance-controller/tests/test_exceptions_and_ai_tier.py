"""Tests for Tier 5 exception classification and Tier 4's honest degradation
when no ANTHROPIC_API_KEY is configured."""
from pipeline import exceptions
from pipeline.ai_tier import AITier


def test_classify_chargeback():
    code, detail = exceptions.classify(is_chargeback=True)
    assert code == "chargeback_dispute"


def test_classify_no_candidate():
    code, detail = exceptions.classify(had_any_candidate=False)
    assert code == "no_counterpart_found"


def test_classify_low_ai_confidence():
    ai_result = {"match": True, "confidence": 0.4, "reasoning": "weak signal"}
    code, detail = exceptions.classify(ai_result=ai_result)
    assert code == "low_ai_confidence"
    assert "0.40" in detail


def test_classify_ai_rejected():
    ai_result = {"match": False, "confidence": 0.1, "reasoning": "unrelated transactions"}
    code, detail = exceptions.classify(ai_result=ai_result)
    assert code == "ai_rejected_no_match"


def test_classify_ai_unavailable():
    ai_result = {"unavailable": True, "reasoning": "no key"}
    code, detail = exceptions.classify(ai_result=ai_result)
    assert code == "ai_unavailable_needs_review"


def test_ai_tier_degrades_honestly_without_api_key(monkeypatch):
    """No hallucinated matches: with no API key, the AI tier must report
    itself unavailable rather than fabricate a match/no-match decision.

    Deletes all three provider env vars, not just ANTHROPIC_API_KEY -- this
    test must not assume nothing else in the suite has touched os.environ.
    Importing api.main (see tests/test_api.py) loads .env as a side effect,
    which previously leaked a real GEMINI_API_KEY into the rest of the
    pytest process and made this test fail depending on run order."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    ai = AITier(api_key=None)
    assert ai.available is False
    result = ai.resolve({
        "record_id": "B1", "source": "bank", "amount": 100.0, "date": "2026-01-01",
        "reference": "UTR1", "candidates": [], "note": "test",
    })
    assert result["match"] is False
    assert result["unavailable"] is True
    assert result["confidence"] == 0.0
