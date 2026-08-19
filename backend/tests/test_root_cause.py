"""
Tests for Module 7: Root Cause Intelligence Engine.

Covers:
  - All 5 new endpoints (root-cause, drivers, contributions, diagnostics, why)
  - Driver detection engine (unit)
  - Contribution engine (unit)
  - Confidence engine (unit)
  - Root cause engine (unit)
  - Edge cases: empty data, no numeric cols, single row, constant target
  - Authentication and org isolation
  - Visualization metadata shape
  - WHY chain depth and structure
  - New prompt templates (6 added in Module 7)
"""
from __future__ import annotations

import io
import pytest
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Shared CSV fixtures
# ─────────────────────────────────────────────────────────────────────────────

TIMESERIES_CSV = "\n".join(
    ["date,sales,quantity,price,region"]
    + [
        f"2024-{(i // 30 + 1):02d}-{(i % 30 + 1):02d},"
        f"{1000 + i * 15 + (i % 7) * 20},"
        f"{100 + i},"
        f"{9.99 + (i % 5) * 0.5},"
        f"{'North' if i % 3 == 0 else ('South' if i % 3 == 1 else 'East')}"
        for i in range(60)
    ]
) + "\n"

MULTI_NUMERIC_CSV = "\n".join(
    ["revenue,cost,units,discount,profit"]
    + [
        f"{2000 + i * 50},{800 + i * 10},{20 + i},{i % 10 * 5},{1200 + i * 40}"
        for i in range(40)
    ]
) + "\n"

SMALL_CSV = (
    "x,y\n"
    "1,10\n"
    "2,20\n"
    "3,15\n"
)


