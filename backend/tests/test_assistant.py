"""
Tests for app.services.ai.assistant -- the conversational help/support
assistant, distinct from the structured-JSON report templates used by
Root Cause / Decision / Executive Advisor.
"""
from app.services.ai.assistant import (
    _keyword_fallback,
    answer_assistant_query,
    PRODUCT_KNOWLEDGE,
)


class _FakeUnavailableService:
    def is_available(self):
        return False


class _FakeAvailableService:
    class _Gemini:
        def __init__(self, response_text, error_info=None):
            self._response_text = response_text
            self._error_info = error_info

        def generate_content(self, prompt, system_instruction, temperature, max_tokens):
            return self._response_text, self._error_info

    def __init__(self, response_text="Here's how forecasting works in Kairos.", error_info=None):
        self.gemini = self._Gemini(response_text, error_info)

    def is_available(self):
        return True


# ── Keyword fallback (used when Gemini is unavailable) ─────────────────────


def test_keyword_fallback_matches_upload_question():
    answer = _keyword_fallback("how do I upload my data?")
    assert "Datasets page" in answer


def test_keyword_fallback_matches_forecast_question():
    answer = _keyword_fallback("can you forecast my revenue?")
    assert "Forecasting" in answer or "forecast" in answer.lower()


def test_keyword_fallback_matches_confidence_question():
    answer = _keyword_fallback("what does the confidence score mean?")
    assert "confidence" in answer.lower()


def test_keyword_fallback_unmatched_returns_default():
    answer = _keyword_fallback("what's the weather like today?")
    assert "Kairos" in answer


def test_keyword_fallback_is_case_insensitive():
    answer_lower = _keyword_fallback("how do i upload a file")
    answer_upper = _keyword_fallback("HOW DO I UPLOAD A FILE")
    assert answer_lower == answer_upper


# ── answer_assistant_query -- full behaviour, never raises ─────────────────


def test_empty_message_returns_prompt_without_calling_ai():
    result = answer_assistant_query("", ai_service=_FakeAvailableService())
    assert result["source"] == "fallback"
    assert result["reply"]


def test_whitespace_only_message_treated_as_empty():
    result = answer_assistant_query("   ", ai_service=_FakeAvailableService())
    assert result["source"] == "fallback"


def test_uses_keyword_fallback_when_service_unavailable():
    result = answer_assistant_query("how do I forecast?", ai_service=_FakeUnavailableService())
    assert result["source"] == "fallback"
    assert "Forecast" in result["reply"] or "forecast" in result["reply"].lower()


def test_uses_keyword_fallback_when_ai_service_is_none():
    """Defensive: a None service (e.g. misconfigured DI) must not crash the assistant."""
    result = answer_assistant_query("how do I forecast?", ai_service=None)
    assert result["source"] == "fallback"


def test_uses_ai_reply_when_service_available_and_succeeds():
    service = _FakeAvailableService(response_text="Kairos forecasts automatically.")
    result = answer_assistant_query("how does forecasting work?", ai_service=service)
    assert result["source"] == "ai"
    assert result["reply"] == "Kairos forecasts automatically."


def test_falls_back_when_ai_returns_error_info():
    service = _FakeAvailableService(response_text=None, error_info={"error": "timeout"})
    result = answer_assistant_query("how does forecasting work?", ai_service=service)
    assert result["source"] == "fallback"


def test_falls_back_when_ai_returns_empty_text():
    service = _FakeAvailableService(response_text="   ")
    result = answer_assistant_query("how does forecasting work?", ai_service=service)
    assert result["source"] == "fallback"


def test_never_raises_when_gemini_client_throws():
    class ThrowingService:
        class _Gemini:
            def generate_content(self, **kwargs):
                raise RuntimeError("network exploded")

        gemini = _Gemini()

        def is_available(self):
            return True

    result = answer_assistant_query("how does forecasting work?", ai_service=ThrowingService())
    assert result["source"] == "fallback"
    assert result["reply"]


def test_history_and_dataset_context_dont_crash_ai_path():
    service = _FakeAvailableService(response_text="Your revenue trend looks healthy.")
    result = answer_assistant_query(
        "what's happening with my revenue?",
        ai_service=service,
        history=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}],
        dataset_summary="'sales.csv': Sales & Revenue, 200 rows. Key measures: revenue, units.",
        current_page="Dashboard",
    )
    assert result["source"] == "ai"


def test_product_knowledge_mentions_every_major_page():
    for page in ["Datasets", "KPI Analytics", "Forecasting", "Root Cause", "What-If Simulation", "Decision Advisor", "Executive Advisor"]:
        assert page in PRODUCT_KNOWLEDGE
