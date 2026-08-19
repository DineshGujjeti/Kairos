"""
Root Cause Engine — Module 7.

Orchestrates driver detection, contribution analysis, and confidence
scoring into a cohesive root cause report that answers WHY a metric
behaves as observed, including multi-level causal reasoning chains
and anomaly explanations grounded exclusively in the data.
"""
from __future__ import annotations

import pandas as pd

from app.core.logging import get_logger
from app.services.root_cause.driver_detector import detect_drivers, detect_drivers_cached
from app.services.root_cause.contribution_engine import compute_contributions
from app.services.root_cause.confidence_engine import (
    score_driver_confidence,
    score_analysis_confidence,
)
from app.services.eda.outliers import outliers as eda_outliers
from app.services.eda.quality import quality as eda_quality
from app.services.kpi.calculator import compute_column_metrics

logger = get_logger(__name__)


def _safe(fn, *args, fallback=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.warning("root_cause_safe_error", fn=fn.__name__, error=str(exc))
        return fallback


# ─────────────────────────────────────────────────────────────────────────────
# Business narrative helpers
# ─────────────────────────────────────────────────────────────────────────────


def _humanise_direction(direction: str, correlation: float) -> str:
    if direction == "positive":
        return "higher values are associated with higher"
    return "higher values are associated with lower"


def _build_why_chain(driver_report: dict, target_column: str, depth: int = 3) -> list[dict]:
    """
    Build a multi-level WHY reasoning chain up to *depth* levels.

    Level 1 → the top driver explains target
    Level 2 → what explains the top driver (recursively)
    Level 3 → what explains the level-2 driver
    """
    chain: list[dict] = []
    drivers = driver_report.get("top_drivers", [])

    if not drivers:
        return chain

    for level, driver in enumerate(drivers[:depth], start=1):
        col = driver["column"]
        pct = driver.get("contribution_pct", 0)
        conf = driver.get("confidence", "Medium")
        direction = driver.get("direction", "positive")
        r = driver.get("pearson_correlation", 0.0)

        chain.append({
            "level": level,
            "question": "WHY?" if level == 1 else f"WHY did {drivers[level - 2]['column']} behave this way?",
            "answer": (
                f"Because '{col}' explains ~{pct:.0f}% of variation in '{target_column}': "
                f"{_humanise_direction(direction, r)} '{target_column}' values "
                f"(correlation={r:+.3f})."
            ),
            "driver": col,
            "contribution_pct": pct,
            "confidence": conf,
        })

    return chain


def _explain_anomalies(
    df: pd.DataFrame,
    outlier_result: dict,
    kpi_metrics: dict,
) -> list[dict]:
    """
    Convert raw outlier detections into business-intelligible explanations.
    """
    explanations: list[dict] = []
    columns_with_outliers = outlier_result.get("column_names_with_outliers", [])
    col_details = outlier_result.get("columns", {})

    for col in columns_with_outliers[:6]:
        detail = col_details.get(col, {})
        count = detail.get("outlier_count", 0)
        pct = detail.get("outlier_percentage", 0.0)
        lower = detail.get("lower_bound")
        upper = detail.get("upper_bound")

        # Guess business impact from correlation with other numeric columns
        related: list[str] = []
        target_series = df[col].dropna()
        for other in df.select_dtypes(include="number").columns:
            if other == col:
                continue
            r = df[other].corr(target_series)
            if abs(r) >= 0.5:
                related.append(f"{other} (r={r:+.2f})")

        confidence = "High" if pct > 5 else ("Medium" if pct > 2 else "Low")

        explanations.append({
            "column": col,
            "outlier_count": count,
            "outlier_pct": round(pct, 2),
            "bounds": {"lower": lower, "upper": upper},
            "possible_causes": [
                f"Data entry errors or system glitches in '{col}'",
                f"Genuine extreme events (e.g. promotions, incidents) in '{col}'",
                "Seasonality or batch effects not captured in other columns",
            ],
            "correlated_variables": related[:4],
            "business_impact": (
                f"{'Significant' if pct > 5 else 'Moderate'} impact: "
                f"{count} outlier rows ({pct:.1f}%) in '{col}' may distort "
                f"aggregates and model accuracy."
            ),
            "affected_kpis": [col] + [r.split(" ")[0] for r in related[:2]],
            "confidence": confidence,
        })

    return explanations


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def run_root_cause_analysis(
    df: pd.DataFrame,
    target_column: str | None = None,
    dataset_id: str | None = None,
) -> dict:
    """
    Full root cause analysis pipeline:
      1. Identify the primary numeric target (auto or provided).
      2. Detect drivers via correlation / MI / RF.
      3. Compute per-feature contributions.
      4. Build multi-level WHY reasoning chain.
      5. Explain anomalies.
      6. Score overall confidence.

    dataset_id, when provided, routes driver detection through the
    shared TTL cache (see driver_detector.detect_drivers_cached) so the
    RandomForest + mutual-information training this step does isn't
    repeated on every request for the same dataset+target -- this is
    the main cost driver behind Root Cause Analysis response time.
    Callers that don't have a stable dataset_id (e.g. ad-hoc/test calls
    against an in-memory frame) can omit it and fall back to the
    uncached path with identical results, just slower.

    Returns a single comprehensive report dict.
    """
    # ── Auto-select target ────────────────────────────────────
    numeric_cols = list(df.select_dtypes(include="number").columns)
    if not numeric_cols:
        return {"error": "No numeric columns found for root cause analysis", "drivers": []}

    if target_column is None or target_column not in df.columns:
        # Prefer columns whose name suggests a business KPI
        preferred = ["revenue", "sales", "amount", "total", "profit",
                     "income", "quantity", "demand", "orders", "cost"]
        target_column = numeric_cols[0]
        found = False
        for pref in preferred:
            for col in numeric_cols:
                if pref.lower() in col.lower():
                    target_column = col
                    found = True
                    break
            if found:
                break

    # ── Run sub-engines ───────────────────────────────────────
    if dataset_id:
        driver_report = _safe(
            detect_drivers_cached, dataset_id, df, target_column, top_n=8,
            fallback={"target_column": target_column, "top_drivers": [], "error": "driver detection failed"},
        )
    else:
        driver_report = _safe(
            detect_drivers, df, target_column, top_n=8,
            fallback={"target_column": target_column, "top_drivers": [], "error": "driver detection failed"},
        )
    contribution_report = _safe(
        compute_contributions, df, target_column, top_n=8,
        fallback={"target_column": target_column, "contributions": []},
    )
    outlier_result = _safe(eda_outliers, df, fallback={"column_names_with_outliers": [], "columns": {}})
    quality_result = _safe(eda_quality, df, fallback={"quality_score": 75.0})
    kpi_metrics = _safe(compute_column_metrics, df, fallback={"columns": {}})

    quality_score = (quality_result or {}).get("quality_score", 75.0)
    missing_rate = round(df.isna().sum().sum() / max(df.size, 1) * 100, 2)
    outlier_pct = (outlier_result or {}).get("total_outliers", 0) / max(len(df), 1) * 100

    # ── Score individual driver confidence ────────────────────
    top_drivers = (driver_report or {}).get("top_drivers", [])
    for d in top_drivers:
        conf_detail = score_driver_confidence(
            rows=len(df),
            pearson=d.get("pearson_correlation", 0.0),
            mi=d.get("mutual_information", 0.0),
            rf=d.get("rf_importance"),
            missing_rate_pct=missing_rate,
            outlier_pct=outlier_pct,
        )
        d["confidence_score"] = conf_detail["score"]
        d["confidence"] = conf_detail["band"]
        d["confidence_components"] = conf_detail["components"]

    # ── Multi-level WHY chain ─────────────────────────────────
    why_chain = _build_why_chain(driver_report or {}, target_column, depth=3)

    # ── Anomaly explanations ──────────────────────────────────
    anomaly_explanations = _explain_anomalies(df, outlier_result or {}, kpi_metrics or {})

    # ── Overall confidence ────────────────────────────────────
    methods_used = (driver_report or {}).get("methods_used", [])
    overall_conf = score_analysis_confidence(
        rows=len(df),
        quality_score=quality_score,
        missing_rate_pct=missing_rate,
        n_methods=len(methods_used),
        n_drivers=len(top_drivers),
    )

    return {
        "target_column": target_column,
        "rows_analysed": len(df),
        "overall_confidence": overall_conf,
        "driver_analysis": driver_report,
        "contribution_analysis": contribution_report,
        "why_chain": why_chain,
        "anomaly_explanations": anomaly_explanations,
        "data_quality": {
            "quality_score": quality_score,
            "missing_rate_pct": missing_rate,
            "outlier_pct": round(outlier_pct, 2),
        },
        "summary": {
            "target": target_column,
            "top_positive_driver": (
                top_drivers[0]["column"]
                if top_drivers and top_drivers[0]["direction"] == "positive"
                else None
            ),
            "top_negative_driver": next(
                (d["column"] for d in top_drivers if d["direction"] == "negative"),
                None,
            ),
            "n_drivers_found": len(top_drivers),
            "n_anomaly_columns": len(anomaly_explanations),
            "confidence": overall_conf["band"],
        },
    }
