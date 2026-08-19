"""
Tests for Module 6: AI Decision Intelligence.

All AI endpoints must return HTTP 200 with the correct schema even when
Gemini is not configured (GEMINI_API_KEY is empty in tests). The service
layer returns a graceful degraded response instead of raising an exception.
"""
import io
import pytest
import pandas as pd

SAMPLE_CSV = (
    "date,product_id,sales,quantity\n"
    "2024-01-01,PROD-1,1000,100\n"
    "2024-01-02,PROD-2,1100,110\n"
    "2024-01-03,PROD-1,900,90\n"
    "2024-01-04,PROD-3,1200,120\n"
    "2024-01-05,PROD-2,1050,105\n"
    "2024-01-06,PROD-1,1300,130\n"
    "2024-01-07,PROD-3,1150,115\n"
    "2024-01-08,PROD-2,1250,125\n"
    "2024-01-09,PROD-1,1100,110\n"
    "2024-01-10,PROD-3,1400,140\n"
)

_REQUIRED_KEYS = {"summary", "insights", "recommendations", "visualizations", "metadata"}


def _upload_sample(client, headers, csv_content=SAMPLE_CSV):
    files = {"file": ("sample.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    data = {"dataset_type": "orders"}
    response = client.post("/api/v1/datasets/upload", files=files, data=data, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ── health & usage ──────────────────────────────────────────────────────────


def test_ai_health_returns_200(client):
    response = client.get("/api/v1/ai/health")
    assert response.status_code == 200
    body = response.json()
    assert "available" in body
    assert "configured" in body


def test_ai_health_structure_when_key_absent(client):
    """Without an API key the health endpoint must still return 200."""
    response = client.get("/api/v1/ai/health")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["available"] is False
    assert "sdk_version" in body


def test_ai_usage_requires_auth(client):
    response = client.get("/api/v1/ai/usage")
    assert response.status_code == 401


def test_ai_usage_returns_200_when_authenticated(client, admin_headers):
    response = client.get("/api/v1/ai/usage", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "available" in body
    assert "requests" in body
    assert "errors" in body
    assert "sdk" in body
    assert body["sdk"] == "google-genai"


# ── authentication guard ────────────────────────────────────────────────────


def test_ai_summary_requires_auth(client, admin_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.get(f"/api/v1/ai/{dataset_id}/summary")
    assert response.status_code == 401


# ── all dataset-level endpoints return 200 with correct schema ───────────────


def _assert_response(body: dict):
    """Shared assertion for every AI endpoint response."""
    assert _REQUIRED_KEYS.issubset(body.keys()), f"Missing keys: {_REQUIRED_KEYS - body.keys()}"
    assert isinstance(body["summary"], str)
    assert len(body["summary"]) > 0
    assert isinstance(body["insights"], list)
    assert isinstance(body["recommendations"], list)
    assert isinstance(body["visualizations"], list)
    assert isinstance(body["metadata"], dict)
    # Metadata must always contain these fields
    meta = body["metadata"]
    assert "template" in meta
    assert "insight_count" in meta
    assert "recommendation_count" in meta
    assert "health_score" in meta
    # confidence, if present, must be an int (not float)
    if meta.get("confidence") is not None:
        assert isinstance(meta["confidence"], int), (
            f"confidence must be int, got {type(meta['confidence'])}"
        )


def test_ai_summary_structure(client, admin_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.get(f"/api/v1/ai/{dataset_id}/summary", headers=admin_headers)
    assert response.status_code == 200
    _assert_response(response.json())
    assert response.json()["metadata"]["template"] == "executive_summary"


def test_ai_question_structure(client, admin_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.post(
        f"/api/v1/ai/{dataset_id}/question",
        json={"question": "What is the sales trend?"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    _assert_response(response.json())
    assert response.json()["metadata"]["template"] == "question_answering"


def test_ai_analyze_business_insights(client, admin_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.post(
        f"/api/v1/ai/{dataset_id}/analyze",
        json={"template_name": "business_insights"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    _assert_response(response.json())


def test_ai_analyze_all_valid_templates(client, admin_headers):
    """Every valid template_name must return 200."""
    dataset_id = _upload_sample(client, admin_headers)
    valid_templates = [
        "executive_summary",
        "business_insights",
        "root_cause_analysis",
        "recommendations",
        "risk_analysis",
        "opportunity_analysis",
        "question_answering",
        "anomaly_detection",
    ]
    for template in valid_templates:
        response = client.post(
            f"/api/v1/ai/{dataset_id}/analyze",
            json={"template_name": template, "custom_query": "test"},
            headers=admin_headers,
        )
        assert response.status_code == 200, f"template '{template}' returned {response.status_code}"
        _assert_response(response.json())


def test_ai_analyze_invalid_template_returns_422(client, admin_headers):
    """Invalid template_name must return 422, not 200."""
    dataset_id = _upload_sample(client, admin_headers)
    response = client.post(
        f"/api/v1/ai/{dataset_id}/analyze",
        json={"template_name": "nonexistent_template"},
        headers=admin_headers,
    )
    assert response.status_code == 422, (
        f"Expected 422 for invalid template, got {response.status_code}"
    )


def test_ai_risks_structure(client, admin_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.get(f"/api/v1/ai/{dataset_id}/risks", headers=admin_headers)
    assert response.status_code == 200
    _assert_response(response.json())
    assert response.json()["metadata"]["template"] == "risk_analysis"


def test_ai_opportunities_structure(client, admin_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.get(f"/api/v1/ai/{dataset_id}/opportunities", headers=admin_headers)
    assert response.status_code == 200
    _assert_response(response.json())
    assert response.json()["metadata"]["template"] == "opportunity_analysis"


def test_ai_anomalies_structure(client, admin_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.get(f"/api/v1/ai/{dataset_id}/anomalies", headers=admin_headers)
    assert response.status_code == 200
    _assert_response(response.json())
    assert response.json()["metadata"]["template"] == "anomaly_detection"


def test_ai_recommendations_structure(client, admin_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.get(f"/api/v1/ai/{dataset_id}/recommendations", headers=admin_headers)
    assert response.status_code == 200
    _assert_response(response.json())
    assert response.json()["metadata"]["template"] == "recommendations"


def test_ai_health_score_present_in_metadata(client, admin_headers):
    """health_score must be included in every response metadata."""
    dataset_id = _upload_sample(client, admin_headers)
    response = client.get(f"/api/v1/ai/{dataset_id}/summary", headers=admin_headers)
    assert response.status_code == 200
    meta = response.json()["metadata"]
    assert "health_score" in meta
    hs = meta["health_score"]
    assert "overall" in hs
    assert "rating" in hs
    assert 0 <= hs["overall"] <= 100
    # operational_score must never be negative
    assert hs.get("operational_score", 0) >= 0
    assert hs.get("financial_score", 0) >= 0
    assert hs.get("risk_score", 0) >= 0


def test_ai_visualizations_are_list_of_dicts(client, admin_headers):
    """visualizations must be a list; each entry must have chart_type and title."""
    dataset_id = _upload_sample(client, admin_headers)
    response = client.get(f"/api/v1/ai/{dataset_id}/summary", headers=admin_headers)
    assert response.status_code == 200
    vis = response.json()["visualizations"]
    assert isinstance(vis, list)
    for v in vis:
        assert "chart_type" in v
        assert "title" in v


def test_ai_metadata_insight_count_matches_insights(client, admin_headers):
    """insight_count in metadata must match len(insights)."""
    dataset_id = _upload_sample(client, admin_headers)
    response = client.get(f"/api/v1/ai/{dataset_id}/risks", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["insight_count"] == len(body["insights"])
    assert body["metadata"]["recommendation_count"] == len(body["recommendations"])


# ── context builder unit tests ───────────────────────────────────────────────


def test_context_builder_numeric_ranges_partial(client, admin_headers):
    """Context builder must survive columns where all values are NaN (excluded from numeric_ranges)."""
    # Upload CSV with an all-NaN numeric column
    csv = "date,sales,empty\n2024-01-01,100,\n2024-01-02,200,\n" * 5
    dataset_id = _upload_sample(client, admin_headers, csv)
    response = client.get(f"/api/v1/ai/{dataset_id}/summary", headers=admin_headers)
    assert response.status_code == 200


def test_business_health_score_always_in_range():
    """Business health score components must all be in 0-100."""
    from app.services.ai.context_builder import _business_health_score

    # Extreme case: very high duplicates, no quality
    result = _business_health_score(
        quality_score=0.0,
        missing_rate=100.0,
        duplicate_rows=10000,
        total_rows=100,
        trend_direction="decreasing",
        outlier_pct=100.0,
    )
    assert result["overall"] >= 0
    assert result["overall"] <= 100
    assert result["operational_score"] >= 0, "operational_score must never be negative"
    assert result["financial_score"] >= 0
    assert result["risk_score"] >= 0

    # Extreme case: perfect data
    result = _business_health_score(
        quality_score=100.0,
        missing_rate=0.0,
        duplicate_rows=0,
        total_rows=1000,
        trend_direction="increasing",
        outlier_pct=0.0,
    )
    assert result["overall"] <= 100
    assert result["operational_score"] <= 100
    assert result["financial_score"] <= 100


def test_response_parser_float_confidence_coerced():
    """Float confidence from Gemini must be coerced to int, not cause ValidationError."""
    from app.services.ai.response_parser import parse_to_response
    # Gemini returns confidence as float
    raw = '{"executive_summary": "Revenue is growing.", "confidence": 87.5}'
    result = parse_to_response(raw, "executive_summary", {})
    conf = result["metadata"]["confidence"]
    # Must be int or None, never a float that would break the schema
    assert conf is None or isinstance(conf, int), f"Expected int/None, got {type(conf)}: {conf}"


def test_response_parser_empty_gemini_response():
    """Empty string from Gemini must produce valid fallback response."""
    from app.services.ai.response_parser import parse_to_response
    result = parse_to_response("", "executive_summary", {})
    assert isinstance(result["summary"], str)
    assert isinstance(result["insights"], list)


def test_response_parser_plain_prose_fallback():
    """Plain prose (no JSON) must produce a usable response, not crash."""
    from app.services.ai.response_parser import parse_to_response
    result = parse_to_response(
        "Revenue is growing 15% YoY. The business is healthy.",
        "executive_summary",
        {},
    )
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0


def test_response_parser_fenced_json():
    """Markdown-fenced JSON from Gemini must be parsed correctly."""
    from app.services.ai.response_parser import parse_to_response
    fenced = '```json\n{"executive_summary": "Test.", "confidence": 90}\n```'
    result = parse_to_response(fenced, "executive_summary", {})
    assert "Test." in result["summary"]


# ── isolation & 404 ─────────────────────────────────────────────────────────


def test_ai_cross_org_isolation(client, admin_headers, other_org_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.get(
        f"/api/v1/ai/{dataset_id}/summary",
        headers=other_org_headers,
    )
    assert response.status_code == 404


def test_ai_nonexistent_dataset(client, admin_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/ai/{fake_id}/summary", headers=admin_headers)
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Assistant chat -- conversational help, works with or without a dataset,
# with or without Gemini configured
# ─────────────────────────────────────────────────────────────────────────────


def test_assistant_chat_requires_auth(client):
    response = client.post("/api/v1/ai/assistant/chat", json={"message": "hi"})
    assert response.status_code == 401


def test_assistant_chat_without_dataset(client, admin_headers):
    response = client.post(
        "/api/v1/ai/assistant/chat",
        json={"message": "how do I upload data?"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "reply" in body
    assert len(body["reply"]) > 0
    assert body["source"] in ("ai", "fallback")


def test_assistant_chat_with_dataset(client, admin_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.post(
        "/api/v1/ai/assistant/chat",
        json={"message": "what can you tell me about this dataset?", "dataset_id": dataset_id},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["reply"]


def test_assistant_chat_nonexistent_dataset_returns_404(client, admin_headers):
    response = client.post(
        "/api/v1/ai/assistant/chat",
        json={"message": "hi", "dataset_id": "00000000-0000-0000-0000-000000000000"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_assistant_chat_cross_org_dataset_returns_404(client, admin_headers, other_org_headers):
    dataset_id = _upload_sample(client, admin_headers)
    response = client.post(
        "/api/v1/ai/assistant/chat",
        json={"message": "hi", "dataset_id": dataset_id},
        headers=other_org_headers,
    )
    assert response.status_code == 404


def test_assistant_chat_with_history(client, admin_headers):
    response = client.post(
        "/api/v1/ai/assistant/chat",
        json={
            "message": "and what about forecasting?",
            "history": [
                {"role": "user", "content": "what is root cause analysis?"},
                {"role": "assistant", "content": "It explains why a metric changed."},
            ],
        },
        headers=admin_headers,
    )
    assert response.status_code == 200


def test_assistant_chat_empty_message_still_returns_200(client, admin_headers):
    response = client.post(
        "/api/v1/ai/assistant/chat",
        json={"message": ""},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["reply"]


def test_assistant_chat_missing_message_returns_422(client, admin_headers):
    response = client.post("/api/v1/ai/assistant/chat", json={}, headers=admin_headers)
    assert response.status_code == 422


def test_assistant_chat_falls_back_without_gemini_configured(client, admin_headers):
    """GEMINI_API_KEY is empty in the test environment, so every chat
    response here must come from the keyword fallback, never crash."""
    response = client.post(
        "/api/v1/ai/assistant/chat",
        json={"message": "how do I run a what-if simulation?"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
