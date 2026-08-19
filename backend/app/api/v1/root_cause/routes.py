"""Module 7: Root Cause Intelligence Engine — API routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.ai import (
    AIAnalysisResponse,
    AIResponseMetadata,
    ChartMetadata,
    ContributionReport,
    DiagnosticsReport,
    DriverReport,
    RootCauseReport,
    RootCauseRequest,
    WhyRequest,
)
from app.services.ai.service import get_ai_service
from app.services.kpi.loader import load_dataframe
from app.services.root_cause.root_cause_engine import run_root_cause_analysis
from app.services.root_cause.driver_detector import detect_drivers_cached
from app.services.root_cause.contribution_engine import compute_contributions
from app.services.root_cause.visualization_builder import build_root_cause_visualizations

router = APIRouter(prefix="/ai", tags=["root-cause"])


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _charts(report: dict) -> list[ChartMetadata]:
    """Convert visualization dicts to ChartMetadata objects."""
    vis = build_root_cause_visualizations(
        driver_report=report.get("driver_analysis", {}),
        contribution_report=report.get("contribution_analysis", {}),
        why_chain=report.get("why_chain", []),
        overall_confidence=report.get("overall_confidence", {}),
    )
    return [
        ChartMetadata(
            chart_type=v.get("chart_type", "unknown"),
            title=v.get("title", ""),
            subtitle=v.get("subtitle"),
            data=v.get("data"),
        )
        for v in vis
    ]


def _ai_layer(
    service,
    df,
    dataset_id: str,
    template: str,
    query: str = "",
) -> AIAnalysisResponse | None:
    """
    Optionally enrich a root cause report with a Gemini AI narrative.
    Returns None gracefully when Gemini is not configured.
    """
    if not service.is_available():
        return None
    try:
        result = service.analyze_dataset(df, dataset_id, template, query)
        raw_meta = result.get("metadata", {})
        meta = AIResponseMetadata(
            template=raw_meta.get("template", template),
            parse_error=raw_meta.get("parse_error", False),
            insight_count=raw_meta.get("insight_count", 0),
            recommendation_count=raw_meta.get("recommendation_count", 0),
            business_condition=raw_meta.get("business_condition"),
            risk_level=raw_meta.get("risk_level"),
            confidence=raw_meta.get("confidence"),
            health_score=raw_meta.get("health_score"),
            structured_data=raw_meta.get("structured_data"),
            error=raw_meta.get("error"),
            error_info=raw_meta.get("error_info"),
        )
        return AIAnalysisResponse(
            summary=result.get("summary", ""),
            insights=result.get("insights", []),
            recommendations=result.get("recommendations", []),
            visualizations=[],
            metadata=meta,
        )
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────


@router.post("/{dataset_id}/root-cause", response_model=RootCauseReport)
def root_cause(
    dataset_id: uuid.UUID,
    body: RootCauseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Full root cause analysis: WHY is the target metric behaving as observed?

    Automatically detects the target column unless *target_column* is provided.
    Returns drivers, contributions, a multi-level WHY chain, and anomaly
    explanations — all grounded in the data.
    """
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)

    report = run_root_cause_analysis(df, body.target_column, dataset_id=str(dataset_id))
    vis = _charts(report)
    ai = _ai_layer(service, df, str(dataset_id), "root_cause")

    return RootCauseReport(
        target_column=report["target_column"],
        rows_analysed=report["rows_analysed"],
        overall_confidence=report["overall_confidence"],
        driver_analysis=report.get("driver_analysis"),
        contribution_analysis=report.get("contribution_analysis"),
        why_chain=report.get("why_chain", []),
        anomaly_explanations=report.get("anomaly_explanations", []),
        data_quality=report["data_quality"],
        summary=report["summary"],
        visualizations=vis,
        ai_insights=ai,
    )


