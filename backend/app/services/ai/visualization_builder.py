"""
Visualization Builder — Module 6.

Kept for backward compatibility. The main visualization assembly
is now handled inside response_parser.py.
"""
from __future__ import annotations
from typing import List, Optional


def build_response_with_visualizations(
    summary: str,
    insights: List[str],
    recommendations: Optional[List[str]] = None,
    visualizations: Optional[list] = None,
) -> dict:
    """Build a minimal response dict (used as a fallback/compatibility shim)."""
    recs = recommendations or []
    vis = visualizations or []
    return {
        "summary": summary,
        "insights": insights,
        "recommendations": recs,
        "visualizations": vis,
        "metadata": {
            "chart_count": len(vis),
            "insight_count": len(insights),
            "recommendation_count": len(recs),
            "business_condition": None,
            "risk_level": None,
            "confidence": None,
            "health_score": {},
            "structured_data": {},
        },
    }
