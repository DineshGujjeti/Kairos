"""
Prediction Engine — Module 8 (improved).

Runs single-variable and multi-variable what-if simulations against a
trained ModelPackage, returning predicted values, deltas, structured
confidence scores, and dynamic business recommendations.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

from app.services.simulation.model_trainer import ModelPackage


# ─────────────────────────────────────────────────────────────────────────────
# Structured confidence scoring (Task 3)
# ─────────────────────────────────────────────────────────────────────────────


def compute_confidence(
    test_r2: float,
    rows: int,
    n_features: int,
    lower: float,
    upper: float,
    predicted: float,
) -> dict:
    """
    Return structured confidence: {level, score}.

    Score (0-100) is derived from:
      - Model R²        → 40 pts
      - Sample size     → 30 pts
      - Feature ratio   → 15 pts
      - Interval width  → 15 pts  (narrow interval = high confidence)
    """
    r2_component = max(0.0, test_r2) * 40.0

    size_component = min(30.0, 30.0 / (1.0 + math.exp(-(math.log(max(rows, 1)) - 3.0))))

    ratio = rows / max(n_features, 1)
    feature_component = min(15.0, (ratio / 10.0) * 15.0)

    # Prediction interval relative width (narrower = better)
    interval_width = abs(upper - lower)
    rel_width = interval_width / (abs(predicted) + 1e-9)
    interval_component = max(0.0, 15.0 * (1.0 - min(1.0, rel_width / 2.0)))

    score = r2_component + size_component + feature_component + interval_component
    score = round(max(0.0, min(100.0, score)), 1)

    if score >= 65:
        level = "High"
    elif score >= 40:
        level = "Medium"
    else:
        level = "Low"

    return {"level": level, "score": score}


def _prediction_interval(
    predicted: float,
    model_pkg: ModelPackage,
    z: float = 1.96,
) -> tuple[float, float]:
    """Approximate 95 % prediction interval using model RMSE."""
    if model_pkg.selected_model_name == "Random Forest" and model_pkg.rf_metrics:
        rmse = model_pkg.rf_metrics.rmse
    else:
        rmse = model_pkg.lr_metrics.rmse
    margin = z * rmse
    return round(predicted - margin, 4), round(predicted + margin, 4)


# ─────────────────────────────────────────────────────────────────────────────
# Feature row builder
# ─────────────────────────────────────────────────────────────────────────────


def _build_feature_row(
    overrides: dict[str, float],
    model_pkg: ModelPackage,
) -> pd.DataFrame:
    """
    Build a single-row feature DataFrame for prediction.
    All features not in *overrides* are set to their training-set mean.
    """
    unknown = [k for k in overrides if k not in model_pkg.feature_columns]
    if unknown:
        raise ValueError(
            f"Column(s) not in model feature set: {unknown}. "
            f"Available: {model_pkg.feature_columns}"
        )
    row = {col: model_pkg.feature_means.get(col, 0.0) for col in model_pkg.feature_columns}
    row.update(overrides)           # ALL override values applied together
    return pd.DataFrame([row])[model_pkg.feature_columns]


# ─────────────────────────────────────────────────────────────────────────────
# Business recommendations generator (Task 5)
# ─────────────────────────────────────────────────────────────────────────────


def _single_recommendations(
    variable: str,
    delta: float,
    delta_pct: float,
    change_pct: float,
    confidence: dict,
    target_column: str,
) -> list[str]:
    """Generate dynamic recommendations for single-variable simulation."""
    recs = []
    direction = "increases" if delta >= 0 else "decreases"
    magnitude = "significantly" if abs(delta_pct) > 10 else ("moderately" if abs(delta_pct) > 2 else "marginally")

    recs.append(
        f"Changing '{variable}' by {change_pct:+.1f}% {direction} "
        f"'{target_column}' {magnitude} ({delta_pct:+.1f}%)."
    )

    if abs(delta_pct) < 1.0:
        recs.append(
            f"'{variable}' has negligible influence on '{target_column}' — "
            f"consider focusing optimization efforts on higher-impact variables."
        )
    elif delta >= 0:
        recs.append(
            f"Increasing '{variable}' appears favorable; validate whether "
            f"this change is operationally and financially feasible."
        )
    else:
        recs.append(
            f"Reducing '{variable}' is predicted to decrease '{target_column}'; "
            f"assess whether cost savings or other benefits justify this trade-off."
        )

    if confidence["level"] == "Low":
        recs.append(
            "Model confidence is low — collect more data or review feature "
            "selection before acting on this prediction."
        )
    elif confidence["level"] == "High":
        recs.append(
            f"High model confidence (score {confidence['score']}) supports "
            "using this prediction for operational planning."
        )

    return recs


def _multi_recommendations(
    variable_impacts: list[dict],
    delta_pct: float,
    target_column: str,
    confidence: dict,
) -> list[str]:
    """Generate dynamic recommendations for multi-variable simulation."""
    recs = []

    if not variable_impacts:
        return [f"Apply variable changes and monitor '{target_column}' closely."]

    top = variable_impacts[0]
    bottom = variable_impacts[-1]

    recs.append(
        f"'{top['variable']}' is the strongest driver in this scenario "
        f"(isolated delta: {top['isolated_delta']:+.4f}); "
        f"prioritize optimizing this variable first."
    )

    if abs(bottom["isolated_delta"]) < 0.01 * abs(top["isolated_delta"]):
        recs.append(
            f"'{bottom['variable']}' shows negligible isolated impact — "
            f"its effect is likely absorbed by stronger correlated variables "
            f"already present in the scenario."
        )

    direction = "positive" if delta_pct >= 0 else "negative"
    recs.append(
        f"The combined scenario produces a {direction} effect of "
        f"{delta_pct:+.1f}% on '{target_column}'."
    )

    negatives = [v for v in variable_impacts if v["direction"] == "negative"]
    if negatives:
        recs.append(
            f"Variables with negative isolated impact: "
            f"{', '.join(v['variable'] for v in negatives[:3])}. "
            f"Consider whether these changes are necessary for the scenario."
        )

    if confidence["level"] == "Low":
        recs.append(
            "Model confidence is low — validate this multi-variable scenario "
            "with domain experts before implementation."
        )

    return recs


def _sensitivity_recommendations(
    sensitivity_ranking: list[dict],
    target_column: str,
) -> list[str]:
    """Generate dynamic recommendations from sensitivity ranking."""
    recs = []
    if not sensitivity_ranking:
        return [f"No sensitivity data available for '{target_column}'."]

    top = sensitivity_ranking[0]
    recs.append(
        f"'{top['column']}' is the highest-leverage variable "
        f"(relative sensitivity {top['relative_sensitivity']:.0f}/100, "
        f"elasticity {top['elasticity']:+.2f}): "
        f"small changes here produce large movements in '{target_column}'."
    )

    low_impact = [r for r in sensitivity_ranking if r["relative_sensitivity"] < 10]
    if low_impact:
        names = ", ".join(f"'{r['column']}'" for r in low_impact[:3])
        recs.append(
            f"{names} show low sensitivity — deprioritize these in "
            f"optimization efforts targeting '{target_column}'."
        )

    positive_levers = [r for r in sensitivity_ranking if r["direction"] == "positive"]
    if positive_levers:
        recs.append(
            f"Focus growth initiatives on: "
            f"{', '.join(r['column'] for r in positive_levers[:3])} — "
            f"increasing these variables positively affects '{target_column}'."
        )

    negative_levers = [r for r in sensitivity_ranking if r["direction"] == "negative"]
    if negative_levers:
        recs.append(
            f"Risk management should monitor: "
            f"{', '.join(r['column'] for r in negative_levers[:3])} — "
            f"increases in these variables reduce '{target_column}'."
        )

    return recs


def _scenario_recommendations(
    results: list[dict],
    best_scenario: str | None,
    baseline: float,
    target_column: str,
) -> list[str]:
    """Generate dynamic recommendations from scenario comparison."""
    recs = []
    valid = [r for r in results if r.get("prediction") is not None]

    if not valid:
        return ["No valid scenarios to compare."]

    # Sort descending so index 0 = best (highest prediction), -1 = worst (lowest)
    valid_sorted = sorted(valid, key=lambda r: -(r["prediction"] or 0))

    if best_scenario:
        best = next((r for r in valid_sorted if r["name"] == best_scenario), None)
        if best:
            recs.append(
                f"Scenario '{best_scenario}' is recommended: it produces the "
                f"highest predicted '{target_column}' ({best['prediction']:.4f}, "
                f"{best['delta_pct']:+.1f}% vs baseline)."
            )

    if len(valid_sorted) > 1:
        worst = valid_sorted[-1]  # lowest prediction after descending sort
        recs.append(
            f"Scenario '{worst['name']}' produces the lowest predicted value "
            f"({worst['prediction']:.4f}) — avoid unless other business factors "
            f"justify the trade-off."
        )

    positives = [r for r in valid if (r.get("delta") or 0) > 0]
    negatives = [r for r in valid if (r.get("delta") or 0) <= 0]
    if negatives:
        names = ", ".join(f"'{r['name']}'" for r in negatives[:2])
        recs.append(
            f"{names} produce outcomes below baseline — reconsider these "
            f"scenario parameters before deployment."
        )

    if len(valid) >= 3:
        spread = max(r["prediction"] for r in valid) - min(r["prediction"] for r in valid)
        spread_pct = spread / abs(baseline) * 100 if baseline else 0
        recs.append(
            f"The spread across all scenarios is {spread_pct:.1f}% of baseline — "
            f"{'high scenario sensitivity: small variable changes matter greatly.' if spread_pct > 20 else 'moderate scenario sensitivity: variables have bounded impact.'}"
        )

    return recs


# ─────────────────────────────────────────────────────────────────────────────
# Zero/negligible impact explanations (Task 4)
# ─────────────────────────────────────────────────────────────────────────────


def _explain_impact(
    variable: str,
    isolated_delta: float,
    change_pct: float,
    target_column: str,
    top_delta: float,
) -> str | None:
    """
    Return a business explanation if the impact is zero, negative, or negligible.
    Returns None if the impact is significant and positive (no explanation needed).
    """
    if top_delta == 0:
        ratio = 0.0
    else:
        ratio = abs(isolated_delta) / (abs(top_delta) + 1e-9)

    if abs(isolated_delta) < 1e-8:
        return (
            f"'{variable}' shows zero isolated impact. This is likely because "
            f"the model learned that '{variable}' has no direct linear relationship "
            f"with '{target_column}' in this dataset — possibly dominated by other "
            f"correlated variables already in the scenario."
        )
    if ratio < 0.05:
        return (
            f"'{variable}' has negligible influence ({isolated_delta:+.4f}) "
            f"compared to the dominant driver in this scenario. "
            f"Historical data indicates '{target_column}' is primarily determined "
            f"by other variables rather than '{variable}'."
        )
    if isolated_delta < 0:
        return (
            f"'{variable}' has a negative isolated effect ({isolated_delta:+.4f}) on "
            f"'{target_column}'. Increasing '{variable}' is associated with lower "
            f"'{target_column}' in historical data — review whether this "
            f"relationship is causal or coincidental."
        )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Simulation-specific AI prompt context builders (Task 1)
# ─────────────────────────────────────────────────────────────────────────────


def build_single_ai_context(
    variable: str,
    original_value: float,
    new_value: float,
    change_pct: float,
    delta: float,
    delta_pct: float,
    baseline_pred: float,
    scenario_pred: float,
    confidence: dict,
    target_column: str,
    model_name: str,
    model_r2: float,
) -> str:
    """Build simulation-specific context for the AI prompt."""
    return (
        f"SIMULATION TYPE: Single-Variable What-If\n"
        f"TARGET METRIC: {target_column}\n"
        f"MODEL: {model_name} (Test R²={model_r2:.3f})\n\n"
        f"CHANGE: '{variable}' changed from {original_value:.4f} to {new_value:.4f} "
        f"({change_pct:+.1f}%)\n\n"
        f"PREDICTION:\n"
        f"  Baseline: {baseline_pred:.4f}\n"
        f"  Scenario: {scenario_pred:.4f}\n"
        f"  Delta: {delta:+.4f} ({delta_pct:+.1f}%)\n\n"
        f"CONFIDENCE: {confidence['level']} (score={confidence['score']})\n"
    )


def build_multi_ai_context(
    scenario: dict,
    variable_impacts: list[dict],
    delta: float,
    delta_pct: float,
    baseline_pred: float,
    scenario_pred: float,
    confidence: dict,
    target_column: str,
    model_name: str,
    model_r2: float,
) -> str:
    """Build multi-variable simulation-specific context for the AI prompt."""
    impact_lines = "\n".join(
        f"  - '{imp['variable']}': {imp['original_value']:.4f} → {imp['new_value']:.4f} "
        f"(isolated delta: {imp['isolated_delta']:+.4f}, {imp['direction']})"
        for imp in variable_impacts
    )
    return (
        f"SIMULATION TYPE: Multi-Variable What-If\n"
        f"TARGET METRIC: {target_column}\n"
        f"MODEL: {model_name} (Test R²={model_r2:.3f})\n\n"
        f"SCENARIO VARIABLES AND ISOLATED IMPACTS:\n{impact_lines}\n\n"
        f"COMBINED PREDICTION:\n"
        f"  Baseline: {baseline_pred:.4f}\n"
        f"  Scenario: {scenario_pred:.4f}\n"
        f"  Combined Delta: {delta:+.4f} ({delta_pct:+.1f}%)\n\n"
        f"CONFIDENCE: {confidence['level']} (score={confidence['score']})\n"
    )


def build_sensitivity_ai_context(
    sensitivity_ranking: list[dict],
    target_column: str,
    model_name: str,
    model_r2: float,
) -> str:
    """Build sensitivity analysis-specific context for the AI prompt."""
    lines = "\n".join(
        f"  Rank {r['rank']}: '{r['column']}' — relative_sensitivity={r['relative_sensitivity']:.1f}/100, "
        f"elasticity={r['elasticity']:+.2f}, direction={r['direction']}"
        for r in sensitivity_ranking[:8]
    )
    return (
        f"ANALYSIS TYPE: Sensitivity Analysis\n"
        f"TARGET METRIC: {target_column}\n"
        f"MODEL: {model_name} (Test R²={model_r2:.3f})\n\n"
        f"SENSITIVITY RANKING (most to least influential):\n{lines}\n"
    )


def build_scenario_ai_context(
    results: list[dict],
    baseline: float,
    best_scenario: str | None,
    target_column: str,
    model_name: str,
    model_r2: float,
) -> str:
    """Build scenario comparison-specific context for the AI prompt."""
    lines = "\n".join(
        f"  '{r['name']}': prediction={r.get('prediction', 'N/A')}, "
        f"delta={r.get('delta_pct', 0):+.1f}%, rank={r.get('rank', 'N/A')}"
        for r in results
        if r.get("prediction") is not None
    )
    return (
        f"ANALYSIS TYPE: Scenario Comparison\n"
        f"TARGET METRIC: {target_column}\n"
        f"MODEL: {model_name} (Test R²={model_r2:.3f})\n"
        f"BASELINE: {baseline:.4f}\n\n"
        f"SCENARIOS (ranked best to worst):\n{lines}\n\n"
        f"RECOMMENDED SCENARIO: {best_scenario or 'N/A'}\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public simulation functions
# ─────────────────────────────────────────────────────────────────────────────


def simulate_single(
    model_pkg: ModelPackage,
    variable: str,
    new_value: float,
    base_overrides: dict[str, float] | None = None,
) -> dict:
    """
    Predict target when *variable* changes to *new_value*, all else at means.
    Returns structured confidence, recommendations, and AI context.
    """
    if variable not in model_pkg.feature_columns:
        raise ValueError(
            f"Column '{variable}' not in model feature set. "
            f"Available: {model_pkg.feature_columns}"
        )

    base_row = base_overrides.copy() if base_overrides else {}
    baseline_df = _build_feature_row(base_row, model_pkg)
    baseline_pred = float(model_pkg.selected_model.predict(baseline_df)[0])

    scenario_row = {**base_row, variable: new_value}
    scenario_df = _build_feature_row(scenario_row, model_pkg)
    scenario_pred = float(model_pkg.selected_model.predict(scenario_df)[0])

    delta = scenario_pred - baseline_pred
    delta_pct = (delta / abs(baseline_pred) * 100.0) if baseline_pred != 0 else 0.0

    lower, upper = _prediction_interval(scenario_pred, model_pkg)
    confidence = compute_confidence(
        model_pkg.test_r2, model_pkg.rows_trained,
        len(model_pkg.feature_columns), lower, upper, scenario_pred,
    )

    original_mean = model_pkg.feature_means.get(variable, 0.0)
    change_pct = ((new_value - original_mean) / abs(original_mean) * 100.0) if original_mean != 0 else 0.0

    recommendations = _single_recommendations(
        variable, delta, delta_pct, change_pct,
        confidence, model_pkg.target_column,
    )

    ai_context = build_single_ai_context(
        variable, original_mean, new_value, change_pct,
        delta, delta_pct, baseline_pred, scenario_pred,
        confidence, model_pkg.target_column,
        model_pkg.selected_model_name, model_pkg.test_r2,
    )

    return {
        "simulation_type": "single_variable",
        "variable": variable,
        "original_value": round(original_mean, 4),
        "new_value": round(new_value, 4),
        "change_pct": round(change_pct, 2),
        "baseline_prediction": round(baseline_pred, 4),
        "scenario_prediction": round(scenario_pred, 4),
        "delta": round(delta, 4),
        "delta_pct": round(delta_pct, 2),
        "prediction_interval": {"lower": lower, "upper": upper, "confidence": "95%"},
        "confidence": confidence,
        "model_used": model_pkg.selected_model_name,
        "model_r2": round(model_pkg.test_r2, 4),
        "recommendations": recommendations,
        "_ai_context": ai_context,   # consumed by route, not in response
    }


def simulate_multi(
    model_pkg: ModelPackage,
    scenario: dict[str, float],
) -> dict:
    """
    Predict target when multiple variables change simultaneously.
    ALL variables in *scenario* are applied together to the prediction.
    Per-variable impacts show each variable's isolated contribution.
    """
    unknown = [k for k in scenario if k not in model_pkg.feature_columns]
    if unknown:
        raise ValueError(
            f"Column(s) not in model feature set: {unknown}. "
            f"Available: {model_pkg.feature_columns}"
        )

    baseline_df = _build_feature_row({}, model_pkg)
    baseline_pred = float(model_pkg.selected_model.predict(baseline_df)[0])

    # All scenario variables applied simultaneously — this is the combined prediction
    scenario_df = _build_feature_row(scenario, model_pkg)
    scenario_pred = float(model_pkg.selected_model.predict(scenario_df)[0])

    delta = scenario_pred - baseline_pred
    delta_pct = (delta / abs(baseline_pred) * 100.0) if baseline_pred != 0 else 0.0

    lower, upper = _prediction_interval(scenario_pred, model_pkg)
    confidence = compute_confidence(
        model_pkg.test_r2, model_pkg.rows_trained,
        len(model_pkg.feature_columns), lower, upper, scenario_pred,
    )

    # Per-variable isolated contributions (each variable changed solo)
    variable_impacts = []
    top_delta = max((abs(float(model_pkg.selected_model.predict(_build_feature_row({col: val}, model_pkg))[0]) - baseline_pred)
                     for col, val in scenario.items()), default=1.0)

    for col, new_val in scenario.items():
        solo_df = _build_feature_row({col: new_val}, model_pkg)
        solo_pred = float(model_pkg.selected_model.predict(solo_df)[0])
        solo_delta = solo_pred - baseline_pred
        orig = model_pkg.feature_means.get(col, 0.0)
        change = ((new_val - orig) / abs(orig) * 100.0) if orig != 0 else 0.0

        explanation = _explain_impact(col, solo_delta, change, model_pkg.target_column, top_delta)

        impact = {
            "variable": col,
            "original_value": round(orig, 4),
            "new_value": round(new_val, 4),
            "change_pct": round(change, 2),
            "isolated_delta": round(solo_delta, 4),
            "direction": "positive" if solo_delta >= 0 else "negative",
        }
        if explanation:
            impact["explanation"] = explanation
        variable_impacts.append(impact)

    variable_impacts.sort(key=lambda x: -abs(x["isolated_delta"]))

    recommendations = _multi_recommendations(
        variable_impacts, delta_pct, model_pkg.target_column, confidence,
    )

    ai_context = build_multi_ai_context(
        scenario, variable_impacts, delta, delta_pct,
        baseline_pred, scenario_pred, confidence,
        model_pkg.target_column, model_pkg.selected_model_name, model_pkg.test_r2,
    )

    return {
        "simulation_type": "multi_variable",
        "scenario": scenario,
        "variable_count": len(scenario),
        "baseline_prediction": round(baseline_pred, 4),
        "scenario_prediction": round(scenario_pred, 4),
        "delta": round(delta, 4),
        "delta_pct": round(delta_pct, 2),
        "prediction_interval": {"lower": lower, "upper": upper, "confidence": "95%"},
        "variable_impacts": variable_impacts,
        "confidence": confidence,
        "model_used": model_pkg.selected_model_name,
        "model_r2": round(model_pkg.test_r2, 4),
        "recommendations": recommendations,
        "_ai_context": ai_context,
    }
