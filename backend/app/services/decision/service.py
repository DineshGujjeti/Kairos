"""
Decision Service — Module 9 orchestrator.

Combines context building, rule evaluation, AI prompting, scoring, and
persistence into a single service layer consumed by all API routes.
"""
from __future__ import annotations

import uuid
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models.decision import (
    BusinessRule,
    DecisionSession,
    Recommendation,
    RecommendationTemplate,
)
from app.services.ai.context_builder import build_complete_context, format_context_for_prompt
from app.services.ai.prompt_engine import get_template
from app.services.ai.response_parser import _extract_json
from app.services.decision.rule_engine import evaluate_rules
from app.services.decision.scoring_engine import score_and_rank
from app.services.decision.visualization_builder import build_all_decision_visualizations

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# AI helpers
# ─────────────────────────────────────────────────────────────────────────────


def _call_ai(service, template_name: str, context_text: str, query: str = "") -> dict | None:
    """Call Gemini with a Module 9 prompt; parse JSON response; return dict or None."""
    if not service.is_available():
        return None
    try:
        tmpl = get_template(template_name)
        sys_inst, user_prompt = tmpl.format(context_text, query)
        response_text, error_info = service.gemini.generate_content(
            prompt=user_prompt,
            system_instruction=sys_inst,
            temperature=0.4,
            max_tokens=3000,
        )
        if error_info or not response_text:
            return None
        parsed = _extract_json(response_text)
        return parsed if isinstance(parsed, dict) else None
    except Exception as exc:
        logger.warning("decision_ai_failed", template=template_name, error=str(exc))
        return None


def _extract_recs_from_ai(ai_result: dict | None) -> list[dict]:
    """Pull the recommendations list from an AI response dict."""
    if not ai_result:
        return []
    recs = ai_result.get("recommendations") or ai_result.get("prescribed_actions") or ai_result.get("decision_recommendations") or []
    if not isinstance(recs, list):
        return []
    return recs


# ─────────────────────────────────────────────────────────────────────────────
# Context builder
# ─────────────────────────────────────────────────────────────────────────────


def build_decision_context(
    df: pd.DataFrame,
    dataset_name: str,
    extra_info: dict | None = None,
) -> tuple[str, dict]:
    """Return (context_text, context_dict) for AI prompts."""
    ctx = build_complete_context(df, dataset_name)
    if extra_info:
        ctx["extra"] = extra_info
    return format_context_for_prompt(ctx), ctx


# ─────────────────────────────────────────────────────────────────────────────
# Core analysis functions (stateless)
# ─────────────────────────────────────────────────────────────────────────────


def run_analysis(
    df: pd.DataFrame,
    dataset_name: str,
    ai_service,
    org_rules: list[dict] | None = None,
    quality_score: float = 75.0,
) -> dict:
    """
    Full decision analysis pipeline:
    1. Build rich context.
    2. Evaluate business rules.
    3. Call AI for recommendations.
    4. Merge and score everything.
    5. Return structured response with visualizations.
    """
    context_text, context_dict = build_decision_context(df, dataset_name)

    # Business rule recommendations
    rule_recs = evaluate_rules(df, org_rules, quality_score)

    # AI recommendations
    ai_result = _call_ai(ai_service, "decision_recommendations", context_text)
    ai_recs = _extract_recs_from_ai(ai_result)

    # Merge — rule recs first (grounded), then AI recs
    all_recs_raw = rule_recs + ai_recs

    # Score and rank
    ranked = score_and_rank(all_recs_raw)

    # Build visualizations
    charts = build_all_decision_visualizations(ranked)

    return {
        "dataset_name": dataset_name,
        "recommendation_count": len(ranked),
        "recommendations": ranked,
        "executive_summary": (ai_result or {}).get("executive_summary", ""),
        "executive_conclusion": (ai_result or {}).get("executive_conclusion", ""),
        "ai_response": ai_result,
        "context_snapshot": context_dict,
        "visualizations": charts,
        "sources": {
            "rule_engine": len(rule_recs),
            "ai_generated": len(ai_recs),
        },
    }


def run_executive_advisor(
    df: pd.DataFrame,
    dataset_name: str,
    ai_service,
) -> dict:
    """Generate board-level executive advisory with 30/90-day plans."""
    context_text, context_dict = build_decision_context(df, dataset_name)
    ai_result = _call_ai(ai_service, "executive_advisor", context_text)

    if not ai_result:
        ai_result = {
            "executive_summary": "AI advisor unavailable. Review analytics data directly.",
            "immediate_actions": [],
            "plan_30_days": [],
            "plan_90_days": [],
            "long_term_strategy": [],
            "risks": [],
            "expected_roi": "N/A",
            "executive_conclusion": "Configure GEMINI_API_KEY to enable AI advisories.",
            "confidence": 0,
        }

    return {"ai_advisory": ai_result, "context_snapshot": context_dict}


