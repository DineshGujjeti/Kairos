"""Module 6: AI Decision Intelligence API routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.ai import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    AIHealthResponse,
    AIQuestionRequest,
    AIResponseMetadata,
    AIUsageResponse,
    AssistantChatRequest,
    AssistantChatResponse,
    ChartMetadata,
    GeminiStatusInfo,
)
from app.services.ai.assistant import answer_assistant_query
from app.services.ai.service import get_ai_service
from app.services.dataset_service import get_dataset_or_404
from app.services.kpi.loader import load_dataframe

router = APIRouter(prefix="/ai", tags=["ai"])


def _dataset_summary_text(dataset) -> str | None:
    """Short plain-text summary of a dataset's already-stored profile,
    for grounding the assistant's chat replies -- deliberately reuses
    the column_profile computed at upload time rather than re-loading
    and re-parsing the file just to answer a chat question."""
    profile = dataset.column_profile
    if not profile:
        return f"'{dataset.name}' ({dataset.row_count or '?'} rows) -- structure not yet profiled."
    domain = profile.get("domain_guess", "General Business Data")
    measures = profile.get("primary_measures") or []
    dims = profile.get("primary_dimensions") or []
    dt_col = profile.get("best_datetime_column")
    parts = [
        f"'{dataset.name}': {domain}, {profile.get('row_count', '?')} rows.",
    ]
    if measures:
        parts.append(f"Key measures: {', '.join(measures[:5])}.")
    if dims:
        parts.append(f"Key dimensions: {', '.join(dims[:5])}.")
    parts.append(f"Date column: {dt_col or 'none detected'}.")
    return " ".join(parts)


@router.post("/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(
    body: AssistantChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    In-app help assistant -- conversational support for using the
    product and interpreting results. Works with or without a dataset
    selected, and with or without Gemini configured (degrades to a
    keyword-matched FAQ answer rather than erroring). See
    app.services.ai.assistant for the fallback behaviour.
    """
    service = get_ai_service()

    dataset_summary = None
    if body.dataset_id:
        # Cross-tenant lookups return 404 exactly like every other
        # dataset-scoped endpoint -- the assistant must not be usable
        # to probe for another org's dataset ids.
        dataset = get_dataset_or_404(db, body.dataset_id, current_user.org_id)
        dataset_summary = _dataset_summary_text(dataset)

    result = answer_assistant_query(
        message=body.message,
        ai_service=service,
        history=[h.model_dump() for h in body.history],
        dataset_summary=dataset_summary,
        current_page=body.current_page,
    )
    return AssistantChatResponse(**result)



def _to_response(result: dict) -> AIAnalysisResponse:
    """Convert service dict to validated AIAnalysisResponse."""
    raw_meta = result.get("metadata", {})
    meta = AIResponseMetadata(
        template=raw_meta.get("template", "unknown"),
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
    vis = [
        ChartMetadata(
            chart_type=v.get("chart_type", "unknown"),
            title=v.get("title", ""),
            subtitle=v.get("subtitle"),
            data=v.get("data"),
        )
        for v in result.get("visualizations", [])
    ]
    return AIAnalysisResponse(
        summary=result.get("summary", ""),
        insights=result.get("insights", []),
        recommendations=result.get("recommendations", []),
        visualizations=vis,
        metadata=meta,
    )


# ── Health & Usage ────────────────────────────────────────────


@router.get("/health", response_model=AIHealthResponse)
def ai_health_check():
    """Check AI service health and SDK status."""
    service = get_ai_service()
    from app.core.config import settings

    status = None
    if service.is_available():
        status_dict = service.get_status()
        status = GeminiStatusInfo(**status_dict)

    return AIHealthResponse(
        available=service.is_available(),
        model=settings.GEMINI_MODEL if service.is_available() else None,
        configured=bool(settings.GEMINI_API_KEY),
        status_info=status,
    )


@router.get("/usage", response_model=AIUsageResponse)
def ai_usage_stats(current_user: User = Depends(get_current_user)):
    """Get AI service usage statistics."""
    service = get_ai_service()
    status = service.get_status()
    return AIUsageResponse(
        available=status.get("available", False),
        requests=status.get("request_count", 0),
        errors=status.get("error_count", 0),
        model=status.get("model"),
        sdk=status.get("sdk", "google-genai"),
    )


# ── Dataset-level AI endpoints ────────────────────────────────


@router.post("/{dataset_id}/analyze", response_model=AIAnalysisResponse)
def analyze_dataset(
    dataset_id: uuid.UUID,
    body: AIAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze dataset using AI with specified template."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    result = service.analyze_dataset(
        df,
        dataset_name=str(dataset_id),
        template_name=body.template_name,
        custom_query=body.custom_query or "",
    )
    return _to_response(result)


@router.post("/{dataset_id}/question", response_model=AIAnalysisResponse)
def ask_question(
    dataset_id: uuid.UUID,
    body: AIQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ask a specific business question about the dataset."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    result = service.answer_question(df, str(dataset_id), body.question)
    return _to_response(result)


@router.get("/{dataset_id}/summary", response_model=AIAnalysisResponse)
def executive_summary(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate executive summary of the dataset."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    result = service.generate_executive_summary(df, str(dataset_id))
    return _to_response(result)


@router.get("/{dataset_id}/risks", response_model=AIAnalysisResponse)
def identify_risks(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Identify business risks from the dataset."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    result = service.identify_risks(df, str(dataset_id))
    return _to_response(result)


@router.get("/{dataset_id}/opportunities", response_model=AIAnalysisResponse)
def identify_opportunities(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Identify growth opportunities from the dataset."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    result = service.identify_opportunities(df, str(dataset_id))
    return _to_response(result)


@router.get("/{dataset_id}/anomalies", response_model=AIAnalysisResponse)
def detect_anomalies(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detect anomalies and unusual patterns from the dataset."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    result = service.detect_anomalies(df, str(dataset_id))
    return _to_response(result)


@router.get("/{dataset_id}/recommendations", response_model=AIAnalysisResponse)
def get_recommendations(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get actionable recommendations based on dataset analysis."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    result = service.get_recommendations(df, str(dataset_id))
    return _to_response(result)
