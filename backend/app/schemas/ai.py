"""AI request and response schemas — Modules 6 & 7."""
from typing import Any, Literal, Optional, List
import uuid
from pydantic import BaseModel


# ── Requests ──────────────────────────────────────────────────

_VALID_TEMPLATES = Literal[
    # Module 6
    "executive_summary",
    "business_insights",
    "root_cause_analysis",
    "recommendations",
    "risk_analysis",
    "opportunity_analysis",
    "question_answering",
    "anomaly_detection",
    # Module 7
    "root_cause",
    "driver_analysis",
    "contribution_analysis",
    "anomaly_explanation",
    "executive_why",
    "business_diagnostics",
    # Module 8
    "simulation_insight",
    "sensitivity_insight",
    "scenario_comparison_insight",
]


class AIAnalysisRequest(BaseModel):
    template_name: _VALID_TEMPLATES = "business_insights"
    custom_query: Optional[str] = None


class AIQuestionRequest(BaseModel):
    question: str


# ── Module 7 specific requests ────────────────────────────────


class RootCauseRequest(BaseModel):
    target_column: Optional[str] = None  # auto-detected if None


class WhyRequest(BaseModel):
    question: str
    target_column: Optional[str] = None


# ── Charts / Visualization ────────────────────────────────────


class ChartMetadata(BaseModel):
    chart_type: str
    title: str
    subtitle: Optional[str] = None
    data: Optional[dict] = None


# ── Business Health Score ─────────────────────────────────────


class HealthScoreComponents(BaseModel):
    data_quality_base: float
    missing_penalty: float
    duplicate_penalty: float
    trend_adjustment: float
    outlier_penalty: float


class BusinessHealthScore(BaseModel):
    overall: float
    rating: str
    financial_score: float
    operational_score: float
    risk_score: float
    components: Optional[HealthScoreComponents] = None


# ── Analysis Response ─────────────────────────────────────────


class AIResponseMetadata(BaseModel):
    template: str
    parse_error: bool = False
    insight_count: int = 0
    recommendation_count: int = 0
    business_condition: Optional[str] = None
    risk_level: Optional[str] = None
    confidence: Optional[int] = None
    health_score: Optional[dict] = None
    structured_data: Optional[dict] = None   # full structured JSON from Gemini
    error: Optional[str] = None
    error_info: Optional[dict] = None


class AIAnalysisResponse(BaseModel):
    summary: str
    insights: List[str]
    recommendations: List[str] = []
    visualizations: List[ChartMetadata] = []
    metadata: AIResponseMetadata


# ── Module 7 response schemas ─────────────────────────────────


class DriverItem(BaseModel):
    column: str
    importance: float
    pearson_correlation: float
    mutual_information: float
    rf_importance: Optional[float] = None
    direction: str
    confidence: str
    confidence_score: Optional[float] = None
    contribution_pct: Optional[float] = None


class DriverReport(BaseModel):
    target_column: str
    rows_analysed: Optional[int] = None
    methods_used: List[str] = []
    total_features_evaluated: Optional[int] = None
    top_drivers: List[DriverItem] = []
    positive_drivers: List[DriverItem] = []
    negative_drivers: List[DriverItem] = []
    error: Optional[str] = None


class ContributionItem(BaseModel):
    column: str
    contribution_pct: float
    raw_contribution: float
    column_mean: float
    correlation_with_target: float
    direction: str
    label: str


class WaterfallItem(BaseModel):
    label: str
    value: float
    running_total: float
    type: str


class ContributionReport(BaseModel):
    target_column: str
    target_mean: Optional[float] = None
    rows_analysed: Optional[int] = None
    total_contributors: Optional[int] = None
    contributions: List[ContributionItem] = []
    positive_contributors: List[ContributionItem] = []
    negative_contributors: List[ContributionItem] = []
    waterfall_data: List[WaterfallItem] = []
    error: Optional[str] = None


class WhyChainStep(BaseModel):
    level: int
    question: str
    answer: str
    driver: Optional[str] = None
    contribution_pct: Optional[float] = None
    confidence: Optional[str] = None


class AnomalyExplanation(BaseModel):
    column: str
    outlier_count: int
    outlier_pct: float
    bounds: dict
    possible_causes: List[str]
    correlated_variables: List[str]
    business_impact: str
    affected_kpis: List[str]
    confidence: str


class ConfidenceScore(BaseModel):
    score: float
    band: str


class RootCauseSummary(BaseModel):
    target: str
    top_positive_driver: Optional[str] = None
    top_negative_driver: Optional[str] = None
    n_drivers_found: int
    n_anomaly_columns: int
    confidence: str


class RootCauseReport(BaseModel):
    target_column: str
    rows_analysed: int
    overall_confidence: ConfidenceScore
    driver_analysis: Optional[dict] = None      # full DriverReport as dict
    contribution_analysis: Optional[dict] = None # full ContributionReport as dict
    why_chain: List[WhyChainStep] = []
    anomaly_explanations: List[AnomalyExplanation] = []
    data_quality: dict
    summary: RootCauseSummary
    visualizations: List[ChartMetadata] = []
    ai_insights: Optional[AIAnalysisResponse] = None  # optional Gemini layer


class DiagnosticsReport(BaseModel):
    """Combined diagnostics: statistical root cause + AI narrative."""
    root_cause: RootCauseReport
    ai_analysis: Optional[AIAnalysisResponse] = None