def run_prescriptive_analysis(
    df: pd.DataFrame,
    dataset_name: str,
    ai_service,
    metric_focus: str = "",
) -> dict:
    """Prescriptive analytics: root cause → specific action plan."""
    context_text, context_dict = build_decision_context(df, dataset_name)
    ai_result = _call_ai(ai_service, "prescriptive_analytics", context_text, metric_focus)

    recs_raw = _extract_recs_from_ai(ai_result)
    ranked = score_and_rank(recs_raw)
    charts = build_all_decision_visualizations(ranked)

    return {
        "metric_focus": metric_focus,
        "prescribed_actions": ranked,
        "ai_analysis": ai_result,
        "visualizations": charts,
    }


def run_root_cause_decision(
    df: pd.DataFrame,
    dataset_name: str,
    ai_service,
    problem_statement: str = "",
) -> dict:
    """Root-cause-based decision recommendations."""
    context_text, context_dict = build_decision_context(df, dataset_name)
    ai_result = _call_ai(ai_service, "decision_root_cause", context_text, problem_statement)

    recs_raw = (ai_result or {}).get("decision_recommendations", [])
    if isinstance(recs_raw, list):
        ranked = score_and_rank(recs_raw)
    else:
        ranked = []

    charts = build_all_decision_visualizations(ranked)

    return {
        "problem_statement": problem_statement,
        "diagnosed_causes": (ai_result or {}).get("diagnosed_causes", []),
        "decision_recommendations": ranked,
        "prevention_measures": (ai_result or {}).get("prevention_measures", []),
        "ai_analysis": ai_result,
        "visualizations": charts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Persistence helpers
# ─────────────────────────────────────────────────────────────────────────────


def save_session(
    db: Session,
    dataset_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    session_type: str,
    analysis_result: dict,
) -> DecisionSession:
    """Persist a DecisionSession and its Recommendation rows."""
    session = DecisionSession(
        id=uuid.uuid4(),
        dataset_id=dataset_id,
        org_id=org_id,
        user_id=user_id,
        session_type=session_type,
        summary=analysis_result.get("executive_summary", ""),
        context_snapshot=analysis_result.get("context_snapshot"),
        ai_response=analysis_result.get("ai_response"),
    )
    db.add(session)
    db.flush()

    for rec_dict in analysis_result.get("recommendations", []):
        rec = Recommendation(
            id=uuid.uuid4(),
            session_id=session.id,
            org_id=org_id,
            title=rec_dict.get("title", "")[:255],
            description=rec_dict.get("description", ""),
            category=rec_dict.get("category", "executive"),
            priority=rec_dict.get("priority", "medium"),
            priority_score=rec_dict.get("priority_score", 50.0),
            impact_score=rec_dict.get("impact_score", 50.0),
            confidence_score=rec_dict.get("confidence_score", 50.0),
            urgency_score=rec_dict.get("urgency_score", 50.0),
            effort_score=rec_dict.get("effort_score", 50.0),
            roi_score=rec_dict.get("roi_score", 50.0),
            overall_score=rec_dict.get("overall_score", 50.0),
            reason=rec_dict.get("reason"),
            business_impact=rec_dict.get("business_impact"),
            expected_gain=rec_dict.get("expected_gain"),
            risk=rec_dict.get("risk"),
            implementation_difficulty=rec_dict.get("implementation_difficulty"),
            timeline=rec_dict.get("timeline"),
        )
        db.add(rec)

    db.commit()
    db.refresh(session)
    return session


def get_session_history(
    db: Session,
    org_id: uuid.UUID,
    dataset_id: uuid.UUID | None = None,
    limit: int = 20,
) -> list[DecisionSession]:
    """Retrieve recent decision sessions for an organisation."""
    q = db.query(DecisionSession).filter(DecisionSession.org_id == org_id)
    if dataset_id:
        q = q.filter(DecisionSession.dataset_id == dataset_id)
    return q.order_by(DecisionSession.created_at.desc()).limit(limit).all()


def get_org_rules(db: Session, org_id: uuid.UUID) -> list[dict]:
    """Load active business rules for an organisation as plain dicts."""
    rules = (
        db.query(BusinessRule)
        .filter(BusinessRule.org_id == org_id, BusinessRule.is_active.is_(True))
        .all()
    )
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "metric_name": r.metric_name,
            "operator": r.operator,
            "threshold": r.threshold,
            "threshold_unit": r.threshold_unit or "",
            "recommendation_title": r.recommendation_title,
            "recommendation_description": r.recommendation_description,
            "category": r.category,
            "priority": r.priority,
        }
        for r in rules
    ]


def get_templates(db: Session) -> list[RecommendationTemplate]:
    """Return all recommendation templates."""
    return db.query(RecommendationTemplate).order_by(RecommendationTemplate.name).all()
