"""
Scenario Comparison Engine — Module 8 (improved).

Compares multiple named what-if scenarios with structured confidence
and dynamic recommendations.
"""
from __future__ import annotations

import pandas as pd

from app.services.simulation.model_trainer import ModelPackage
from app.services.simulation.prediction_engine import (
    _build_feature_row,
    _prediction_interval,
    compute_confidence,
    _scenario_recommendations,
    build_scenario_ai_context,
)


def compare_scenarios(
    model_pkg: ModelPackage,
    scenarios: list[dict],
) -> dict:
    """Compare multiple named scenarios against the baseline."""
    if not scenarios:
        return {"error": "No scenarios provided", "results": []}

    baseline_df = _build_feature_row({}, model_pkg)
    baseline_pred = float(model_pkg.selected_model.predict(baseline_df)[0])

    results: list[dict] = []
    for s in scenarios:
        name = s.get("name", f"Scenario {len(results) + 1}")
        variables = s.get("variables", {})

        unknown = [k for k in variables if k not in model_pkg.feature_columns]
        if unknown:
            results.append({
                "name": name,
                "error": f"Unknown columns: {unknown}",
                "prediction": None,
                "delta": None,
                "delta_pct": None,
            })
            continue

        try:
            scenario_df = _build_feature_row(variables, model_pkg)
            pred = float(model_pkg.selected_model.predict(scenario_df)[0])
            lower, upper = _prediction_interval(pred, model_pkg)
            delta = pred - baseline_pred
            delta_pct = (delta / abs(baseline_pred) * 100.0) if baseline_pred != 0 else 0.0

            results.append({
                "name": name,
                "variables": variables,
                "prediction": round(pred, 4),
                "delta": round(delta, 4),
                "delta_pct": round(delta_pct, 2),
                "prediction_interval": {"lower": lower, "upper": upper},
                "rank": 0,
                "error": None,
            })
        except Exception as exc:
            results.append({
                "name": name,
                "error": str(exc),
                "prediction": None,
                "delta": None,
                "delta_pct": None,
            })

    valid = [r for r in results if r.get("prediction") is not None]
    valid.sort(key=lambda r: -(r["prediction"] or 0))
    for rank, r in enumerate(valid, start=1):
        r["rank"] = rank

    best = valid[0]["name"] if valid else None
    worst = valid[-1]["name"] if valid else None

    chart_data = {
        "labels": ["Baseline"] + [r["name"] for r in valid],
        "predictions": [round(baseline_pred, 4)] + [r["prediction"] for r in valid],
        "deltas": [0.0] + [r["delta"] for r in valid],
    }

    # Structured confidence
    lower_b, upper_b = _prediction_interval(baseline_pred, model_pkg)
    confidence = compute_confidence(
        model_pkg.test_r2, model_pkg.rows_trained,
        len(model_pkg.feature_columns), lower_b, upper_b, baseline_pred,
    )

    recommendations = _scenario_recommendations(
        results, best, baseline_pred, model_pkg.target_column,
    )

    ai_context = build_scenario_ai_context(
        results, baseline_pred, best,
        model_pkg.target_column, model_pkg.selected_model_name, model_pkg.test_r2,
    )

    return {
        "target_column": model_pkg.target_column,
        "baseline_prediction": round(baseline_pred, 4),
        "model_used": model_pkg.selected_model_name,
        "model_r2": round(model_pkg.test_r2, 4),
        "confidence": confidence,
        "scenario_count": len(scenarios),
        "results": results,
        "best_scenario": best,
        "worst_scenario": worst,
        "chart_data": chart_data,
        "recommendations": recommendations,
        "_ai_context": ai_context,
    }
