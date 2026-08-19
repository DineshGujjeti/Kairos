"""
Enterprise AI Response Parser — Module 6.

Parses raw Gemini JSON output into the canonical AIAnalysisResponse
schema. Handles malformed responses gracefully with clear fallbacks.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if Gemini wraps output in them."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json(text: str) -> dict:
    """
    Attempt JSON extraction from raw Gemini text.
    1. Direct parse after fence stripping.
    2. Find the first { … } block.
    3. Return empty dict with error marker.
    """
    cleaned = _strip_fences(text)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find first complete JSON object
    start = cleaned.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(cleaned[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[start : i + 1])
                    except json.JSONDecodeError:
                        break

    logger.warning("gemini_json_parse_failed", preview=text[:200])
    return {"_parse_error": True, "raw": text}


def _ensure_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        return [value]
    return []


def parse_to_response(
    raw_text: str,
    template_name: str,
    context: dict,
) -> dict:
    """
    Parse Gemini's raw JSON response into AIAnalysisResponse fields.

    Always returns a dict with keys:
      summary, insights, recommendations, visualizations, metadata
    """
    parsed = _extract_json(raw_text) if raw_text else {}
    parse_error = parsed.pop("_parse_error", False)
    raw_fallback = parsed.pop("raw", "")

    # ── Build summary ──────────────────────────────────────────
    summary = (
        parsed.get("executive_summary")
        or parsed.get("detailed_answer")
        or parsed.get("answer")
        or (raw_fallback[:400] if parse_error else "Analysis complete")
    )

    # ── Build insights list ────────────────────────────────────
    insights: list[str] = []

    # Pull structured insight objects
    for key in ("key_insights", "business_risks", "growth_opportunities",
                "anomalies", "root_causes", "recommendations"):
        items = parsed.get(key, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    title = item.get("title") or item.get("risk_title") or item.get("opportunity_title") or item.get("anomaly_title") or item.get("cause") or ""
                    body = item.get("finding") or item.get("description") or item.get("business_impact") or ""
                    if title or body:
                        insights.append(f"[{title}] {body}".strip("[] "))
                elif isinstance(item, str):
                    insights.append(item)

    # Headline findings / market signals / root cause hypotheses as additional insights
    for key in ("headline_findings", "market_signals", "root_cause_hypotheses",
                "data_quality_risks", "supporting_evidence"):
        insights.extend(_ensure_list(parsed.get(key, [])))

    # EDA insights from the context (always include a few)
    eda_ins = (context.get("eda", {}).get("insights") or {}).get("insights", [])
    if eda_ins and not insights:
        insights.extend(eda_ins[:5])

    if not insights and summary:
        insights = [summary]

    # ── Build recommendations ─────────────────────────────────
    recs: list[str] = []
    raw_recs = parsed.get("recommendations", [])
    if isinstance(raw_recs, list):
        for r in raw_recs:
            if isinstance(r, dict):
                title = r.get("title", "")
                action = r.get("recommended_action", "")
                benefit = r.get("expected_benefit", "")
                priority = r.get("priority", "")
                parts = [p for p in [title, action, benefit] if p]
                label = f"[{priority}] " if priority else ""
                recs.append(label + " — ".join(parts))
            elif isinstance(r, str):
                recs.append(r)

    # Priority matrix items
    pm = parsed.get("priority_matrix", {})
    if isinstance(pm, dict):
        for horizon, items in pm.items():
            for item in _ensure_list(items):
                recs.append(f"[{horizon.replace('_', ' ').title()}] {item}")

    # ── Build visualization metadata ──────────────────────────
    visualizations = _build_visualizations(context, parsed)

    # ── Metadata ──────────────────────────────────────────────
    # Coerce confidence to int — Gemini sometimes returns 85.7 (float).
    # AIResponseMetadata.confidence is Optional[int]; Pydantic v2 rejects non-integer floats.
    raw_confidence = parsed.get("confidence")
    if raw_confidence is not None:
        try:
            raw_confidence = int(raw_confidence)
        except (TypeError, ValueError):
            raw_confidence = None

    health = context.get("health_score", {})
    metadata: dict = {
        "template": template_name,
        "parse_error": parse_error,
        "insight_count": len(insights),
        "recommendation_count": len(recs),
        "business_condition": parsed.get("business_condition"),
        "risk_level": parsed.get("risk_level"),
        "confidence": raw_confidence,
        "health_score": health,
        "structured_data": parsed,  # full structured payload for frontend
    }

    return {
        "summary": str(summary),
        "insights": [str(i) for i in insights[:15]],
        "recommendations": [str(r) for r in recs[:10]],
        "visualizations": visualizations,
        "metadata": metadata,
    }


def _build_visualizations(context: dict, parsed: dict) -> list[dict]:
    """Build frontend-ready visualization metadata from context + parsed AI."""
    charts: list[dict] = []

    # ── KPI Cards ─────────────────────────────────────────────
    kpi_metrics = (context.get("kpi", {}).get("metrics") or {}).get("columns", {})
    kpi_cards = []
    for col, m in list(kpi_metrics.items())[:6]:
        kpi_cards.append({
            "chart_type": "kpi_card",
            "title": col,
            "data": {
                "value": m.get("sum"),
                "mean": m.get("mean"),
                "min": m.get("min"),
                "max": m.get("max"),
                "unit": "",
            },
        })
    if kpi_cards:
        charts.append({
            "chart_type": "kpi_cards",
            "title": "KPI Dashboard",
            "data": {"cards": kpi_cards},
        })

    # ── Numeric Ranges Bar Chart ──────────────────────────────
    ranges = context.get("numeric_ranges", {})
    if ranges:
        cols = list(ranges.keys())[:8]
        charts.append({
            "chart_type": "bar",
            "title": "Metric Averages",
            "data": {
                "x_axis": {"label": "Column", "values": cols},
                "y_axis": {"label": "Mean Value"},
                "series": [{"name": "Mean", "values": [ranges[c].get("mean", 0) for c in cols]}],
            },
        })

    # ── Top Categories Pie Charts ─────────────────────────────
    for col, vals in list(context.get("top_categories", {}).items())[:2]:
        labels = list(vals.keys())
        values = list(vals.values())
        if labels:
            charts.append({
                "chart_type": "pie",
                "title": f"Top Categories — {col}",
                "data": {"labels": labels, "values": values},
            })

    # ── Forecast Line Chart ───────────────────────────────────
    fc = context.get("forecast", {})
    if fc.get("suitable"):
        ov = fc.get("overview", {})
        charts.append({
            "chart_type": "line",
            "title": f"Trend — {fc.get('target_column', 'Target')}",
            "data": {
                "x_axis": {"label": "Date", "values": [ov.get("date_range_start"), ov.get("date_range_end")]},
                "y_axis": {"label": fc.get("target_column", "Value")},
                "trend": fc.get("trend", {}),
                "seasonality": fc.get("seasonality", {}),
                "series": [{"name": "Trend", "values": []}],
            },
        })

    # ── Data Quality Radar ────────────────────────────────────
    q = (context.get("eda", {}).get("quality") or {}).get("metrics", {})
    if q:
        charts.append({
            "chart_type": "radar",
            "title": "Data Quality Scores",
            "data": {
                "labels": list(q.keys()),
                "values": [round(v, 1) for v in q.values()],
            },
        })

    # ── Health Score Gauge ────────────────────────────────────
    health = context.get("health_score", {})
    if health:
        charts.append({
            "chart_type": "gauge",
            "title": "Business Health Score",
            "data": {
                "value": health.get("overall"),
                "rating": health.get("rating"),
                "max": 100,
                "financial_score": health.get("financial_score"),
                "operational_score": health.get("operational_score"),
                "risk_score": health.get("risk_score"),
            },
        })

    # ── Outlier Heatmap ───────────────────────────────────────
    out = context.get("eda", {}).get("outliers") or {}
    outlier_cols = out.get("column_names_with_outliers", [])
    if outlier_cols:
        col_data = out.get("columns", {})
        charts.append({
            "chart_type": "heatmap",
            "title": "Outlier Distribution",
            "data": {
                "columns": outlier_cols[:8],
                "values": [
                    {
                        "column": c,
                        "outlier_count": col_data.get(c, {}).get("outlier_count", 0),
                        "outlier_percentage": col_data.get(c, {}).get("outlier_percentage", 0),
                        "lower_bound": col_data.get(c, {}).get("lower_bound"),
                        "upper_bound": col_data.get(c, {}).get("upper_bound"),
                    }
                    for c in outlier_cols[:8]
                ],
            },
        })

    # ── Missing Values Table ──────────────────────────────────
    mv = context.get("eda", {}).get("missing_values") or {}
    mv_cols = {
        col: info
        for col, info in (mv.get("columns") or {}).items()
        if info.get("missing_count", 0) > 0
    }
    if mv_cols:
        charts.append({
            "chart_type": "table",
            "title": "Missing Value Summary",
            "data": {
                "columns": ["Column", "Missing Count", "Missing %"],
                "rows": [
                    [col, info.get("missing_count", 0), f"{info.get('missing_percentage', 0):.1f}%"]
                    for col, info in list(mv_cols.items())[:10]
                ],
            },
        })

    # ── Correlation Scatter ───────────────────────────────────
    corr = context.get("eda", {}).get("correlation") or {}
    pairs = corr.get("highly_correlated_pairs", [])
    if pairs:
        charts.append({
            "chart_type": "scatter",
            "title": "Highly Correlated Variables",
            "data": {
                "x_axis": {"label": "Column Pair"},
                "y_axis": {"label": "Correlation Coefficient"},
                "points": [
                    {
                        "label": f"{p.get('column_1')} ↔ {p.get('column_2')}",
                        "x": i,
                        "y": p.get("correlation", 0),
                    }
                    for i, p in enumerate(pairs[:10])
                ],
            },
        })

    return charts