@router.get("/{dataset_id}/drivers", response_model=DriverReport)
def get_drivers(
    dataset_id: uuid.UUID,
    target_column: str | None = None,
    top_n: int = 8,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Identify which variables most strongly drive a target metric.

    Uses correlation, mutual information, and Random Forest importance.
    Returns ranked drivers with confidence scores and directions.
    """
    df = load_dataframe(dataset_id, db, current_user)

    # Auto-select target if not provided
    if not target_column:
        numeric_cols = list(df.select_dtypes(include="number").columns)
        if not numeric_cols:
            return DriverReport(
                target_column="",
                error="No numeric columns found",
                top_drivers=[],
                positive_drivers=[],
                negative_drivers=[],
            )
        target_column = numeric_cols[0]

    report = detect_drivers_cached(str(dataset_id), df, target_column, top_n=min(top_n, 20))
    return DriverReport(**report)


@router.get("/{dataset_id}/contributions", response_model=ContributionReport)
def get_contributions(
    dataset_id: uuid.UUID,
    target_column: str | None = None,
    top_n: int = 8,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compute how much each variable contributed to the observed target metric value.

    Returns additive contribution percentages, directions, and
    waterfall-ready data for the frontend.
    """
    df = load_dataframe(dataset_id, db, current_user)

    if not target_column:
        numeric_cols = list(df.select_dtypes(include="number").columns)
        if not numeric_cols:
            return ContributionReport(
                target_column="",
                error="No numeric columns found",
                contributions=[],
            )
        target_column = numeric_cols[0]

    report = compute_contributions(df, target_column, top_n=min(top_n, 20))
    return ContributionReport(**report)


@router.get("/{dataset_id}/diagnostics", response_model=DiagnosticsReport)
def get_diagnostics(
    dataset_id: uuid.UUID,
    target_column: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Comprehensive business diagnostic: what is working, what is broken,
    and what needs immediate attention.

    Combines full root cause analysis with an AI-generated narrative
    (when Gemini is configured).
    """
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)

    report = run_root_cause_analysis(df, target_column, dataset_id=str(dataset_id))
    vis = _charts(report)
    ai = _ai_layer(service, df, str(dataset_id), "business_diagnostics")

    rc_report = RootCauseReport(
        target_column=report["target_column"],
        rows_analysed=report["rows_analysed"],
        overall_confidence=report["overall_confidence"],
        driver_analysis=report.get("driver_analysis"),
        contribution_analysis=report.get("contribution_analysis"),
        why_chain=report.get("why_chain", []),
        anomaly_explanations=report.get("anomaly_explanations", []),
        data_quality=report["data_quality"],
        summary=report["summary"],
        visualizations=vis,
        ai_insights=None,
    )

    return DiagnosticsReport(root_cause=rc_report, ai_analysis=ai)


@router.post("/{dataset_id}/why", response_model=AIAnalysisResponse)
def ask_why(
    dataset_id: uuid.UUID,
    body: WhyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Answer a specific WHY question about the dataset in executive language.

    Combines statistical root cause findings with Gemini AI to produce
    a board-level causal explanation grounded in the data.

    Example body: {"question": "Why did revenue increase last month?"}
    """
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)

    # Run statistical root cause to enrich the AI context
    report = run_root_cause_analysis(df, body.target_column, dataset_id=str(dataset_id))

    # Delegate to AI service with the 'executive_why' template
    result = service.analyze_dataset(
        df,
        dataset_name=str(dataset_id),
        template_name="executive_why",
        custom_query=body.question,
    )

    raw_meta = result.get("metadata", {})

    # Inject root cause stats into structured_data so frontend can use them
    structured = raw_meta.get("structured_data") or {}
    structured["root_cause_stats"] = {
        "target_column": report["target_column"],
        "why_chain": report.get("why_chain", []),
        "summary": report["summary"],
        "top_drivers": (report.get("driver_analysis") or {}).get("top_drivers", [])[:5],
    }

    meta = AIResponseMetadata(
        template=raw_meta.get("template", "executive_why"),
        parse_error=raw_meta.get("parse_error", False),
        insight_count=raw_meta.get("insight_count", 0),
        recommendation_count=raw_meta.get("recommendation_count", 0),
        business_condition=raw_meta.get("business_condition"),
        risk_level=raw_meta.get("risk_level"),
        confidence=raw_meta.get("confidence"),
        health_score=raw_meta.get("health_score"),
        structured_data=structured,
        error=raw_meta.get("error"),
        error_info=raw_meta.get("error_info"),
    )

    return AIAnalysisResponse(
        summary=result.get("summary", ""),
        insights=result.get("insights", []),
        recommendations=result.get("recommendations", []),
        visualizations=[],
        metadata=meta,
    )
