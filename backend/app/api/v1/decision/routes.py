"""Module 9: Decision Advisor & Prescriptive Intelligence Engine — API routes."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.decision import (
    BusinessRuleCreate,
    BusinessRuleResponse,
    DecisionAnalysisResponse,
    DecisionAnalyzeRequest,
    DecisionExecutiveRequest,
    DecisionPrescriptiveRequest,
    DecisionRecommendRequest,
    DecisionRootCauseRequest,
    ExecutiveAdvisoryResponse,
    PrescriptiveResponse,
    RecommendationSchema,
    RootCauseDecisionResponse,
    SessionHistoryItem,
    TemplateResponse,
    ChartItem,
)
from app.services.ai.service import get_ai_service
from app.services.decision.service import (
    build_decision_context,
    get_org_rules,
    get_session_history,
    get_templates,
    run_analysis,
    run_executive_advisor,
    run_prescriptive_analysis,
    run_root_cause_decision,
    save_session,
)
from app.services.kpi.loader import load_dataframe
from app.db.models.decision import BusinessRule

router = APIRouter(prefix="/decision", tags=["decision"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _to_chart(v: dict) -> ChartItem:
    return ChartItem(
        chart_type=v.get("chart_type", "bar"),
        title=v.get("title", ""),
        subtitle=v.get("subtitle"),
        data=v.get("data"),
    )


def _to_rec(r: dict) -> RecommendationSchema:
    return RecommendationSchema(
        title=r.get("title", "")[:255],
        description=r.get("description", ""),
        category=r.get("category", "executive"),
        priority=r.get("priority", "medium"),
        priority_score=r.get("priority_score", 50.0),
        impact_score=r.get("impact_score", 50.0),
        confidence_score=r.get("confidence_score", 50.0),
        urgency_score=r.get("urgency_score", 50.0),
        effort_score=r.get("effort_score", 50.0),
        roi_score=r.get("roi_score", 50.0),
        overall_score=r.get("overall_score", 50.0),
        reason=r.get("reason"),
        business_impact=r.get("business_impact"),
        expected_gain=r.get("expected_gain"),
        risk=r.get("risk"),
        implementation_difficulty=r.get("implementation_difficulty"),
        timeline=r.get("timeline"),
        source=r.get("source"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/analyze", response_model=DecisionAnalysisResponse)
def analyze_and_recommend(
    body: DecisionAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Full decision analysis: business rules + AI recommendations, scored and ranked.

    Persists a DecisionSession when save_session=True.
    """
    ai_service = get_ai_service()
    df = load_dataframe(body.dataset_id, db, current_user)
    org_rules = get_org_rules(db, current_user.org_id)

    result = run_analysis(df, str(body.dataset_id), ai_service, org_rules)

    session_id: Optional[uuid.UUID] = None
    if body.save_session:
        try:
            session = save_session(
                db, body.dataset_id, current_user.org_id,
                current_user.id, "analysis", result,
            )
            session_id = session.id
        except Exception:
            pass

    return DecisionAnalysisResponse(
        dataset_name=result["dataset_name"],
        recommendation_count=result["recommendation_count"],
        recommendations=[_to_rec(r) for r in result["recommendations"]],
        executive_summary=result.get("executive_summary"),
        executive_conclusion=result.get("executive_conclusion"),
        ai_response=result.get("ai_response"),
        visualizations=[_to_chart(v) for v in result.get("visualizations", [])],
        sources=result["sources"],
        session_id=session_id,
    )


