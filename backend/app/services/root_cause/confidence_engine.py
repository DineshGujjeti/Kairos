"""
Confidence Engine — Module 7.

Every root cause finding is scored for reliability based on:
  - Sample size (more rows → higher confidence)
  - Data quality  (missing values, duplicates)
  - Method agreement (correlation + MI + RF pointing the same way)
  - Effect size   (weak correlations lower confidence)
  - Outlier influence (high outlier ratio lowers confidence)
"""
from __future__ import annotations

import math
from typing import Optional


def _sigmoid(x: float) -> float:
    """Map any real value to (0, 1)."""
    return 1.0 / (1.0 + math.exp(-x))


def score_driver_confidence(
    rows: int,
    pearson: float,
    mi: float,
    rf: Optional[float],
    missing_rate_pct: float = 0.0,
    outlier_pct: float = 0.0,
) -> dict:
    """
    Return a numeric confidence score (0-100) and a band label for a driver.

    Parameters
    ----------
    rows            : number of non-null observations
    pearson         : Pearson correlation coefficient (-1 to 1)
    mi              : normalised mutual information (0-1)
    rf              : Random Forest importance (0-1) or None
    missing_rate_pct: percentage of missing values in the dataset (0-100)
    outlier_pct     : percentage of rows that are outliers (0-100)
    """
    # ── Sample size component (0-25 pts) ─────────────────────
    # log curve: 20 rows → ~12 pts, 100 rows → ~20 pts, 500 rows → ~25 pts
    size_score = min(25.0, 25.0 * _sigmoid((math.log(max(rows, 1)) - 3.0) * 0.8))

    # ── Effect size component (0-30 pts) ─────────────────────
    # Pearson |r| plus MI contribute equally
    effect = (abs(pearson) + mi) / 2.0  # 0-1
    effect_score = effect * 30.0

    # ── Method agreement component (0-25 pts) ────────────────
    signals = [abs(pearson), mi]
    if rf is not None:
        signals.append(rf)
    strong = sum(1 for s in signals if s >= 0.15)
    agreement = strong / len(signals)
    agreement_score = agreement * 25.0

    # ── Data quality penalty (0-20 pts deducted) ─────────────
    missing_penalty = min(10.0, missing_rate_pct * 0.2)
    outlier_penalty = min(10.0, outlier_pct * 0.2)
    quality_score = 20.0 - missing_penalty - outlier_penalty

    raw = size_score + effect_score + agreement_score + quality_score
    score = max(0, min(100, raw))

    if score >= 75:
        band = "High"
    elif score >= 50:
        band = "Medium"
    else:
        band = "Low"

    return {
        "score": round(score, 1),
        "band": band,
        "components": {
            "sample_size_score": round(size_score, 1),
            "effect_size_score": round(effect_score, 1),
            "method_agreement_score": round(agreement_score, 1),
            "data_quality_score": round(quality_score, 1),
        },
    }


def score_analysis_confidence(
    rows: int,
    quality_score: float,
    missing_rate_pct: float,
    n_methods: int,
    n_drivers: int,
) -> dict:
    """
    Compute an overall confidence score for the entire root cause analysis.

    Used in the analysis-level metadata returned by every endpoint.
    """
    # Sample size
    size = min(30.0, 30.0 * _sigmoid((math.log(max(rows, 1)) - 3.0) * 0.8))

    # Data quality (quality_score is 0-100)
    quality = quality_score * 0.3

    # Coverage — more methods and more discovered drivers → more confidence
    method_cov = min(20.0, n_methods * 7.0)
    driver_cov = min(20.0, n_drivers * 2.5)

    raw = size + quality + method_cov + driver_cov
    score = max(0, min(100, raw))

    if score >= 75:
        band = "High"
    elif score >= 50:
        band = "Medium"
    else:
        band = "Low"

    return {"score": round(score, 1), "band": band}
