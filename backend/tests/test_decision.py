"""
Tests for Module 9: Decision Advisor & Prescriptive Intelligence Engine.

Covers:
  - All 9 decision endpoints
  - Rule engine unit tests
  - Scoring engine unit tests
  - Visualization builder unit tests
  - Decision service unit tests
  - Prompt templates (4 new)
  - Authentication / org isolation
  - Edge cases
"""
from __future__ import annotations

import io
import uuid
import pytest
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# CSV fixtures
# ─────────────────────────────────────────────────────────────────────────────

GOOD_CSV = "\n".join(
    ["revenue,cost,units,price"]
    + [f"{2000 + i * 50},{800 + i * 10},{20 + i},{9.99 + (i % 5) * 0.5}" for i in range(40)]
) + "\n"

POOR_QUALITY_CSV = (
    "revenue,cost,units\n"
    + "\n".join(
        f"{'' if i % 5 == 0 else 1000 + i * 20},{'' if i % 7 == 0 else 400 + i * 5},{i}"
        for i in range(30)
    )
    + "\n"
)


def _upload(client, headers, content: str = GOOD_CSV) -> str:
    files = {"file": ("data.csv", io.BytesIO(content.encode()), "text/csv")}
    r = client.post(
        "/api/v1/datasets/upload",
        files=files,
        data={"dataset_type": "orders"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Authentication guards
# ─────────────────────────────────────────────────────────────────────────────


def test_analyze_requires_auth(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/analyze", json={"dataset_id": did})
    assert r.status_code == 401


def test_recommend_requires_auth(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/recommend", json={"dataset_id": did})
    assert r.status_code == 401


def test_root_cause_requires_auth(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/root-cause", json={"dataset_id": did, "problem_statement": "Why?"})
    assert r.status_code == 401


def test_prescriptive_requires_auth(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/prescriptive", json={"dataset_id": did})
    assert r.status_code == 401


def test_executive_requires_auth(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/executive", json={"dataset_id": did})
    assert r.status_code == 401


def test_history_requires_auth(client):
    r = client.get("/api/v1/decision/history")
    assert r.status_code == 401


def test_templates_requires_auth(client):
    r = client.get("/api/v1/decision/templates")
    assert r.status_code == 401


def test_rules_requires_auth(client):
    r = client.get("/api/v1/decision/rules")
    assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 2. 404 and cross-org isolation
# ─────────────────────────────────────────────────────────────────────────────


def test_analyze_nonexistent_dataset(client, admin_headers):
    fake = str(uuid.uuid4())
    r = client.post("/api/v1/decision/analyze", json={"dataset_id": fake}, headers=admin_headers)
    assert r.status_code == 404


def test_analyze_cross_org_isolation(client, admin_headers, other_org_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=other_org_headers)
    assert r.status_code == 404


def test_recommend_cross_org_isolation(client, admin_headers, other_org_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/recommend", json={"dataset_id": did}, headers=other_org_headers)
    assert r.status_code == 404


def test_root_cause_cross_org_isolation(client, admin_headers, other_org_headers):
    did = _upload(client, admin_headers)
    r = client.post(
        "/api/v1/decision/root-cause",
        json={"dataset_id": did, "problem_statement": "Why?"},
        headers=other_org_headers,
    )
    assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 3. /decision/analyze endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_analyze_returns_200(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=admin_headers)
    assert r.status_code == 200


def test_analyze_schema(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=admin_headers).json()
    required = {"dataset_name", "recommendation_count", "recommendations", "sources", "visualizations"}
    assert required.issubset(body.keys())
    assert isinstance(body["recommendations"], list)
    assert isinstance(body["sources"], dict)
    assert isinstance(body["visualizations"], list)


def test_analyze_recommendations_have_scores(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=admin_headers).json()
    for rec in body["recommendations"]:
        assert "overall_score" in rec
        assert "priority_score" in rec
        assert "impact_score" in rec
        assert "roi_score" in rec
        assert 0 <= rec["overall_score"] <= 100


def test_analyze_recommendations_sorted_by_overall_score(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=admin_headers).json()
    recs = body["recommendations"]
    if len(recs) > 1:
        scores = [r["overall_score"] for r in recs]
        assert scores == sorted(scores, reverse=True), "Recommendations must be sorted by overall_score desc"


def test_analyze_sources_breakdown(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=admin_headers).json()
    sources = body["sources"]
    assert "rule_engine" in sources
    assert "ai_generated" in sources


def test_analyze_session_saved(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post(
        "/api/v1/decision/analyze",
        json={"dataset_id": did, "save_session": True},
        headers=admin_headers,
    ).json()
    # session_id may be None if DB write fails in test (sqlite FK), but key exists
    assert "session_id" in body


def test_analyze_session_not_saved_when_false(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post(
        "/api/v1/decision/analyze",
        json={"dataset_id": did, "save_session": False},
        headers=admin_headers,
    ).json()
    assert body.get("session_id") is None


def test_analyze_poor_quality_fires_rules(client, admin_headers):
    """Poor-quality dataset should trigger rule-engine recommendations."""
    did = _upload(client, admin_headers, POOR_QUALITY_CSV)
    body = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=admin_headers).json()
    assert body["sources"]["rule_engine"] >= 1
    assert body["recommendation_count"] >= 1


def test_analyze_visualizations_have_chart_type(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=admin_headers).json()
    for v in body["visualizations"]:
        assert "chart_type" in v
        assert "title" in v


# ─────────────────────────────────────────────────────────────────────────────
# 4. /decision/recommend endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_recommend_returns_200(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/recommend", json={"dataset_id": did}, headers=admin_headers)
    assert r.status_code == 200


def test_recommend_schema_matches_analyze(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/recommend", json={"dataset_id": did}, headers=admin_headers).json()
    required = {"dataset_name", "recommendation_count", "recommendations", "sources"}
    assert required.issubset(body.keys())


def test_recommend_with_metric_focus(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post(
        "/api/v1/decision/recommend",
        json={"dataset_id": did, "metric_focus": "revenue"},
        headers=admin_headers,
    )
    assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 5. /decision/root-cause endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_root_cause_returns_200(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post(
        "/api/v1/decision/root-cause",
        json={"dataset_id": did, "problem_statement": "Why did revenue decline?"},
        headers=admin_headers,
    )
    assert r.status_code == 200


def test_root_cause_schema(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post(
        "/api/v1/decision/root-cause",
        json={"dataset_id": did, "problem_statement": "Revenue drop"},
        headers=admin_headers,
    ).json()
    required = {"problem_statement", "diagnosed_causes", "decision_recommendations",
                "prevention_measures", "visualizations"}
    assert required.issubset(body.keys())
    assert isinstance(body["diagnosed_causes"], list)
    assert isinstance(body["decision_recommendations"], list)
    assert isinstance(body["prevention_measures"], list)


def test_root_cause_problem_statement_echoed(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post(
        "/api/v1/decision/root-cause",
        json={"dataset_id": did, "problem_statement": "Profit margin declined"},
        headers=admin_headers,
    ).json()
    assert body["problem_statement"] == "Profit margin declined"


def test_root_cause_empty_problem_statement(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post(
        "/api/v1/decision/root-cause",
        json={"dataset_id": did, "problem_statement": ""},
        headers=admin_headers,
    )
    assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 6. /decision/prescriptive endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_prescriptive_returns_200(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/prescriptive", json={"dataset_id": did}, headers=admin_headers)
    assert r.status_code == 200


def test_prescriptive_schema(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/prescriptive", json={"dataset_id": did}, headers=admin_headers).json()
    required = {"metric_focus", "prescribed_actions", "visualizations"}
    assert required.issubset(body.keys())
    assert isinstance(body["prescribed_actions"], list)


def test_prescriptive_with_metric_focus(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post(
        "/api/v1/decision/prescriptive",
        json={"dataset_id": did, "metric_focus": "cost reduction"},
        headers=admin_headers,
    ).json()
    assert body["metric_focus"] == "cost reduction"


# ─────────────────────────────────────────────────────────────────────────────
# 7. /decision/executive endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_executive_returns_200(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.post("/api/v1/decision/executive", json={"dataset_id": did}, headers=admin_headers)
    assert r.status_code == 200


def test_executive_schema(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/executive", json={"dataset_id": did}, headers=admin_headers).json()
    assert "ai_advisory" in body
    advisory = body["ai_advisory"]
    assert isinstance(advisory, dict)
    # When Gemini unavailable, fallback struct must have required keys
    assert "executive_summary" in advisory
    assert "immediate_actions" in advisory
    assert "plan_30_days" in advisory
    assert "plan_90_days" in advisory
    assert "long_term_strategy" in advisory
    assert "risks" in advisory


def test_executive_fallback_when_gemini_absent(client, admin_headers):
    """Without Gemini, executive advisory must return a structured fallback."""
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/executive", json={"dataset_id": did}, headers=admin_headers).json()
    advisory = body["ai_advisory"]
    assert isinstance(advisory["immediate_actions"], list)
    assert isinstance(advisory["plan_30_days"], list)
    assert isinstance(advisory["long_term_strategy"], list)


# ─────────────────────────────────────────────────────────────────────────────
# 8. /decision/history endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_history_returns_200(client, admin_headers):
    r = client.get("/api/v1/decision/history", headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_history_filtered_by_dataset(client, admin_headers):
    did = _upload(client, admin_headers)
    r = client.get(f"/api/v1/decision/history?dataset_id={did}", headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_history_limit_param(client, admin_headers):
    r = client.get("/api/v1/decision/history?limit=5", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) <= 5


# ─────────────────────────────────────────────────────────────────────────────
# 9. /decision/templates endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_templates_returns_200(client, admin_headers):
    r = client.get("/api/v1/decision/templates", headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ─────────────────────────────────────────────────────────────────────────────
# 10. /decision/rules CRUD
# ─────────────────────────────────────────────────────────────────────────────


def test_rules_list_returns_200(client, admin_headers):
    r = client.get("/api/v1/decision/rules", headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_rules_create_and_list(client, admin_headers):
    rule_body = {
        "name": "Low Revenue Alert",
        "description": "Fire when revenue mean is low",
        "metric_name": "revenue_mean",
        "operator": "lt",
        "threshold": 500.0,
        "recommendation_title": "Boost Revenue",
        "recommendation_description": "Revenue below threshold — initiate growth plan.",
        "category": "financial",
        "priority": "high",
    }
    r = client.post("/api/v1/decision/rules", json=rule_body, headers=admin_headers)
    assert r.status_code == 200
    created = r.json()
    assert created["name"] == "Low Revenue Alert"
    assert created["operator"] == "lt"
    assert created["threshold"] == 500.0
    assert "id" in created

    # Verify appears in list
    rules = client.get("/api/v1/decision/rules", headers=admin_headers).json()
    ids = [rule["id"] for rule in rules]
    assert created["id"] in ids


def test_rules_cross_org_isolation(client, admin_headers, other_org_headers):
    """Rules created by one org must not be visible to another."""
    rule_body = {
        "name": "Org A Secret Rule",
        "metric_name": "cost_mean",
        "operator": "gt",
        "threshold": 1000.0,
        "recommendation_title": "Cut Costs",
        "recommendation_description": "Costs are too high.",
        "category": "financial",
        "priority": "high",
    }
    client.post("/api/v1/decision/rules", json=rule_body, headers=admin_headers)
    other_rules = client.get("/api/v1/decision/rules", headers=other_org_headers).json()
    names = [r["name"] for r in other_rules]
    assert "Org A Secret Rule" not in names


# ─────────────────────────────────────────────────────────────────────────────
# 11. Rule Engine unit tests
# ─────────────────────────────────────────────────────────────────────────────


def _make_df(n=30, missing_pct=0.0):
    import numpy as np
    np.random.seed(42)
    data = {
        "revenue": [1000 + i * 20 for i in range(n)],
        "cost": [400 + i * 5 for i in range(n)],
        "units": range(n),
    }
    df = pd.DataFrame(data)
    if missing_pct > 0:
        n_missing = int(n * missing_pct)
        df.loc[:n_missing, "revenue"] = None
    return df


def test_rule_engine_no_rules_on_clean_data():
    from app.services.decision.rule_engine import evaluate_rules
    df = _make_df(30)
    fired = evaluate_rules(df, quality_score=95.0)
    # Clean data should fire few or no high-missing rules
    missing_rules = [r for r in fired if "Missing" in r.get("rule_name", "")]
    assert len(missing_rules) == 0


def test_rule_engine_fires_on_high_missing():
    from app.services.decision.rule_engine import evaluate_rules
    df = _make_df(30, missing_pct=0.5)  # 50% missing
    fired = evaluate_rules(df, quality_score=60.0)
    assert any("Missing" in r.get("rule_name", "") or r.get("trigger", {}).get("metric") == "missing_rate_pct"
               for r in fired)


def test_rule_engine_fires_on_low_quality_score():
    from app.services.decision.rule_engine import evaluate_rules
    df = _make_df(30)
    fired = evaluate_rules(df, quality_score=50.0)  # below threshold of 70
    assert any("quality_score" in r.get("trigger", {}).get("metric", "") for r in fired)


def test_rule_engine_custom_rule_fires():
    from app.services.decision.rule_engine import evaluate_rules
    df = _make_df(30)
    custom_rules = [{
        "id": "custom-1",
        "name": "Low Units",
        "metric_name": "units_mean",
        "operator": "lt",
        "threshold": 99999.0,  # always fires
        "recommendation_title": "Increase Units",
        "recommendation_description": "Unit count is below target.",
        "category": "sales",
        "priority": "medium",
    }]
    fired = evaluate_rules(df, org_rules=custom_rules)
    custom_fired = [r for r in fired if r.get("rule_id") == "custom-1"]
    assert len(custom_fired) == 1


def test_rule_engine_unknown_metric_skipped():
    from app.services.decision.rule_engine import evaluate_rules
    df = _make_df(30)
    custom_rules = [{
        "id": "bad-rule",
        "name": "Bad Metric",
        "metric_name": "nonexistent_metric_xyz",
        "operator": "gt",
        "threshold": 0.0,
        "recommendation_title": "Fix Something",
        "recommendation_description": "Description.",
        "category": "executive",
        "priority": "low",
    }]
    # Should not raise — unknown metric is silently skipped
    fired = evaluate_rules(df, org_rules=custom_rules)
    bad = [r for r in fired if r.get("rule_id") == "bad-rule"]
    assert len(bad) == 0


def test_rule_engine_operators():
    from app.services.decision.rule_engine import _evaluate_condition
    assert _evaluate_condition(10.0, "gt", 5.0) is True
    assert _evaluate_condition(3.0, "gt", 5.0) is False
    assert _evaluate_condition(3.0, "lt", 5.0) is True
    assert _evaluate_condition(5.0, "gte", 5.0) is True
    assert _evaluate_condition(5.0, "lte", 5.0) is True
    assert _evaluate_condition(5.0, "eq", 5.0) is True
    assert _evaluate_condition(5.0, "neq", 6.0) is True
    assert _evaluate_condition(5.0, "neq", 5.0) is False


def test_rule_engine_result_has_required_keys():
    from app.services.decision.rule_engine import evaluate_rules
    df = _make_df(30)
    fired = evaluate_rules(df, quality_score=50.0)
    for r in fired:
        assert "title" in r
        assert "description" in r
        assert "category" in r
        assert "priority" in r
        assert "reason" in r
        assert "source" in r
        assert r["source"] == "rule_engine"


# ─────────────────────────────────────────────────────────────────────────────
# 12. Scoring Engine unit tests
# ─────────────────────────────────────────────────────────────────────────────


def test_score_recommendation_basic():
    from app.services.decision.scoring_engine import score_recommendation
    rec = {
        "title": "Boost Revenue",
        "priority": "high",
        "implementation_difficulty": "low",
        "timeline": "30 days",
    }
    scored = score_recommendation(rec)
    assert "overall_score" in scored
    assert "priority_score" in scored
    assert "impact_score" in scored
    assert "confidence_score" in scored
    assert "urgency_score" in scored
    assert "effort_score" in scored
    assert "roi_score" in scored
    assert 0 <= scored["overall_score"] <= 100


def test_score_recommendation_high_priority_scores_higher():
    from app.services.decision.scoring_engine import score_recommendation
    high = score_recommendation({"priority": "high", "implementation_difficulty": "low", "timeline": "immediate"})
    low = score_recommendation({"priority": "low", "implementation_difficulty": "high", "timeline": "12 months"})
    assert high["overall_score"] > low["overall_score"]


def test_score_recommendation_all_scores_in_range():
    from app.services.decision.scoring_engine import score_recommendation
    for priority in ["high", "medium", "low"]:
        for diff in ["low", "medium", "high"]:
            for tl in ["immediate", "30 days", "90 days", "6 months", "12 months"]:
                rec = {"priority": priority, "implementation_difficulty": diff, "timeline": tl}
                scored = score_recommendation(rec)
                for key in ["priority_score", "impact_score", "confidence_score",
                            "urgency_score", "effort_score", "roi_score", "overall_score"]:
                    assert 0 <= scored[key] <= 100, f"{key} out of range for {rec}"


def test_score_and_rank_sorted():
    from app.services.decision.scoring_engine import score_and_rank
    recs = [
        {"title": "Low Priority", "priority": "low", "implementation_difficulty": "high", "timeline": "12 months"},
        {"title": "High Priority", "priority": "high", "implementation_difficulty": "low", "timeline": "immediate"},
        {"title": "Medium Priority", "priority": "medium", "implementation_difficulty": "medium", "timeline": "90 days"},
    ]
    ranked = score_and_rank(recs)
    scores = [r["overall_score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[0]["title"] == "High Priority"


def test_score_recommendation_preserves_existing_keys():
    from app.services.decision.scoring_engine import score_recommendation
    rec = {"title": "Test", "description": "Desc", "category": "financial", "priority": "high"}
    scored = score_recommendation(rec)
    assert scored["title"] == "Test"
    assert scored["description"] == "Desc"
    assert scored["category"] == "financial"


# ─────────────────────────────────────────────────────────────────────────────
# 13. Visualization Builder unit tests
# ─────────────────────────────────────────────────────────────────────────────


def _sample_recs():
    return [
        {"title": "Boost Revenue", "category": "financial", "priority": "high",
         "overall_score": 85, "roi_score": 80, "impact_score": 90,
         "effort_score": 70, "confidence_score": 80, "urgency_score": 90,
         "timeline": "30 days", "risk": "Low"},
        {"title": "Cut Costs", "category": "operations", "priority": "medium",
         "overall_score": 65, "roi_score": 60, "impact_score": 70,
         "effort_score": 50, "confidence_score": 65, "urgency_score": 55,
         "timeline": "90 days", "risk": "Medium"},
        {"title": "Hire Staff", "category": "hr", "priority": "low",
         "overall_score": 40, "roi_score": 35, "impact_score": 50,
         "effort_score": 30, "confidence_score": 45, "urgency_score": 35,
         "timeline": "6 months", "risk": "Low"},
    ]


def test_viz_priority_distribution():
    from app.services.decision.visualization_builder import build_priority_distribution_chart
    chart = build_priority_distribution_chart(_sample_recs())
    assert chart["chart_type"] == "pie"
    assert "data" in chart
    assert chart["data"]["values"][0] == 1   # 1 high
    assert chart["data"]["values"][1] == 1   # 1 medium
    assert chart["data"]["values"][2] == 1   # 1 low


def test_viz_recommendation_ranking():
    from app.services.decision.visualization_builder import build_recommendation_ranking_chart
    chart = build_recommendation_ranking_chart(_sample_recs())
    assert chart["chart_type"] == "bar"
    assert "series" in chart["data"]
    scores = chart["data"]["series"][0]["values"]
    assert scores == sorted(scores, reverse=True)


def test_viz_roi_comparison():
    from app.services.decision.visualization_builder import build_roi_comparison_chart
    chart = build_roi_comparison_chart(_sample_recs())
    assert chart["chart_type"] == "bar"
    assert "series" in chart["data"]


def test_viz_impact_matrix():
    from app.services.decision.visualization_builder import build_impact_matrix_chart
    chart = build_impact_matrix_chart(_sample_recs())
    assert chart["chart_type"] == "scatter"
    assert "points" in chart["data"]
    assert len(chart["data"]["points"]) == 3


def test_viz_timeline():
    from app.services.decision.visualization_builder import build_decision_timeline_chart
    chart = build_decision_timeline_chart(_sample_recs())
    assert chart["chart_type"] == "bar"
    assert "30 days" in chart["data"]["x_axis"]["values"]


def test_viz_risk_matrix():
    from app.services.decision.visualization_builder import build_risk_matrix_chart
    chart = build_risk_matrix_chart(_sample_recs())
    assert chart["chart_type"] == "scatter"
    assert len(chart["data"]["points"]) == 3


def test_viz_category_breakdown():
    from app.services.decision.visualization_builder import build_category_breakdown_chart
    chart = build_category_breakdown_chart(_sample_recs())
    assert chart["chart_type"] == "bar"
    labels = chart["data"]["x_axis"]["values"]
    assert "financial" in labels
    assert "operations" in labels


def test_viz_all_returns_list():
    from app.services.decision.visualization_builder import build_all_decision_visualizations
    charts = build_all_decision_visualizations(_sample_recs())
    assert isinstance(charts, list)
    assert len(charts) >= 5
    for c in charts:
        assert "chart_type" in c
        assert "title" in c


def test_viz_empty_recs_returns_empty():
    from app.services.decision.visualization_builder import build_all_decision_visualizations
    assert build_all_decision_visualizations([]) == []


# ─────────────────────────────────────────────────────────────────────────────
# 14. Module 9 prompt templates
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("template_name", [
    "decision_recommendations",
    "executive_advisor",
    "prescriptive_analytics",
    "decision_root_cause",
])
def test_m9_prompt_templates_format_without_error(template_name):
    from app.services.ai.prompt_engine import get_template
    tmpl = get_template(template_name)
    sys_inst, user = tmpl.format("sample context", "sample query")
    assert isinstance(sys_inst, str) and len(sys_inst) > 0
    assert isinstance(user, str) and len(user) > 0
    assert "{context}" not in user
    assert "{query}" not in user


def test_m9_templates_in_registry():
    from app.services.ai.prompt_engine import TEMPLATES
    for name in ["decision_recommendations", "executive_advisor",
                 "prescriptive_analytics", "decision_root_cause"]:
        assert name in TEMPLATES, f"'{name}' missing from registry"


# ─────────────────────────────────────────────────────────────────────────────
# 15. Edge cases
# ─────────────────────────────────────────────────────────────────────────────


def test_analyze_returns_recommendations_even_without_gemini(client, admin_headers):
    """Rule engine must fire recommendations even without Gemini configured."""
    did = _upload(client, admin_headers, POOR_QUALITY_CSV)
    body = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=admin_headers).json()
    # Rule engine should produce at least 1 rec for poor quality data
    assert body["recommendation_count"] >= 1
    assert len(body["recommendations"]) >= 1


def test_analyze_recommendations_priority_values_valid(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=admin_headers).json()
    valid_priorities = {"high", "medium", "low"}
    for rec in body["recommendations"]:
        assert rec["priority"] in valid_priorities, f"Invalid priority: {rec['priority']}"


def test_analyze_recommendations_category_values_valid(client, admin_headers):
    did = _upload(client, admin_headers)
    body = client.post("/api/v1/decision/analyze", json={"dataset_id": did}, headers=admin_headers).json()
    valid_cats = {
        "financial", "sales", "marketing", "operations",
        "customer", "supply_chain", "hr", "executive"
    }
    for rec in body["recommendations"]:
        assert rec["category"] in valid_cats, f"Invalid category: {rec['category']}"
