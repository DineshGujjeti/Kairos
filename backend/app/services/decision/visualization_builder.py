"""
Decision Visualization Builder — Module 9.

Builds frontend-ready chart metadata from decision and recommendation results.
"""
from __future__ import annotations


def build_priority_distribution_chart(recommendations: list[dict]) -> dict:
    """Pie chart: count of high/medium/low priority recommendations."""
    counts = {"high": 0, "medium": 0, "low": 0}
    for r in recommendations:
        p = str(r.get("priority", "medium")).lower()
        if p in counts:
            counts[p] += 1
    return {
        "chart_type": "pie",
        "title": "Recommendation Priority Distribution",
        "subtitle": f"{len(recommendations)} total recommendations",
        "data": {
            "labels": ["High", "Medium", "Low"],
            "values": [counts["high"], counts["medium"], counts["low"]],
            "colors": ["#ef4444", "#f59e0b", "#22c55e"],
        },
    }


def build_roi_comparison_chart(recommendations: list[dict]) -> dict:
    """Horizontal bar chart: ROI score per recommendation."""
    top = recommendations[:10]
    return {
        "chart_type": "bar",
        "title": "ROI Score by Recommendation",
        "subtitle": "Higher score indicates better return on investment",
        "data": {
            "x_axis": {"label": "ROI Score", "values": [r.get("roi_score", 0) for r in top]},
            "y_axis": {"label": "Recommendation", "values": [r.get("title", "")[:40] for r in top]},
            "orientation": "horizontal",
            "series": [{"name": "ROI Score", "values": [r.get("roi_score", 0) for r in top]}],
        },
    }


def build_impact_matrix_chart(recommendations: list[dict]) -> dict:
    """Scatter chart: effort (x) vs impact (y) for each recommendation."""
    points = [
        {
            "label": r.get("title", "")[:30],
            "x": r.get("effort_score", 50),
            "y": r.get("impact_score", 50),
            "priority": r.get("priority", "medium"),
            "overall_score": r.get("overall_score", 50),
        }
        for r in recommendations
    ]
    return {
        "chart_type": "scatter",
        "title": "Impact vs Effort Matrix",
        "subtitle": "Top-right = high impact, easy to implement (best ROI)",
        "data": {
            "x_axis": {"label": "Effort Score (higher = easier)"},
            "y_axis": {"label": "Impact Score"},
            "points": points,
        },
    }


def build_recommendation_ranking_chart(recommendations: list[dict]) -> dict:
    """Bar chart: overall_score per recommendation, sorted."""
    top = sorted(recommendations, key=lambda r: -(r.get("overall_score") or 0))[:10]
    return {
        "chart_type": "bar",
        "title": "Recommendation Ranking by Overall Score",
        "subtitle": "Composite of impact, ROI, urgency, confidence, and effort",
        "data": {
            "x_axis": {"label": "Recommendation", "values": [r.get("title", "")[:35] for r in top]},
            "y_axis": {"label": "Overall Score (0-100)"},
            "series": [{"name": "Overall Score", "values": [r.get("overall_score", 0) for r in top]}],
        },
    }


def build_decision_timeline_chart(recommendations: list[dict]) -> dict:
    """Bar chart: count of recommendations per timeline bucket."""
    buckets: dict[str, int] = {
        "immediate": 0,
        "30 days": 0,
        "90 days": 0,
        "6 months": 0,
        "12 months": 0,
    }
    for r in recommendations:
        tl = str(r.get("timeline", "90 days")).lower()
        for key in buckets:
            if key in tl:
                buckets[key] += 1
                break
        else:
            buckets["90 days"] += 1
    return {
        "chart_type": "bar",
        "title": "Recommendation Implementation Timeline",
        "subtitle": "When to action each recommendation",
        "data": {
            "x_axis": {"label": "Timeline", "values": list(buckets.keys())},
            "y_axis": {"label": "Recommendation Count"},
            "series": [{"name": "Count", "values": list(buckets.values())}],
        },
    }


def build_risk_matrix_chart(recommendations: list[dict]) -> dict:
    """Scatter: confidence (x) vs urgency (y) as proxy for risk."""
    points = [
        {
            "label": r.get("title", "")[:30],
            "x": r.get("confidence_score", 50),
            "y": r.get("urgency_score", 50),
            "risk": r.get("risk", ""),
        }
        for r in recommendations
    ]
    return {
        "chart_type": "scatter",
        "title": "Risk Matrix: Confidence vs Urgency",
        "subtitle": "Bottom-right = urgent but low confidence (highest risk)",
        "data": {
            "x_axis": {"label": "Confidence Score"},
            "y_axis": {"label": "Urgency Score"},
            "points": points,
        },
    }


def build_category_breakdown_chart(recommendations: list[dict]) -> dict:
    """Bar chart: count of recommendations per category."""
    counts: dict[str, int] = {}
    for r in recommendations:
        cat = str(r.get("category", "executive"))
        counts[cat] = counts.get(cat, 0) + 1
    labels = list(counts.keys())
    values = [counts[k] for k in labels]
    return {
        "chart_type": "bar",
        "title": "Recommendations by Business Category",
        "data": {
            "x_axis": {"label": "Category", "values": labels},
            "y_axis": {"label": "Count"},
            "series": [{"name": "Count", "values": values}],
        },
    }


def build_all_decision_visualizations(recommendations: list[dict]) -> list[dict]:
    """Build the full set of Module 9 visualizations."""
    if not recommendations:
        return []
    charts = []
    for builder in [
        build_priority_distribution_chart,
        build_recommendation_ranking_chart,
        build_roi_comparison_chart,
        build_impact_matrix_chart,
        build_decision_timeline_chart,
        build_risk_matrix_chart,
        build_category_breakdown_chart,
    ]:
        try:
            chart = builder(recommendations)
            if chart:
                charts.append(chart)
        except Exception:
            pass
    return charts