@router.post("/recommend", response_model=DecisionAnalysisResponse)
def get_recommendations(
    body: DecisionRecommendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate scored, ranked business recommendations for a dataset.
    Optional metric_focus to direct AI attention to a specific KPI.
    """
    ai_service = get_ai_service()
    df = load_dataframe(body.dataset_id, db, current_user)
    org_rules = get_org_rules(db, current_user.org_id)

    result = run_analysis(df, str(body.dataset_id), ai_service, org_rules)

    session_id = None
    if body.save_session:
        try:
            session = save_session(
                db, body.dataset_id, current_user.org_id,
                current_user.id, "recommendation", result,
            )
            session_id = session.id
        except Exception:
            pass

    return DecisionAnalysisResponse(
        dataset_name=result["dataset_name"],
        recommendation_count=result["recommendation_count"],
        recommendations=[_to_rec(r) for r in result["recommendations"]],
        executive_summary=result.get("executive_summary"),
        executive_conclusion=result.get("executive_conclusion"),
        ai_response=result.get("ai_response"),
        visualizations=[_to_chart(v) for v in result.get("visualizations", [])],
        sources=result["sources"],
        session_id=session_id,
    )


@router.post("/root-cause", response_model=RootCauseDecisionResponse)
def root_cause_decisions(
    body: DecisionRootCauseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Root-cause-based decision recommendations.
    Diagnoses why a metric declined and prescribes specific countermeasures.
    """
    ai_service = get_ai_service()
    df = load_dataframe(body.dataset_id, db, current_user)

    result = run_root_cause_decision(
        df, str(body.dataset_id), ai_service, body.problem_statement
    )

    if body.save_session:
        try:
            rec_dicts = result.get("decision_recommendations", [])
            save_result = {
                "recommendations": rec_dicts,
                "executive_summary": body.problem_statement,
                "context_snapshot": {},
                "ai_response": result.get("ai_analysis"),
            }
            save_session(
                db, body.dataset_id, current_user.org_id,
                current_user.id, "root_cause", save_result,
            )
        except Exception:
            pass

    return RootCauseDecisionResponse(
        problem_statement=result["problem_statement"],
        diagnosed_causes=result.get("diagnosed_causes", []),
        decision_recommendations=[_to_rec(r) for r in result.get("decision_recommendations", [])],
        prevention_measures=result.get("prevention_measures", []),
        ai_analysis=result.get("ai_analysis"),
        visualizations=[_to_chart(v) for v in result.get("visualizations", [])],
    )


@router.post("/prescriptive", response_model=PrescriptiveResponse)
def prescriptive_analytics(
    body: DecisionPrescriptiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Prescriptive analytics: given root causes, prescribe a specific action plan.
    """
    ai_service = get_ai_service()
    df = load_dataframe(body.dataset_id, db, current_user)

    result = run_prescriptive_analysis(
        df, str(body.dataset_id), ai_service, body.metric_focus
    )

    if body.save_session:
        try:
            save_session(
                db, body.dataset_id, current_user.org_id,
                current_user.id, "prescriptive",
                {"recommendations": result["prescribed_actions"],
                 "executive_summary": body.metric_focus,
                 "context_snapshot": {}, "ai_response": result.get("ai_analysis")},
            )
        except Exception:
            pass

    return PrescriptiveResponse(
        metric_focus=result["metric_focus"],
        prescribed_actions=[_to_rec(r) for r in result["prescribed_actions"]],
        ai_analysis=result.get("ai_analysis"),
        visualizations=[_to_chart(v) for v in result.get("visualizations", [])],
    )


@router.post("/executive", response_model=ExecutiveAdvisoryResponse)
def executive_advisor(
    body: DecisionExecutiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Board-level executive advisory with immediate actions and 30/90-day plans.
    """
    ai_service = get_ai_service()
    df = load_dataframe(body.dataset_id, db, current_user)

    result = run_executive_advisor(df, str(body.dataset_id), ai_service)
    return ExecutiveAdvisoryResponse(**result)


@router.get("/history", response_model=list[SessionHistoryItem])
def decision_history(
    dataset_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve recent decision sessions for the current organisation."""
    sessions = get_session_history(db, current_user.org_id, dataset_id, limit)
    return [SessionHistoryItem.model_validate(s) for s in sessions]


@router.get("/templates", response_model=list[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all recommendation templates."""
    templates = get_templates(db)
    return [TemplateResponse.model_validate(t) for t in templates]


@router.get("/rules", response_model=list[BusinessRuleResponse])
def list_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active business rules for the current organisation."""
    rules = (
        db.query(BusinessRule)
        .filter(BusinessRule.org_id == current_user.org_id)
        .all()
    )
    return [BusinessRuleResponse.model_validate(r) for r in rules]


@router.post("/rules", response_model=BusinessRuleResponse)
def create_rule(
    body: BusinessRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new business rule for the current organisation."""
    rule = BusinessRule(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        **body.model_dump(),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return BusinessRuleResponse.model_validate(rule)
