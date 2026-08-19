"""
Recommendation Scoring Engine — Module 9.

Computes the 7 scores for every recommendation:
  priority_score, impact_score, confidence_score, urgency_score,
  effort_score, roi_score, overall_score.

All scores are 0-100. overall_score is a weighted composite.
"""
from __future__ import annotations

_PRIORITY_WEIGHTS = {"high": 85.0, "medium": 55.0, "low": 30.0}
_DIFFICULTY_EFFORT = {"low": 80.0, "medium": 50.0, "high": 20.0}
_TIMELINE_URGENCY = {
    "immediate": 95.0,
    "30 days": 80.0,
    "90 days": 60.0,
    "6 months": 40.0,
    "12 months": 25.0,
}

# Overall score weights
_WEIGHTS = {
    "priority_score": 0.20,
    "impact_score": 0.25,
    "confidence_score": 0.15,
    "urgency_score": 0.15,
    "effort_score": 0.10,   # inversely weighted below
    "roi_score": 0.15,
}


def score_recommendation(rec: dict) -> dict:
    """
    Accept a recommendation dict (as produced by the AI or rule engine)
    and return it enriched with all 7 numeric scores.

    Input keys used (all optional with sensible defaults):
      priority, implementation_difficulty, timeline,
      impact_score (raw AI), confidence (raw AI int), roi_score (raw AI)
    """
    priority = str(rec.get("priority", "medium")).lower()
    difficulty = str(rec.get("implementation_difficulty", "medium")).lower()
    timeline = str(rec.get("timeline", "90 days")).lower()

    priority_score = _PRIORITY_WEIGHTS.get(priority, 55.0)

    # Impact: use AI-provided value or derive from priority
    raw_impact = rec.get("impact_score")
    impact_score = float(raw_impact) if raw_impact is not None else _PRIORITY_WEIGHTS.get(priority, 55.0)
    impact_score = max(0.0, min(100.0, impact_score))

    # Confidence: AI provides an int 0-100
    raw_conf = rec.get("confidence_score") or rec.get("confidence")
    confidence_score = float(raw_conf) if raw_conf is not None else 60.0
    confidence_score = max(0.0, min(100.0, confidence_score))

    urgency_score = _TIMELINE_URGENCY.get(timeline, 60.0)

    # Effort score: inverted difficulty (low effort = high score, easy to implement)
    effort_score = _DIFFICULTY_EFFORT.get(difficulty, 50.0)

    # ROI: AI-provided or estimated from impact / effort
    raw_roi = rec.get("roi_score")
    roi_score = float(raw_roi) if raw_roi is not None else (impact_score * 0.7 + effort_score * 0.3)
    roi_score = max(0.0, min(100.0, roi_score))

    # Weighted overall (effort contributes negatively via inversion)
    overall_score = (
        priority_score * _WEIGHTS["priority_score"]
        + impact_score * _WEIGHTS["impact_score"]
        + confidence_score * _WEIGHTS["confidence_score"]
        + urgency_score * _WEIGHTS["urgency_score"]
        + effort_score * _WEIGHTS["effort_score"]
        + roi_score * _WEIGHTS["roi_score"]
    )
    # Small difficulty penalty: high effort drags overall down slightly
    if difficulty == "high":
        overall_score *= 0.92

    overall_score = round(max(0.0, min(100.0, overall_score)), 1)

    return {
        **rec,
        "priority_score": round(priority_score, 1),
        "impact_score": round(impact_score, 1),
        "confidence_score": round(confidence_score, 1),
        "urgency_score": round(urgency_score, 1),
        "effort_score": round(effort_score, 1),
        "roi_score": round(roi_score, 1),
        "overall_score": overall_score,
    }


def score_and_rank(recommendations: list[dict]) -> list[dict]:
    """
    Score every recommendation and return sorted descending by overall_score.
    """
    scored = [score_recommendation(r) for r in recommendations]
    scored.sort(key=lambda r: -(r.get("overall_score") or 0))
    return scored