# ── Health / Usage ────────────────────────────────────────────


class GeminiStatusInfo(BaseModel):
    available: bool
    configured: bool
    model: str
    sdk: str
    request_count: int
    error_count: int
    max_retries: int
    timeout_seconds: int


class AIHealthResponse(BaseModel):
    available: bool
    model: Optional[str] = None
    configured: bool
    sdk_version: str = "google-genai"
    status_info: Optional[GeminiStatusInfo] = None


class AIUsageResponse(BaseModel):
    available: bool
    requests: int
    errors: int
    model: Optional[str] = None
    sdk: str = "google-genai"


# ── Module 8 Schemas ──────────────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    """Body for POST /{dataset_id}/simulate."""
    target_column: Optional[str] = None
    feature_columns: Optional[List[str]] = None


class SingleSimulationRequest(BaseModel):
    variable: str
    new_value: float
    target_column: Optional[str] = None
    feature_columns: Optional[List[str]] = None
    base_overrides: Optional[dict] = None


class MultiSimulationRequest(BaseModel):
    scenario: dict  # {column: new_value}
    target_column: Optional[str] = None
    feature_columns: Optional[List[str]] = None


class ScenarioItem(BaseModel):
    name: str
    variables: dict  # {column: new_value}


class ScenarioComparisonRequest(BaseModel):
    scenarios: List[ScenarioItem]
    target_column: Optional[str] = None
    feature_columns: Optional[List[str]] = None


class SensitivityRequest(BaseModel):
    target_column: Optional[str] = None
    feature_columns: Optional[List[str]] = None
    columns: Optional[List[str]] = None  # subset of features to analyse
    n_steps: int = 20
    top_n: int = 10


class ModelMetricsSchema(BaseModel):
    model_config = {"protected_namespaces": ()}
    r2: float
    rmse: float
    mae: float
    mape: Optional[float] = None


class ModelComparisonSchema(BaseModel):
    model_config = {"protected_namespaces": ()}
    selected_model: str
    linear_regression: ModelMetricsSchema
    random_forest: Optional[ModelMetricsSchema] = None
    rows_trained: int
    train_r2: float
    test_r2: float


class PredictionInterval(BaseModel):
    lower: float
    upper: float
    confidence: str = "95%"


class ConfidenceScore(BaseModel):
    level: str
    score: float


class VariableImpact(BaseModel):
    variable: str
    original_value: float
    new_value: float
    change_pct: float
    isolated_delta: float
    direction: str
    explanation: Optional[str] = None


class SingleSimulationResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    simulation_type: str
    variable: str
    original_value: float
    new_value: float
    change_pct: float
    baseline_prediction: float
    scenario_prediction: float
    delta: float
    delta_pct: float
    prediction_interval: PredictionInterval
    confidence: ConfidenceScore
    model_used: str
    model_r2: float
    recommendations: List[str] = []
    visualizations: List[ChartMetadata] = []
    ai_insight: Optional[dict] = None


class MultiSimulationResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    simulation_type: str
    scenario: dict
    variable_count: int
    baseline_prediction: float
    scenario_prediction: float
    delta: float
    delta_pct: float
    prediction_interval: PredictionInterval
    variable_impacts: List[VariableImpact]
    confidence: ConfidenceScore
    model_used: str
    model_r2: float
    recommendations: List[str] = []
    visualizations: List[ChartMetadata] = []
    ai_insight: Optional[dict] = None


class SensitivityRanking(BaseModel):
    rank: int
    column: str
    sensitivity_score: float
    relative_sensitivity: float
    elasticity: float
    direction: str


class SensitivityResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    target_column: str
    model_used: str
    model_r2: float
    confidence: Optional[ConfidenceScore] = None
    columns_analysed: int
    sensitivity_ranking: List[SensitivityRanking]
    most_sensitive: Optional[str] = None
    least_sensitive: Optional[str] = None
    recommendations: List[str] = []
    visualizations: List[ChartMetadata] = []
    ai_insight: Optional[dict] = None


class ScenarioResult(BaseModel):
    name: str
    variables: Optional[dict] = None
    prediction: Optional[float] = None
    delta: Optional[float] = None
    delta_pct: Optional[float] = None
    prediction_interval: Optional[dict] = None
    rank: Optional[int] = None
    error: Optional[str] = None


class ScenarioComparisonResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    target_column: str
    baseline_prediction: float
    model_used: str
    model_r2: float
    confidence: ConfidenceScore
    scenario_count: int
    results: List[ScenarioResult]
    best_scenario: Optional[str] = None
    worst_scenario: Optional[str] = None
    chart_data: dict
    recommendations: List[str] = []
    visualizations: List[ChartMetadata] = []
    ai_insight: Optional[dict] = None


class SimulationOverviewResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    """Returned by GET /{dataset_id}/simulate — model info before running scenarios."""
    target_column: str
    feature_columns: List[str]
    model_comparison: ModelComparisonSchema
    feature_stats: dict
    visualizations: List[ChartMetadata] = []


# ── Assistant chat -- conversational help, distinct from the ────────────
# ── structured JSON board-report templates used elsewhere in this file ──

class AssistantChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AssistantChatRequest(BaseModel):
    message: str
    dataset_id: Optional[uuid.UUID] = None
    current_page: Optional[str] = None
    history: List[AssistantChatMessage] = []


class AssistantChatResponse(BaseModel):
    reply: str
    source: str  # "ai" | "fallback"
