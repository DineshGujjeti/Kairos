"""
Root Cause Visualization Builder — Module 7.

Builds frontend-ready visualization metadata from root cause analysis
results. All chart data is pre-computed server-side; the React layer
only needs to render, not transform.
"""
from __future__ import annotations

from typing import Any


def build_driver_importance_chart(driver_report: dict) -> dict:
    """Bar chart: driver columns sorted by importance."""
    drivers = driver_report.get("top_drivers", [])
    if not drivers:
        return {}
    return {
        "chart_type": "bar",
        "title": f"Key Drivers of {driver_report.get('target_column', 'Target')}",
        "subtitle": "Feature importance from correlation + mutual information + random forest",
        "data": {
            "x_axis": {"label": "Driver Variable", "values": [d["column"] for d in drivers]},
            "y_axis": {"label": "Composite Importance"},
            "series": [
                {"name": "Importance", "values": [d["importance"] for d in drivers]},
                {"name": "Contribution %", "values": [d.get("contribution_pct", 0) for d in drivers]},
            ],
            "colors": [
                "#22c55e" if d["direction"] == "positive" else "#ef4444"
                for d in drivers
            ],
            "metadata": {col: d for d, col in [(d, d["column"]) for d in drivers]},
        },
    }


def build_contribution_waterfall(contribution_report: dict) -> dict:
    """Waterfall chart: additive contribution of each variable."""
    waterfall = contribution_report.get("waterfall_data", [])
    if not waterfall:
        return {}
    return {
        "chart_type": "waterfall",
        "title": f"Contribution Waterfall — {contribution_report.get('target_column', 'Target')}",
        "subtitle": "How each variable contributes to the target metric",
        "data": {
            "categories": [w["label"] for w in waterfall],
            "values": [w["value"] for w in waterfall],
            "running_totals": [w["running_total"] for w in waterfall],
            "types": [w["type"] for w in waterfall],
            "baseline": contribution_report.get("target_mean", 0),
        },
    }


def build_why_chain_tree(why_chain: list[dict]) -> dict:
    """Tree / cascade chart representing the multi-level WHY reasoning."""
    if not why_chain:
        return {}
    return {
        "chart_type": "tree",
        "title": "Root Cause WHY Chain",
        "subtitle": "Multi-level causal reasoning derived from the data",
        "data": {
            "nodes": [
                {
                    "id": step["level"],
                    "question": step["question"],
                    "answer": step["answer"],
                    "driver": step.get("driver"),
                    "contribution_pct": step.get("contribution_pct"),
                    "confidence": step.get("confidence"),
                }
                for step in why_chain
            ],
            "edges": [
                {"from": i, "to": i + 1}
                for i in range(1, len(why_chain))
            ],
        },
    }


def build_influence_heatmap(driver_report: dict) -> dict:
    """Heatmap: correlation between all feature drivers and the target."""
    drivers = driver_report.get("top_drivers", [])
    if not drivers:
        return {}
    return {
        "chart_type": "heatmap",
        "title": "Driver Influence Matrix",
        "subtitle": "Pearson correlation between key drivers and the target metric",
        "data": {
            "x_labels": [d["column"] for d in drivers],
            "y_labels": [driver_report.get("target_column", "Target")],
            "values": [[d["pearson_correlation"] for d in drivers]],
            "color_range": {"min": -1.0, "max": 1.0, "midpoint": 0},
        },
    }


def build_confidence_gauge(confidence: dict) -> dict:
    """Gauge chart: overall analysis confidence score."""
    return {
        "chart_type": "gauge",
        "title": "Analysis Confidence",
        "subtitle": "Based on sample size, data quality, and method agreement",
        "data": {
            "value": confidence.get("score", 0),
            "band": confidence.get("band", "Low"),
            "max": 100,
            "thresholds": {"low": 50, "medium": 75, "high": 100},
        },
    }


def build_cause_network(driver_report: dict, contribution_report: dict) -> dict:
    """Network graph: causal relationships between variables."""
    target = driver_report.get("target_column", "Target")
    drivers = driver_report.get("top_drivers", [])[:8]
    if not drivers:
        return {}

    nodes = [{"id": target, "type": "target", "label": target}]
    edges = []

    for d in drivers:
        col = d["column"]
        nodes.append({
            "id": col,
            "type": "driver",
            "label": col,
            "importance": d["importance"],
            "direction": d["direction"],
            "confidence": d["confidence"],
        })
        edges.append({
            "source": col,
            "target": target,
            "weight": d["importance"],
            "direction": d["direction"],
            "label": f"r={d['pearson_correlation']:+.2f}",
        })

    return {
        "chart_type": "network",
        "title": "Cause-and-Effect Network",
        "subtitle": "Variables influencing the target metric",
        "data": {"nodes": nodes, "edges": edges},
    }


def build_root_cause_visualizations(
    driver_report: dict,
    contribution_report: dict,
    why_chain: list,
    overall_confidence: dict,
) -> list[dict]:
    """Assemble all Module 7 visualizations into a single list."""
    charts: list[dict] = []

    for builder, args in [
        (build_driver_importance_chart, (driver_report,)),
        (build_contribution_waterfall, (contribution_report,)),
        (build_why_chain_tree, (why_chain,)),
        (build_influence_heatmap, (driver_report,)),
        (build_confidence_gauge, (overall_confidence,)),
        (build_cause_network, (driver_report, contribution_report)),
    ]:
        try:
            chart = builder(*args)
            if chart:
                charts.append(chart)
        except Exception:
            pass

    return charts
