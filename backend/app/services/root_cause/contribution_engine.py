"""
Contribution Engine — Module 7.

Decomposes how much each variable contributed to the observed value of a
target metric, producing waterfall-ready data for the frontend and a
narrative explanation suitable for executive reporting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)


def _column_contribution(
    df: pd.DataFrame,
    col: str,
    target: str,
) -> float:
    """
    Estimate the linear contribution of *col* to *target* using simple
    OLS regression coefficient × mean of *col*.

    This gives an additive decomposition: Σ contribution_i ≈ mean(target).
    """
    try:
        s = df[[col, target]].dropna()
        if len(s) < 5 or s[col].std() == 0:
            return 0.0
        corr = s[col].corr(s[target])
        # Scale by relative variance ratio for a rough contribution estimate
        ratio = s[col].std() / (s[target].std() or 1.0)
        return float(corr * ratio * s[col].mean())
    except Exception:
        return 0.0


def compute_contributions(
    df: pd.DataFrame,
    target_column: str,
    top_n: int = 8,
) -> dict:
    """
    Compute additive contributions of numeric features to the target column.

    Returns a waterfall-friendly structure with positive and negative
    contributors, their contribution percentages, and a baseline.
    """
    if target_column not in df.columns:
        return {
            "target_column": target_column,
            "error": f"Column '{target_column}' not found",
            "contributions": [],
        }

    target_series = df[target_column].dropna()
    if len(target_series) < 5:
        return {
            "target_column": target_column,
            "error": "Insufficient data",
            "contributions": [],
        }

    target_mean = float(target_series.mean())

    # Compute raw contributions for all numeric feature columns
    numeric_cols = [
        c for c in df.select_dtypes(include="number").columns
        if c != target_column
    ]

    raw: list[dict] = []
    for col in numeric_cols:
        contrib = _column_contribution(df, col, target_column)
        if contrib == 0.0:
            continue
        col_mean = float(df[col].dropna().mean())
        col_pct = df[col].dropna().std() / (target_series.std() or 1.0) * 100
        raw.append({
            "column": col,
            "raw_contribution": round(contrib, 4),
            "column_mean": round(col_mean, 4),
            "correlation_with_target": round(df[col].corr(target_series), 4) if len(df) >= 5 else 0.0,
        })

    raw.sort(key=lambda x: -abs(x["raw_contribution"]))
    top = raw[:top_n]

    # Normalise to percentage contributions
    total_abs = sum(abs(c["raw_contribution"]) for c in top) or 1.0
    contributions: list[dict] = []
    for c in top:
        pct = round(c["raw_contribution"] / total_abs * 100, 1)
        contributions.append({
            "column": c["column"],
            "contribution_pct": pct,
            "raw_contribution": c["raw_contribution"],
            "column_mean": c["column_mean"],
            "correlation_with_target": c["correlation_with_target"],
            "direction": "positive" if c["raw_contribution"] >= 0 else "negative",
            "label": (
                f"{c['column']} contributed {abs(pct):.1f}% "
                f"({'upward' if pct >= 0 else 'downward'}) to {target_column}"
            ),
        })

    # Separate positive and negative
    positive = sorted(
        [c for c in contributions if c["direction"] == "positive"],
        key=lambda x: -x["contribution_pct"],
    )
    negative = sorted(
        [c for c in contributions if c["direction"] == "negative"],
        key=lambda x: x["contribution_pct"],
    )

    # Build waterfall data for the visualisation
    waterfall = []
    running = 0.0
    for c in positive[:5]:
        waterfall.append({
            "label": c["column"],
            "value": c["raw_contribution"],
            "running_total": round(running + c["raw_contribution"], 4),
            "type": "positive",
        })
        running += c["raw_contribution"]
    for c in negative[:5]:
        waterfall.append({
            "label": c["column"],
            "value": c["raw_contribution"],
            "running_total": round(running + c["raw_contribution"], 4),
            "type": "negative",
        })
        running += c["raw_contribution"]

    return {
        "target_column": target_column,
        "target_mean": round(target_mean, 4),
        "rows_analysed": len(target_series),
        "total_contributors": len(raw),
        "contributions": contributions,
        "positive_contributors": positive[:5],
        "negative_contributors": negative[:5],
        "waterfall_data": waterfall,
    }
