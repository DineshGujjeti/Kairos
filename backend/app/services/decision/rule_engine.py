"""
Business Rule Engine — Module 9.

Evaluates configurable IF metric operator threshold THEN recommendation
rules against computed dataset metrics. Returns fired rules as
Recommendation-ready dicts without touching the database.
"""
from __future__ import annotations

import uuid

import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)


# Default system rules that fire when no org-specific rules exist
_SYSTEM_RULES: list[dict] = [
    {
        "id": "sys-001",
        "name": "High Missing Data",
        "metric_name": "missing_rate_pct",
        "operator": "gt",
        "threshold": 10.0,
        "threshold_unit": "%",
        "recommendation_title": "Improve Data Quality",
        "recommendation_description": (
            "Missing value rate exceeds 10%. Implement data validation at ingestion "
            "and establish data stewardship processes to improve completeness."
        ),
        "category": "operations",
        "priority": "high",
    },
    {
        "id": "sys-002",
        "name": "High Duplicate Rate",
        "metric_name": "duplicate_rate_pct",
        "operator": "gt",
        "threshold": 5.0,
        "threshold_unit": "%",
        "recommendation_title": "Eliminate Duplicate Records",
        "recommendation_description": (
            "Duplicate row rate exceeds 5%. Review ETL pipelines and implement "
            "deduplication logic to ensure metric accuracy."
        ),
        "category": "operations",
        "priority": "medium",
    },
    {
        "id": "sys-003",
        "name": "Low Data Quality Score",
        "metric_name": "quality_score",
        "operator": "lt",
        "threshold": 70.0,
        "threshold_unit": "score",
        "recommendation_title": "Initiate Data Quality Programme",
        "recommendation_description": (
            "Overall data quality score is below 70/100. Launch a data quality "
            "initiative to address completeness, consistency, and uniqueness gaps."
        ),
        "category": "executive",
        "priority": "high",
    },
]


def _evaluate_condition(metric_value: float, operator: str, threshold: float) -> bool:
    """Test a single rule condition."""
    ops = {
        "gt": lambda v, t: v > t,
        "lt": lambda v, t: v < t,
        "gte": lambda v, t: v >= t,
        "lte": lambda v, t: v <= t,
        "eq": lambda v, t: abs(v - t) < 1e-9,
        "neq": lambda v, t: abs(v - t) >= 1e-9,
    }
    fn = ops.get(operator)
    return fn(metric_value, threshold) if fn else False


def _compute_metrics(df: pd.DataFrame) -> dict[str, float]:
    """Extract a flat dict of numeric metrics from a DataFrame for rule evaluation."""
    total_cells = len(df) * len(df.columns)
    missing_cells = int(df.isna().sum().sum())
    dup_rows = int(df.duplicated().sum())

    metrics: dict[str, float] = {
        "row_count": float(len(df)),
        "column_count": float(len(df.columns)),
        "missing_cells": float(missing_cells),
        "missing_rate_pct": round(missing_cells / total_cells * 100, 2) if total_cells else 0.0,
        "duplicate_rows": float(dup_rows),
        "duplicate_rate_pct": round(dup_rows / len(df) * 100, 2) if len(df) else 0.0,
    }

    # Add per-column numeric stats
    for col in df.select_dtypes(include="number").columns:
        s = df[col].dropna()
        if s.empty:
            continue
        metrics[f"{col}_mean"] = round(float(s.mean()), 4)
        metrics[f"{col}_sum"] = round(float(s.sum()), 4)
        metrics[f"{col}_min"] = round(float(s.min()), 4)
        metrics[f"{col}_max"] = round(float(s.max()), 4)

    return metrics


def evaluate_rules(
    df: pd.DataFrame,
    org_rules: list[dict] | None = None,
    quality_score: float = 75.0,
) -> list[dict]:
    """
    Evaluate system + org-specific rules against dataset metrics.

    Returns list of fired rule recommendation dicts (not DB objects).
    """
    metrics = _compute_metrics(df)
    metrics["quality_score"] = quality_score

    all_rules = _SYSTEM_RULES + (org_rules or [])
    fired: list[dict] = []

    for rule in all_rules:
        metric_name = rule.get("metric_name", "")
        metric_value = metrics.get(metric_name)
        if metric_value is None:
            continue

        try:
            if _evaluate_condition(float(metric_value), rule["operator"], float(rule["threshold"])):
                fired.append({
                    "rule_id": rule.get("id", str(uuid.uuid4())),
                    "rule_name": rule["name"],
                    "title": rule["recommendation_title"],
                    "description": rule["recommendation_description"],
                    "category": rule.get("category", "executive"),
                    "priority": rule.get("priority", "medium"),
                    "trigger": {
                        "metric": metric_name,
                        "actual_value": round(metric_value, 4),
                        "operator": rule["operator"],
                        "threshold": rule["threshold"],
                        "unit": rule.get("threshold_unit", ""),
                    },
                    "reason": (
                        f"Rule '{rule['name']}' fired: "
                        f"{metric_name} = {metric_value:.2f} "
                        f"{rule['operator']} {rule['threshold']}{rule.get('threshold_unit', '')}"
                    ),
                    "source": "rule_engine",
                })
        except (TypeError, ValueError) as exc:
            logger.warning("rule_evaluation_error", rule=rule.get("name"), error=str(exc))

    logger.info("rules_evaluated", total=len(all_rules), fired=len(fired))
    return fired