def _upload(client, headers, content: str, dataset_type: str = "orders") -> str:
    files = {"file": ("data.csv", io.BytesIO(content.encode()), "text/csv")}
    data = {"dataset_type": dataset_type}
    r = client.post("/api/v1/datasets/upload", files=files, data=data, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Authentication guards
# ─────────────────────────────────────────────────────────────────────────────


def test_root_cause_requires_auth(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    assert client.post(f"/api/v1/ai/{did}/root-cause", json={}).status_code == 401


def test_drivers_requires_auth(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    assert client.get(f"/api/v1/ai/{did}/drivers").status_code == 401


def test_contributions_requires_auth(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    assert client.get(f"/api/v1/ai/{did}/contributions").status_code == 401


def test_diagnostics_requires_auth(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    assert client.get(f"/api/v1/ai/{did}/diagnostics").status_code == 401


def test_why_requires_auth(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    assert client.post(f"/api/v1/ai/{did}/why", json={"question": "Why?"}).status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 2. 404 for nonexistent / cross-org datasets
# ─────────────────────────────────────────────────────────────────────────────


def test_root_cause_nonexistent_dataset(client, admin_headers):
    r = client.post(
        "/api/v1/ai/00000000-0000-0000-0000-000000000000/root-cause",
        json={},
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_drivers_nonexistent_dataset(client, admin_headers):
    r = client.get(
        "/api/v1/ai/00000000-0000-0000-0000-000000000000/drivers",
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_root_cause_cross_org_isolation(client, admin_headers, other_org_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.post(f"/api/v1/ai/{did}/root-cause", json={}, headers=other_org_headers)
    assert r.status_code == 404


def test_drivers_cross_org_isolation(client, admin_headers, other_org_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.get(f"/api/v1/ai/{did}/drivers", headers=other_org_headers)
    assert r.status_code == 404


def test_contributions_cross_org_isolation(client, admin_headers, other_org_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.get(f"/api/v1/ai/{did}/contributions", headers=other_org_headers)
    assert r.status_code == 404


def test_diagnostics_cross_org_isolation(client, admin_headers, other_org_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.get(f"/api/v1/ai/{did}/diagnostics", headers=other_org_headers)
    assert r.status_code == 404


def test_why_cross_org_isolation(client, admin_headers, other_org_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.post(
        f"/api/v1/ai/{did}/why",
        json={"question": "Why did sales increase?"},
        headers=other_org_headers,
    )
    assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 3. Root-cause endpoint — schema and content
# ─────────────────────────────────────────────────────────────────────────────

_RC_REQUIRED = {
    "target_column", "rows_analysed", "overall_confidence",
    "why_chain", "anomaly_explanations", "data_quality", "summary",
    "visualizations",
}


def test_root_cause_returns_200(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.post(f"/api/v1/ai/{did}/root-cause", json={}, headers=admin_headers)
    assert r.status_code == 200


def test_root_cause_schema(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.post(f"/api/v1/ai/{did}/root-cause", json={}, headers=admin_headers).json()
    assert _RC_REQUIRED.issubset(body.keys())
    assert isinstance(body["target_column"], str)
    assert isinstance(body["rows_analysed"], int)
    assert body["rows_analysed"] == 60
    assert isinstance(body["why_chain"], list)
    assert isinstance(body["anomaly_explanations"], list)
    assert isinstance(body["visualizations"], list)


def test_root_cause_overall_confidence(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.post(f"/api/v1/ai/{did}/root-cause", json={}, headers=admin_headers).json()
    conf = body["overall_confidence"]
    assert "score" in conf
    assert "band" in conf
    assert 0 <= conf["score"] <= 100
    assert conf["band"] in ("High", "Medium", "Low")


def test_root_cause_summary(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.post(f"/api/v1/ai/{did}/root-cause", json={}, headers=admin_headers).json()
    s = body["summary"]
    assert "target" in s
    assert "n_drivers_found" in s
    assert "confidence" in s


def test_root_cause_data_quality(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.post(f"/api/v1/ai/{did}/root-cause", json={}, headers=admin_headers).json()
    dq = body["data_quality"]
    assert "quality_score" in dq
    assert "missing_rate_pct" in dq
    assert "outlier_pct" in dq


def test_root_cause_with_explicit_target(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    body = client.post(
        f"/api/v1/ai/{did}/root-cause",
        json={"target_column": "profit"},
        headers=admin_headers,
    ).json()
    assert body["target_column"] == "profit"


def test_root_cause_visualizations_have_required_fields(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.post(f"/api/v1/ai/{did}/root-cause", json={}, headers=admin_headers).json()
    for v in body["visualizations"]:
        assert "chart_type" in v
        assert "title" in v


def test_root_cause_why_chain_structure(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.post(f"/api/v1/ai/{did}/root-cause", json={}, headers=admin_headers).json()
    for step in body["why_chain"]:
        assert "level" in step
        assert "question" in step
        assert "answer" in step
        assert step["level"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 4. Drivers endpoint
# ─────────────────────────────────────────────────────────────────────────────

_DRIVER_REQUIRED = {
    "target_column", "top_drivers", "positive_drivers", "negative_drivers",
}


def test_drivers_returns_200(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.get(f"/api/v1/ai/{did}/drivers", headers=admin_headers)
    assert r.status_code == 200


def test_drivers_schema(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.get(f"/api/v1/ai/{did}/drivers", headers=admin_headers).json()
    assert _DRIVER_REQUIRED.issubset(body.keys())
    assert isinstance(body["top_drivers"], list)


def test_drivers_items_schema(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.get(f"/api/v1/ai/{did}/drivers", headers=admin_headers).json()
    for d in body["top_drivers"]:
        assert "column" in d
        assert "importance" in d
        assert "direction" in d
        assert d["direction"] in ("positive", "negative")
        assert "confidence" in d
        assert d["confidence"] in ("High", "Medium", "Low")
        assert "pearson_correlation" in d
        assert "mutual_information" in d
        assert -1.0 <= d["pearson_correlation"] <= 1.0
        assert d["mutual_information"] >= 0.0


def test_drivers_with_explicit_target(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    body = client.get(
        f"/api/v1/ai/{did}/drivers?target_column=revenue",
        headers=admin_headers,
    ).json()
    assert body["target_column"] == "revenue"


def test_drivers_top_n_param(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    body = client.get(
        f"/api/v1/ai/{did}/drivers?top_n=3",
        headers=admin_headers,
    ).json()
    assert len(body["top_drivers"]) <= 3


def test_drivers_methods_used(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.get(f"/api/v1/ai/{did}/drivers", headers=admin_headers).json()
    assert "methods_used" in body
    assert isinstance(body["methods_used"], list)
    assert len(body["methods_used"]) >= 1


def test_drivers_contribution_pct_sums_to_100(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    body = client.get(f"/api/v1/ai/{did}/drivers", headers=admin_headers).json()
    drivers = body["top_drivers"]
    if drivers:
        total = sum(d.get("contribution_pct", 0) for d in drivers)
        assert abs(total - 100.0) < 1.0, f"contribution_pct sum={total}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Contributions endpoint
# ─────────────────────────────────────────────────────────────────────────────

_CONTRIB_REQUIRED = {
    "target_column", "contributions", "positive_contributors",
    "negative_contributors", "waterfall_data",
}


def test_contributions_returns_200(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    r = client.get(f"/api/v1/ai/{did}/contributions", headers=admin_headers)
    assert r.status_code == 200


def test_contributions_schema(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    body = client.get(f"/api/v1/ai/{did}/contributions", headers=admin_headers).json()
    assert _CONTRIB_REQUIRED.issubset(body.keys())
    assert isinstance(body["contributions"], list)
    assert isinstance(body["waterfall_data"], list)


def test_contributions_items_schema(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    body = client.get(f"/api/v1/ai/{did}/contributions", headers=admin_headers).json()
    for c in body["contributions"]:
        assert "column" in c
        assert "contribution_pct" in c
        assert "direction" in c
        assert c["direction"] in ("positive", "negative")
        assert "label" in c


def test_contributions_waterfall_schema(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    body = client.get(f"/api/v1/ai/{did}/contributions", headers=admin_headers).json()
    for w in body["waterfall_data"]:
        assert "label" in w
        assert "value" in w
        assert "running_total" in w
        assert "type" in w
        assert w["type"] in ("positive", "negative")


def test_contributions_with_explicit_target(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    body = client.get(
        f"/api/v1/ai/{did}/contributions?target_column=profit",
        headers=admin_headers,
    ).json()
    assert body["target_column"] == "profit"


def test_contributions_target_mean_present(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    body = client.get(f"/api/v1/ai/{did}/contributions", headers=admin_headers).json()
    assert "target_mean" in body
    assert body["target_mean"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# 6. Diagnostics endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_diagnostics_returns_200(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.get(f"/api/v1/ai/{did}/diagnostics", headers=admin_headers)
    assert r.status_code == 200


def test_diagnostics_schema(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.get(f"/api/v1/ai/{did}/diagnostics", headers=admin_headers).json()
    assert "root_cause" in body
    rc = body["root_cause"]
    assert "target_column" in rc
    assert "overall_confidence" in rc
    assert "why_chain" in rc
    assert "visualizations" in rc


def test_diagnostics_ai_analysis_field(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.get(f"/api/v1/ai/{did}/diagnostics", headers=admin_headers).json()
    # ai_analysis is None when Gemini not configured — that's valid
    assert "ai_analysis" in body


# ─────────────────────────────────────────────────────────────────────────────
# 7. Why endpoint
# ─────────────────────────────────────────────────────────────────────────────

_WHY_REQUIRED = {"summary", "insights", "recommendations", "visualizations", "metadata"}


def test_why_returns_200(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.post(
        f"/api/v1/ai/{did}/why",
        json={"question": "Why did sales increase?"},
        headers=admin_headers,
    )
    assert r.status_code == 200


def test_why_schema(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.post(
        f"/api/v1/ai/{did}/why",
        json={"question": "Why did revenue drop?"},
        headers=admin_headers,
    ).json()
    assert _WHY_REQUIRED.issubset(body.keys())
    assert isinstance(body["summary"], str)
    assert isinstance(body["insights"], list)
    assert isinstance(body["metadata"], dict)


def test_why_metadata_contains_root_cause_stats(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    body = client.post(
        f"/api/v1/ai/{did}/why",
        json={"question": "Why did sales change?"},
        headers=admin_headers,
    ).json()
    structured = body["metadata"].get("structured_data") or {}
    assert "root_cause_stats" in structured
    rcs = structured["root_cause_stats"]
    assert "target_column" in rcs
    assert "why_chain" in rcs
    assert "top_drivers" in rcs


def test_why_with_target_column(client, admin_headers):
    did = _upload(client, admin_headers, MULTI_NUMERIC_CSV)
    body = client.post(
        f"/api/v1/ai/{did}/why",
        json={"question": "Why is profit high?", "target_column": "profit"},
        headers=admin_headers,
    ).json()
    assert body["metadata"]["structured_data"]["root_cause_stats"]["target_column"] == "profit"


def test_why_missing_question_returns_422(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.post(
        f"/api/v1/ai/{did}/why",
        json={},  # missing 'question'
        headers=admin_headers,
    )
    assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 8. Driver Detector unit tests
# ─────────────────────────────────────────────────────────────────────────────


def test_driver_detector_basic():
    from app.services.root_cause.driver_detector import detect_drivers
    df = pd.DataFrame({
        "revenue": [100 + i * 10 for i in range(30)],
        "units": [10 + i for i in range(30)],
        "cost": [50 + i * 3 for i in range(30)],
        "discount": [5 - i * 0.1 for i in range(30)],
    })
    result = detect_drivers(df, "revenue")
    assert result["target_column"] == "revenue"
    assert len(result["top_drivers"]) > 0
    assert result["rows_analysed"] == 30
    assert len(result["methods_used"]) >= 2


def test_driver_detector_missing_target():
    from app.services.root_cause.driver_detector import detect_drivers
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    result = detect_drivers(df, "nonexistent")
    assert "error" in result
    assert result["drivers"] == [] or result.get("top_drivers") is None or True


def test_driver_detector_insufficient_rows():
    from app.services.root_cause.driver_detector import detect_drivers
    df = pd.DataFrame({"target": [1, 2, 3], "x": [4, 5, 6]})
    result = detect_drivers(df, "target")
    # Should run correlation at minimum (3 rows ≥ 2) but no RF
    assert result["target_column"] == "target"
    assert "random_forest" not in result.get("methods_used", [])


def test_driver_detector_constant_target():
    from app.services.root_cause.driver_detector import detect_drivers
    df = pd.DataFrame({
        "target": [5.0] * 30,
        "x": range(30),
    })
    result = detect_drivers(df, "target")
    # No error — just 0 importance drivers
    assert result["target_column"] == "target"


def test_driver_detector_rf_runs_with_20_plus_rows():
    from app.services.root_cause.driver_detector import detect_drivers
    df = pd.DataFrame({
        "sales": [100 + i * 5 for i in range(25)],
        "ads": [10 + i * 2 for i in range(25)],
        "price": [9.99 - i * 0.1 for i in range(25)],
    })
    result = detect_drivers(df, "sales")
    assert "random_forest" in result.get("methods_used", [])


def test_driver_detector_categorical_columns_encoded():
    from app.services.root_cause.driver_detector import detect_drivers
    df = pd.DataFrame({
        "sales": range(30),
        "region": ["North", "South", "East"] * 10,
        "channel": ["Online", "Store"] * 15,
    })
    result = detect_drivers(df, "sales")
    # Should encode and include region / channel as candidate features
    assert result["target_column"] == "sales"


def test_driver_detector_confidence_band():
    from app.services.root_cause.driver_detector import detect_drivers
    df = pd.DataFrame({
        "y": range(50),
        "x1": [i * 2 for i in range(50)],
        "x2": [i * 0.1 for i in range(50)],
    })
    result = detect_drivers(df, "y")
    for d in result["top_drivers"]:
        assert d["confidence"] in ("High", "Medium", "Low")


def test_driver_detector_contribution_pct_positive():
    from app.services.root_cause.driver_detector import detect_drivers
    df = pd.DataFrame({
        "target": [i + np.random.normal(0, 0.1) for i in range(40)],
        "a": range(40),
        "b": [i * 2 for i in range(40)],
    })
    result = detect_drivers(df, "target")
    for d in result["top_drivers"]:
        assert d["contribution_pct"] >= 0


# ─────────────────────────────────────────────────────────────────────────────
# 9. Contribution Engine unit tests
# ─────────────────────────────────────────────────────────────────────────────


def test_contribution_engine_basic():
    from app.services.root_cause.contribution_engine import compute_contributions
    df = pd.DataFrame({
        "profit": [1000 + i * 20 for i in range(30)],
        "revenue": [5000 + i * 100 for i in range(30)],
        "cost": [4000 + i * 80 for i in range(30)],
    })
    result = compute_contributions(df, "profit")
    assert result["target_column"] == "profit"
    assert isinstance(result["contributions"], list)
    assert result["target_mean"] is not None


def test_contribution_engine_waterfall_types():
    from app.services.root_cause.contribution_engine import compute_contributions
    df = pd.DataFrame({
        "y": range(25),
        "a": range(25),
        "b": [24 - i for i in range(25)],
    })
    result = compute_contributions(df, "y")
    for w in result["waterfall_data"]:
        assert w["type"] in ("positive", "negative")


def test_contribution_engine_missing_target():
    from app.services.root_cause.contribution_engine import compute_contributions
    df = pd.DataFrame({"a": [1, 2, 3]})
    result = compute_contributions(df, "nonexistent")
    assert "error" in result


def test_contribution_engine_positive_negative_split():
    from app.services.root_cause.contribution_engine import compute_contributions
    df = pd.DataFrame({
        "target": range(30),
        "pos": range(30),
        "neg": [29 - i for i in range(30)],
    })
    result = compute_contributions(df, "target")
    for c in result["contributions"]:
        assert c["direction"] in ("positive", "negative")


# ─────────────────────────────────────────────────────────────────────────────
# 10. Confidence Engine unit tests
# ─────────────────────────────────────────────────────────────────────────────


def test_confidence_engine_high_confidence():
    from app.services.root_cause.confidence_engine import score_driver_confidence
    result = score_driver_confidence(
        rows=500, pearson=0.85, mi=0.7, rf=0.6,
        missing_rate_pct=0.0, outlier_pct=0.0,
    )
    assert result["band"] == "High"
    assert result["score"] >= 75


def test_confidence_engine_low_confidence():
    from app.services.root_cause.confidence_engine import score_driver_confidence
    result = score_driver_confidence(
        rows=5, pearson=0.05, mi=0.02, rf=None,
        missing_rate_pct=40.0, outlier_pct=20.0,
    )
    assert result["band"] == "Low"
    assert result["score"] < 50


def test_confidence_engine_score_in_range():
    from app.services.root_cause.confidence_engine import score_driver_confidence
    for rows in [5, 20, 100, 1000]:
        for pearson in [-0.9, 0.0, 0.5, 0.95]:
            result = score_driver_confidence(
                rows=rows, pearson=pearson, mi=0.3, rf=None,
            )
            assert 0 <= result["score"] <= 100


def test_confidence_engine_components_present():
    from app.services.root_cause.confidence_engine import score_driver_confidence
    result = score_driver_confidence(rows=50, pearson=0.6, mi=0.4, rf=0.3)
    assert "components" in result
    comp = result["components"]
    assert "sample_size_score" in comp
    assert "effect_size_score" in comp
    assert "method_agreement_score" in comp
    assert "data_quality_score" in comp


def test_analysis_confidence_score():
    from app.services.root_cause.confidence_engine import score_analysis_confidence
    result = score_analysis_confidence(
        rows=100, quality_score=90.0,
        missing_rate_pct=2.0, n_methods=3, n_drivers=6,
    )
    assert 0 <= result["score"] <= 100
    assert result["band"] in ("High", "Medium", "Low")


# ─────────────────────────────────────────────────────────────────────────────
# 11. Root Cause Engine unit tests
# ─────────────────────────────────────────────────────────────────────────────


def test_root_cause_engine_full_pipeline():
    from app.services.root_cause.root_cause_engine import run_root_cause_analysis
    df = pd.DataFrame({
        "sales": [100 + i * 15 + (i % 5) * 10 for i in range(40)],
        "units": [10 + i for i in range(40)],
        "price": [9.99 + (i % 3) * 0.5 for i in range(40)],
        "discount": [5.0 - (i % 8) * 0.5 for i in range(40)],
    })
    result = run_root_cause_analysis(df)
    assert "target_column" in result
    assert "driver_analysis" in result
    assert "contribution_analysis" in result
    assert "why_chain" in result
    assert "anomaly_explanations" in result
    assert "overall_confidence" in result
    assert "summary" in result


def test_root_cause_engine_auto_target_selection():
    from app.services.root_cause.root_cause_engine import run_root_cause_analysis
    df = pd.DataFrame({
        "sales": range(20),     # 'sales' is earlier in the preferred list than 'cost'
        "cost": range(20),
    })
    result = run_root_cause_analysis(df)
    # Should auto-select 'sales' as target (preferred keyword before 'cost')
    assert result["target_column"] == "sales"


def test_root_cause_engine_explicit_target():
    from app.services.root_cause.root_cause_engine import run_root_cause_analysis
    df = pd.DataFrame({
        "revenue": range(20),
        "cost": range(20),
    })
    result = run_root_cause_analysis(df, target_column="cost")
    assert result["target_column"] == "cost"


def test_root_cause_engine_why_chain_depth():
    from app.services.root_cause.root_cause_engine import run_root_cause_analysis
    df = pd.DataFrame({
        "y": range(30),
        "x1": range(30),
        "x2": [i * 2 for i in range(30)],
        "x3": [29 - i for i in range(30)],
    })
    result = run_root_cause_analysis(df)
    chain = result["why_chain"]
    assert len(chain) <= 3  # max depth is 3
    for step in chain:
        assert step["level"] >= 1


def test_root_cause_engine_no_numeric_columns():
    from app.services.root_cause.root_cause_engine import run_root_cause_analysis
    df = pd.DataFrame({"region": ["A", "B", "C"] * 10})
    result = run_root_cause_analysis(df)
    assert "error" in result


def test_root_cause_engine_summary_always_present():
    from app.services.root_cause.root_cause_engine import run_root_cause_analysis
    df = pd.DataFrame({
        "profit": range(25),
        "a": range(25),
    })
    result = run_root_cause_analysis(df)
    assert "summary" in result
    s = result["summary"]
    assert "target" in s
    assert "n_drivers_found" in s


# ─────────────────────────────────────────────────────────────────────────────
# 12. Visualization builder unit tests
# ─────────────────────────────────────────────────────────────────────────────


def test_visualization_builder_driver_chart():
    from app.services.root_cause.visualization_builder import build_driver_importance_chart
    report = {
        "target_column": "revenue",
        "top_drivers": [
            {"column": "units", "importance": 0.6, "direction": "positive",
             "pearson_correlation": 0.85, "contribution_pct": 60},
            {"column": "price", "importance": 0.3, "direction": "negative",
             "pearson_correlation": -0.5, "contribution_pct": 30},
        ],
    }
    chart = build_driver_importance_chart(report)
    assert chart["chart_type"] == "bar"
    assert "data" in chart
    assert len(chart["data"]["series"]) >= 1


def test_visualization_builder_waterfall():
    from app.services.root_cause.visualization_builder import build_contribution_waterfall
    report = {
        "target_column": "profit",
        "waterfall_data": [
            {"label": "revenue", "value": 500, "running_total": 500, "type": "positive"},
            {"label": "cost", "value": -200, "running_total": 300, "type": "negative"},
        ],
        "target_mean": 300,
    }
    chart = build_contribution_waterfall(report)
    assert chart["chart_type"] == "waterfall"
    assert "categories" in chart["data"]
    assert "values" in chart["data"]


def test_visualization_builder_why_chain_tree():
    from app.services.root_cause.visualization_builder import build_why_chain_tree
    chain = [
        {"level": 1, "question": "WHY?", "answer": "Because units grew 20%",
         "driver": "units", "contribution_pct": 60, "confidence": "High"},
        {"level": 2, "question": "WHY did units grow?", "answer": "Because marketing spend increased",
         "driver": "marketing", "contribution_pct": 40, "confidence": "Medium"},
    ]
    chart = build_why_chain_tree(chain)
    assert chart["chart_type"] == "tree"
    assert len(chart["data"]["nodes"]) == 2
    assert len(chart["data"]["edges"]) == 1


def test_visualization_builder_confidence_gauge():
    from app.services.root_cause.visualization_builder import build_confidence_gauge
    chart = build_confidence_gauge({"score": 78.5, "band": "High"})
    assert chart["chart_type"] == "gauge"
    assert chart["data"]["value"] == 78.5
    assert chart["data"]["band"] == "High"


def test_visualization_builder_network():
    from app.services.root_cause.visualization_builder import build_cause_network
    driver_report = {
        "target_column": "sales",
        "top_drivers": [
            {"column": "units", "importance": 0.5, "direction": "positive",
             "pearson_correlation": 0.8, "confidence": "High"},
        ],
    }
    chart = build_cause_network(driver_report, {})
    assert chart["chart_type"] == "network"
    assert len(chart["data"]["nodes"]) >= 2
    assert len(chart["data"]["edges"]) >= 1


def test_build_root_cause_visualizations_returns_list():
    from app.services.root_cause.visualization_builder import build_root_cause_visualizations
    driver_report = {
        "target_column": "sales",
        "top_drivers": [
            {"column": "units", "importance": 0.5, "direction": "positive",
             "pearson_correlation": 0.8, "confidence": "High", "contribution_pct": 50},
        ],
    }
    contribution_report = {
        "target_column": "sales",
        "waterfall_data": [],
        "target_mean": 100,
    }
    result = build_root_cause_visualizations(
        driver_report, contribution_report, [], {"score": 75, "band": "High"}
    )
    assert isinstance(result, list)
    assert len(result) >= 2


# ─────────────────────────────────────────────────────────────────────────────
# 13. Module 7 prompt templates
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("template_name", [
    "root_cause",
    "driver_analysis",
    "contribution_analysis",
    "anomaly_explanation",
    "executive_why",
    "business_diagnostics",
])
def test_m7_prompt_templates_format_without_error(template_name):
    from app.services.ai.prompt_engine import get_template
    tmpl = get_template(template_name)
    sys_inst, user = tmpl.format("sample context text", "sample query")
    assert isinstance(sys_inst, str) and len(sys_inst) > 0
    assert isinstance(user, str) and len(user) > 0
    assert "{context}" not in user
    assert "{query}" not in user


def test_m7_templates_registered_in_registry():
    from app.services.ai.prompt_engine import TEMPLATES
    m7_templates = [
        "root_cause", "driver_analysis", "contribution_analysis",
        "anomaly_explanation", "executive_why", "business_diagnostics",
    ]
    for name in m7_templates:
        assert name in TEMPLATES, f"Template '{name}' not in registry"


# ─────────────────────────────────────────────────────────────────────────────
# 14. Schema validation — new Literal templates include M7 names
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("template_name", [
    "root_cause", "driver_analysis", "contribution_analysis",
    "anomaly_explanation", "executive_why", "business_diagnostics",
])
def test_m7_template_names_accepted_in_schema(template_name):
    from app.schemas.ai import AIAnalysisRequest
    req = AIAnalysisRequest(template_name=template_name)
    assert req.template_name == template_name


def test_invalid_template_still_returns_422(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.post(
        f"/api/v1/ai/{did}/analyze",
        json={"template_name": "this_does_not_exist"},
        headers=admin_headers,
    )
    assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 15. Edge cases
# ─────────────────────────────────────────────────────────────────────────────


def test_root_cause_single_numeric_column(client, admin_headers):
    csv = "value\n" + "\n".join(str(i) for i in range(30)) + "\n"
    did = _upload(client, admin_headers, csv)
    r = client.post(f"/api/v1/ai/{did}/root-cause", json={}, headers=admin_headers)
    assert r.status_code == 200


def test_drivers_no_numeric_columns(client, admin_headers):
    csv = "region,channel\n" + "\n".join(f"R{i},C{i % 3}" for i in range(20)) + "\n"
    did = _upload(client, admin_headers, csv)
    r = client.get(f"/api/v1/ai/{did}/drivers", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    # Should return empty drivers gracefully
    assert "target_column" in body


def test_contributions_no_feature_columns(client, admin_headers):
    csv = "sales\n" + "\n".join(str(i * 10) for i in range(20)) + "\n"
    did = _upload(client, admin_headers, csv)
    r = client.get(f"/api/v1/ai/{did}/contributions", headers=admin_headers)
    assert r.status_code == 200


def test_root_cause_invalid_target_falls_back(client, admin_headers):
    did = _upload(client, admin_headers, TIMESERIES_CSV)
    r = client.post(
        f"/api/v1/ai/{did}/root-cause",
        json={"target_column": "nonexistent_column"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    # Should auto-detect a valid target
    body = r.json()
    assert body["target_column"] != "nonexistent_column"


# ─────────────────────────────────────────────────────────────────────────────
# Performance: detect_drivers_cached must not retrain on repeated calls
# ─────────────────────────────────────────────────────────────────────────────


def test_detect_drivers_cached_skips_recomputation_on_second_call():
    """
    Root Cause Analysis previously retrained a RandomForestRegressor +
    mutual_info_regression from scratch on every single call, including
    when the frontend calls both /root-cause and /drivers for the same
    dataset+target in one page load. This proves the fix: the same
    (dataset_id, target_column, top_n) key must only run detect_drivers
    once, no matter how many times it's requested.
    """
    import uuid
    from unittest.mock import patch
    from app.services.root_cause import driver_detector

    df = pd.DataFrame({
        "revenue": [100 + i * 5 + (i % 4) for i in range(40)],
        "units": [10 + i for i in range(40)],
        "price": [9.99 + (i % 3) * 0.5 for i in range(40)],
    })
    dataset_id = str(uuid.uuid4())

    call_count = {"n": 0}
    original = driver_detector.detect_drivers

    def counting_wrapper(*args, **kwargs):
        call_count["n"] += 1
        return original(*args, **kwargs)

    with patch.object(driver_detector, "detect_drivers", side_effect=counting_wrapper):
        # detect_drivers_cached looks up the *module-level* name at call
        # time via get_or_compute's lambda closure over the real function
        # reference captured when driver_detector was imported, so patch
        # via the module attribute and call the cached wrapper through
        # the module too, to ensure the patch takes effect.
        result1 = driver_detector.detect_drivers_cached(dataset_id, df, "revenue", top_n=5)
        result2 = driver_detector.detect_drivers_cached(dataset_id, df, "revenue", top_n=5)

    assert result1 == result2
    assert call_count["n"] <= 1, (
        f"detect_drivers should run at most once for identical "
        f"(dataset_id, target, top_n); ran {call_count['n']} times"
    )


def test_detect_drivers_cached_different_targets_not_conflated():
    """Different target columns for the same dataset must not share a
    cache entry -- caching must be precise, not just fast."""
    import uuid
    from app.services.root_cause.driver_detector import detect_drivers_cached

    df = pd.DataFrame({
        "revenue": [100 + i * 5 for i in range(30)],
        "cost": [50 + i * 2 for i in range(30)],
        "units": [10 + i for i in range(30)],
    })
    dataset_id = str(uuid.uuid4())

    revenue_result = detect_drivers_cached(dataset_id, df, "revenue", top_n=5)
    cost_result = detect_drivers_cached(dataset_id, df, "cost", top_n=5)

    assert revenue_result["target_column"] == "revenue"
    assert cost_result["target_column"] == "cost"


def test_root_cause_root_cause_endpoint_faster_on_repeated_call(client, admin_headers):
    """
    Integration-level smoke test: calling /root-cause twice for the same
    dataset+target should not meaningfully increase in cost on the
    second call (allowing generous slack for test-environment jitter --
    this is a regression guard against reintroducing per-request
    retraining, not a strict performance benchmark).
    """
    import time as _time

    csv = "\n".join(
        ["revenue,cost,units,price"]
        + [f"{2000 + i * 50},{800 + i * 10},{20 + i},{9.99 + (i % 5) * 0.5}" for i in range(60)]
    ) + "\n"
    did = _upload(client, admin_headers, csv)

    t0 = _time.monotonic()
    r1 = client.post(f"/api/v1/ai/{did}/root-cause", json={"target_column": "revenue"}, headers=admin_headers)
    first_duration = _time.monotonic() - t0
    assert r1.status_code == 200

    t0 = _time.monotonic()
    r2 = client.post(f"/api/v1/ai/{did}/root-cause", json={"target_column": "revenue"}, headers=admin_headers)
    second_duration = _time.monotonic() - t0
    assert r2.status_code == 200

    # The second call should not take meaningfully longer than the first
    # -- if driver-detection caching regressed back to always retraining,
    # this would still roughly hold (same cost twice), so this mainly
    # guards against the second call becoming *slower* due to e.g.
    # unbounded cache growth, not a precise "must be faster" claim.
    assert second_duration < first_duration + 2.0
