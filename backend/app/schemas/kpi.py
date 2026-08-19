from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


# ============================================================
# 1. Overview
# ============================================================


class KPIOverviewResponse(BaseModel):
    rows: int
    columns: int
    numeric_columns: int
    categorical_columns: int
    datetime_columns: int
    duplicate_rows: int
    missing_values: int
    memory_usage_mb: float


# ============================================================
# 2. Metrics
# ============================================================


class ColumnMetrics(BaseModel):
    count: int
    sum: float | None
    mean: float | None
    median: float | None
    variance: float | None
    std: float | None
    min: float | None
    max: float | None
    unique_values: int
    missing_values: int


class KPIMetricsResponse(BaseModel):
    total_numeric_columns: int
    columns: dict[str, ColumnMetrics]


# ============================================================
# 3. Ranking
# ============================================================


class RankingItem(BaseModel):
    dimension_value: str
    metric_value: float | None
    percentage_of_total: float | None = None


class KPIRankingResponse(BaseModel):
    dimension: str
    metric: str
    aggregation: str
    top_n: int
    total_groups: int
    items: list[RankingItem]


# ============================================================
# 4. Trend
# ============================================================


class TrendPoint(BaseModel):
    period: str
    value: float | None


class KPITrendResponse(BaseModel):
    has_datetime_column: bool
    message: str | None
    detected_datetime_columns: list[str]
    datetime_column_used: str | None
    frequency: str
    metric: str
    points: list[TrendPoint]


# ============================================================
# 5. Dashboard
# ============================================================


class KPIDashboardResponse(BaseModel):
    overview: KPIOverviewResponse
    metrics: KPIMetricsResponse
    alerts: dict
    timestamp: str


# ============================================================
# 6. Alerts
# ============================================================


class KPIAlertsResponse(BaseModel):
    total_alerts: int
    alerts: list[str]
    severity_high: int


# ============================================================
# 7. Formula
# ============================================================


class FormulaRequest(BaseModel):
    formula: str


class FormulaStats(BaseModel):
    mean: float
    sum: float
    min: float
    max: float


class KPIFormulaResponse(BaseModel):
    formula: str
    result_type: str
    values: Optional[dict[str, Any]] = None
    value: Optional[float] = None
    stats: Optional[FormulaStats] = None


# ============================================================
# 8. Smart KPI Cards -- curated, business-readable metrics
# ============================================================


class SmartKPICard(BaseModel):
    key: str
    label: str
    value: float
    formatted_value: str
    aggregation: str
    trend_available: bool
    direction: str
    change_pct: Optional[float] = None
    sentiment: str
    comparison_basis: Optional[str] = None
    description: str
    is_notable: bool


class SmartKPICardsResponse(BaseModel):
    cards: list[SmartKPICard]
    has_measures: bool
    has_time_comparison: bool
    datetime_column: Optional[str] = None
    summary: Optional[str] = None
