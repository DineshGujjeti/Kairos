"""Module 9 — Decision Advisor schemas."""
from __future__ import annotations

import uuid
from typing import Any, List, Optional
from pydantic import BaseModel


# ── Requests ──────────────────────────────────────────────────────────────────


class DecisionAnalyzeRequest(BaseModel):
    dataset_id: uuid.UUID
    save_session: bool = True


class DecisionRecommendRequest(BaseModel):
    dataset_id: uuid.UUID
    metric_focus: Optional[str] = None
    save_session: bool = True


class DecisionRootCauseRequest(BaseModel):
    dataset_id: uuid.UUID
    problem_statement: str = ""
    save_session: bool = True


class DecisionPrescriptiveRequest(BaseModel):
    dataset_id: uuid.UUID
    metric_focus: str = ""
    save_session: bool = True


class DecisionExecutiveRequest(BaseModel):
    dataset_id: uuid.UUID


class BusinessRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    metric_name: str
    operator: str
    threshold: float
    threshold_unit: Optional[str] = None
    recommendation_title: str
    recommendation_description: str
    category: str = "executive"
    priority: str = "medium"


# ── Recommendation schema ─────────────────────────────────────────────────────


class RecommendationSchema(BaseModel):
    title: str
    description: str
    category: str
    priority: str
    priority_score: float = 50.0
    impact_score: float = 50.0
    confidence_score: float = 50.0
    urgency_score: float = 50.0
    effort_score: float = 50.0
    roi_score: float = 50.0
    overall_score: float = 50.0
    reason: Optional[str] = None
    business_impact: Optional[str] = None
    expected_gain: Optional[str] = None
    risk: Optional[str] = None
    implementation_difficulty: Optional[str] = None
    timeline: Optional[str] = None
    source: Optional[str] = None


class ChartItem(BaseModel):
    chart_type: str
    title: str
    subtitle: Optional[str] = None
    data: Optional[dict] = None


# ── Response schemas ──────────────────────────────────────────────────────────


class DecisionAnalysisResponse(BaseModel):
    dataset_name: str
    recommendation_count: int
    recommendations: List[RecommendationSchema]
    executive_summary: Optional[str] = None
    executive_conclusion: Optional[str] = None
    ai_response: Optional[dict] = None
    visualizations: List[ChartItem] = []
    sources: dict
    session_id: Optional[uuid.UUID] = None


class ExecutiveAdvisoryResponse(BaseModel):
    ai_advisory: dict
    context_snapshot: Optional[dict] = None


class PrescriptiveResponse(BaseModel):
    metric_focus: str
    prescribed_actions: List[RecommendationSchema]
    ai_analysis: Optional[dict] = None
    visualizations: List[ChartItem] = []


class RootCauseDecisionResponse(BaseModel):
    problem_statement: str
    diagnosed_causes: List[dict] = []
    decision_recommendations: List[RecommendationSchema] = []
    prevention_measures: List[str] = []
    ai_analysis: Optional[dict] = None
    visualizations: List[ChartItem] = []


class SessionHistoryItem(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    session_type: str
    summary: Optional[str] = None
    created_at: Any

    class Config:
        from_attributes = True


class BusinessRuleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    metric_name: str
    operator: str
    threshold: float
    threshold_unit: Optional[str] = None
    recommendation_title: str
    category: str
    priority: str
    is_active: bool

    class Config:
        from_attributes = True


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    title_template: str
    description_template: str
    default_priority: str

    class Config:
        from_attributes = True
