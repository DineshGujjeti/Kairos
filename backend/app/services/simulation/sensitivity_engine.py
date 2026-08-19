"""
Sensitivity Analysis — Module 8 (improved).

Sweeps each feature column across its range to measure sensitivity,
returning elasticity, structured confidence, and recommendations.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from app.services.simulation.model_trainer import ModelPackage
from app.services.simulation.prediction_engine import (
    _build_feature_row,
    _prediction_interval,
    compute_confidence,
    _sensitivity_recommendations,
    build_sensitivity_ai_context,
)


def _sweep_column(
    model_pkg: ModelPackage,
    column: str,
    n_steps: int = 20,
    std_range: float = 2.0,
) -> dict:
    mean = model_pkg.feature_means.get(column, 0.0)
    std = model_pkg.feature_stds.get(column, 1.0)
    col_min = model_pkg.feature_mins.get(column, mean - std_range * std)
    col_max = model_pkg.feature_maxs.get(column, mean + std_range * std)

    lo = max(col_min, mean - std_range * std)
    hi = min(col_max, mean + std_range * std)
    if lo >= hi:
        lo, hi = col_min, col_max
    if lo >= hi:
        lo, hi = mean - 1.0, mean + 1.0

    x_values = np.linspace(lo, hi, n_steps).tolist()
    y_values: list[float] = []
    for x in x_values:
        row = _build_feature_row({column: x}, model_pkg)
        y_values.append(float(model_pkg.selected_model.predict(row)[0]))

    y_arr = np.array(y_values)
    x_arr = np.array(x_values)
    delta_y = y_arr[-1] - y_arr[0]
    delta_x = x_arr[-1] - x_arr[0]
    y_at_mean = y_arr[n_steps // 2]

    elasticity = 0.0
    if mean != 0 and y_at_mean != 0 and delta_x != 0:
        pct_y = delta_y / abs(y_at_mean)
        pct_x = delta_x / abs(mean)
        elasticity = float(pct_y / pct_x) if pct_x != 0 else 0.0

    sensitivity_score = abs(delta_y / delta_x) if delta_x != 0 else 0.0

    return {
        "column": column,
        "x_values": [round(x, 4) for x in x_values],
        "y_values": [round(y, 4) for y in y_values],
        "sensitivity_score": round(sensitivity_score, 6),
        "elasticity": round(elasticity, 4),
        "direction": "positive" if delta_y >= 0 else "negative",
        "range": {"min": round(lo, 4), "max": round(hi, 4), "mean": round(mean, 4)},
    }


def run_sensitivity_analysis(
    model_pkg: ModelPackage,
    columns: Optional[list[str]] = None,
    n_steps: int = 20,
    std_range: float = 2.0,
    top_n: int = 10,
) -> dict:
    """Run sensitivity analysis across all (or specified) feature columns."""
    target_cols = [c for c in (columns or model_pkg.feature_columns)
                   if c in model_pkg.feature_columns]

    results: list[dict] = []
    for col in target_cols:
        try:
            sweep = _sweep_column(model_pkg, col, n_steps=n_steps, std_range=std_range)
            results.append(sweep)
        except Exception:
            pass

    results.sort(key=lambda r: -r["sensitivity_score"])

    max_score = max((r["sensitivity_score"] for r in results), default=1.0) or 1.0
    for r in results:
        r["relative_sensitivity"] = round(r["sensitivity_score"] / max_score * 100.0, 1)

    top = results[:top_n]

    # Structured confidence for the overall analysis
    dummy_pred = float(model_pkg.selected_model.predict(
        _build_feature_row({}, model_pkg))[0])
    lower, upper = _prediction_interval(dummy_pred, model_pkg)
    confidence = compute_confidence(
        model_pkg.test_r2, model_pkg.rows_trained,
        len(model_pkg.feature_columns), lower, upper, dummy_pred,
    )

    ranking = [
        {
            "rank": i + 1,
            "column": r["column"],
            "sensitivity_score": r["sensitivity_score"],
            "relative_sensitivity": r["relative_sensitivity"],
            "elasticity": r["elasticity"],
            "direction": r["direction"],
        }
        for i, r in enumerate(top)
    ]

    recommendations = _sensitivity_recommendations(ranking, model_pkg.target_column)

    ai_context = build_sensitivity_ai_context(
        ranking, model_pkg.target_column,
        model_pkg.selected_model_name, model_pkg.test_r2,
    )

    return {
        "target_column": model_pkg.target_column,
        "model_used": model_pkg.selected_model_name,
        "model_r2": round(model_pkg.test_r2, 4),
        "confidence": confidence,
        "columns_analysed": len(results),
        "sensitivity_ranking": ranking,
        "sweep_data": top,
        "most_sensitive": top[0]["column"] if top else None,
        "least_sensitive": results[-1]["column"] if results else None,
        "recommendations": recommendations,
        "_ai_context": ai_context,
    }
