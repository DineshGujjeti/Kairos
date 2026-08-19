"""
Simulation Visualization Builder — Module 8.

Builds frontend-ready chart metadata from simulation results.
The React layer renders these directly — no data transformation needed.
"""
from __future__ import annotations


def build_single_simulation_chart(result: dict) -> dict:
    """Bar/gauge showing baseline vs scenario prediction."""
    return {
        "chart_type": "bar",
        "title": f"What-If: {result.get('variable', 'Variable')} = {result.get('new_value')}",
        "subtitle": f"Impact on {result.get('target_column', 'Target')} — {result.get('model_used')}",
        "data": {
            "labels": ["Baseline", "Scenario"],
            "values": [result.get("baseline_prediction", 0), result.get("scenario_prediction", 0)],
            "delta": result.get("delta", 0),
            "delta_pct": result.get("delta_pct", 0),
            "prediction_interval": result.get("prediction_interval", {}),
        },
    }


def build_multi_simulation_chart(result: dict) -> dict:
    """Waterfall showing isolated impact of each changed variable."""
    impacts = result.get("variable_impacts", [])
    return {
        "chart_type": "waterfall",
        "title": "Multi-Variable What-If Impact",
        "subtitle": f"Breakdown by variable — {result.get('model_used')}",
        "data": {
            "baseline": result.get("baseline_prediction", 0),
            "final": result.get("scenario_prediction", 0),
            "categories": [i["variable"] for i in impacts],
            "values": [i["isolated_delta"] for i in impacts],
            "directions": [i["direction"] for i in impacts],
        },
    }


def build_sensitivity_chart(sensitivity_result: dict) -> dict:
    """Bar chart: sensitivity ranking of all features."""
    ranking = sensitivity_result.get("sensitivity_ranking", [])
    return {
        "chart_type": "bar",
        "title": f"Sensitivity Analysis — {sensitivity_result.get('target_column', 'Target')}",
        "subtitle": "How much the target changes per unit change in each variable",
        "data": {
            "x_axis": {"label": "Feature", "values": [r["column"] for r in ranking]},
            "y_axis": {"label": "Relative Sensitivity (0-100)"},
            "series": [
                {"name": "Sensitivity", "values": [r["relative_sensitivity"] for r in ranking]},
                {"name": "Elasticity", "values": [r["elasticity"] for r in ranking]},
            ],
            "colors": [
                "#22c55e" if r["direction"] == "positive" else "#ef4444"
                for r in ranking
            ],
        },
    }


def build_sensitivity_sweep_charts(sensitivity_result: dict) -> list[dict]:
    """One line chart per feature showing how the target varies across the feature's range."""
    charts = []
    for sweep in sensitivity_result.get("sweep_data", [])[:6]:  # top 6 only
        charts.append({
            "chart_type": "line",
            "title": f"Sensitivity Sweep — {sweep['column']}",
            "subtitle": f"Impact on {sensitivity_result.get('target_column', 'Target')} "
                        f"as {sweep['column']} varies",
            "data": {
                "x_axis": {"label": sweep["column"], "values": sweep["x_values"]},
                "y_axis": {"label": sensitivity_result.get("target_column", "Target")},
                "series": [{"name": "Predicted", "values": sweep["y_values"]}],
                "elasticity": sweep["elasticity"],
                "direction": sweep["direction"],
            },
        })
    return charts


def build_scenario_comparison_chart(comparison_result: dict) -> dict:
    """Bar chart comparing all named scenarios."""
    chart_data = comparison_result.get("chart_data", {})
    return {
        "chart_type": "bar",
        "title": f"Scenario Comparison — {comparison_result.get('target_column', 'Target')}",
        "subtitle": f"Best: {comparison_result.get('best_scenario', 'N/A')} | "
                    f"Model: {comparison_result.get('model_used', 'N/A')}",
        "data": {
            "x_axis": {"label": "Scenario", "values": chart_data.get("labels", [])},
            "y_axis": {"label": "Predicted Value"},
            "series": [
                {"name": "Prediction", "values": chart_data.get("predictions", [])},
            ],
            "deltas": chart_data.get("deltas", []),
            "baseline": comparison_result.get("baseline_prediction", 0),
        },
    }


def build_model_comparison_chart(model_metrics: dict) -> dict:
    """Bar chart comparing LR vs RF model metrics."""
    lr = model_metrics.get("linear_regression") or {}
    rf = model_metrics.get("random_forest") or {}
    models = ["Linear Regression"]
    r2_vals = [lr.get("r2", 0)]
    rmse_vals = [lr.get("rmse", 0)]

    if rf:
        models.append("Random Forest")
        r2_vals.append(rf.get("r2", 0))
        rmse_vals.append(rf.get("rmse", 0))

    return {
        "chart_type": "bar",
        "title": "Model Comparison: Linear Regression vs Random Forest",
        "subtitle": f"Selected: {model_metrics.get('selected_model', 'N/A')} "
                    f"(Test R²={model_metrics.get('test_r2', 0):.3f})",
        "data": {
            "x_axis": {"label": "Model", "values": models},
            "y_axis": {"label": "Score"},
            "series": [
                {"name": "R² (Test)", "values": r2_vals},
                {"name": "RMSE", "values": rmse_vals},
            ],
        },
    }
