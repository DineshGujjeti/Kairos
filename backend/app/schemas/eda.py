"""
Response schemas for Module 3 (EDA).

Each model here corresponds 1:1 with a function in app/services/eda/
and matches its actual return shape -- not an idealized one. This
matters because FastAPI's response_model performs real validation
against these on every response; a schema that's "close enough" to the
service output produces ResponseValidationError (HTTP 500) rather than
silently passing extra/missing fields through.

Where a service function's dict has a mix of both float and None
(e.g. an empty column after dropna), fields are typed `X | None`
rather than just `X` -- reflects reality, not optimism.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============================================================
# 1. Preview
# ============================================================


class DatasetPreviewResponse(BaseModel):
    rows: int
    columns: int
    column_names: list[str]
    dtypes: dict[str, str]
    missing_values: dict[str, int]
    duplicate_rows: int
    sample_rows: list[dict[str, Any]]


# ============================================================
# 2. Summary
# ============================================================


class DatasetSummaryResponse(BaseModel):
    rows: int
    columns: int
    memory_usage_mb: float
    numeric_columns: int
    categorical_columns: int
    datetime_columns: int


# ============================================================
# 3. Statistics
# ============================================================


class ColumnStatistics(BaseModel):
    """
    Percentile keys ('25%', '50%', '75%') aren't valid Python
    identifiers, so they're aliased. FastAPI serializes response
    models by alias by default (response_model_by_alias=True), so the
    JSON the client sees still has the '25%'/'50%'/'75%' keys the
    service function actually produces.
    """

    count: int
    mean: float | None
    std: float | None
    min: float | None
    p25: float | None = Field(alias="25%")
    p50: float | None = Field(alias="50%")
    p75: float | None = Field(alias="75%")
    max: float | None


class DatasetStatisticsResponse(BaseModel):
    columns: dict[str, ColumnStatistics]
    total_numeric_columns: int


# ============================================================
# 4. Missing Values
# ============================================================


class MissingValuesDatasetInfo(BaseModel):
    rows: int
    columns: int
    total_cells: int
    total_missing_cells: int
    dataset_completeness: float


class MissingValuesSummary(BaseModel):
    columns_with_missing: int
    complete_columns: int
    missing_columns: list[str]
    complete_column_names: list[str]


class ColumnMissingInfo(BaseModel):
    missing_count: int
    missing_percentage: float
    is_complete: bool


class DatasetMissingValuesResponse(BaseModel):
    dataset: MissingValuesDatasetInfo
    summary: MissingValuesSummary
    columns: dict[str, ColumnMissingInfo]


# ============================================================
# 5. Correlation
# ============================================================


class CorrelationPair(BaseModel):
    column_1: str
    column_2: str
    correlation: float
    absolute_correlation: float


class DatasetCorrelationResponse(BaseModel):
    method: str
    threshold: float
    total_numeric_columns: int
    correlation_matrix: dict[str, dict[str, float | None]]
    highly_correlated_pairs: list[CorrelationPair]
    strongest_positive: list[CorrelationPair]
    strongest_negative: list[CorrelationPair]


# ============================================================
# 6. Outlier Detection
# ============================================================


class OutlierColumnInfo(BaseModel):
    q1: float | None
    q3: float | None
    iqr: float | None
    lower_bound: float | None
    upper_bound: float | None
    outlier_count: int
    outlier_percentage: float
    outlier_indices: list[int]


class DatasetOutlierResponse(BaseModel):
    total_numeric_columns: int
    columns_with_outliers: int
    column_names_with_outliers: list[str]
    total_outliers: int
    columns: dict[str, OutlierColumnInfo]


# ============================================================
# 7. Distribution Analysis
# ============================================================


class DistributionColumnInfo(BaseModel):
    count: int
    mean: float | None
    median: float | None
    mode: float | None
    variance: float | None
    std: float | None
    min: float | None
    max: float | None
    range: float | None
    skewness: float | None
    kurtosis: float | None
    unique_values: int
    zero_count: int
    negative_count: int
    coefficient_of_variation: float | None


class DatasetDistributionResponse(BaseModel):
    total_numeric_columns: int
    columns: dict[str, DistributionColumnInfo]


# ============================================================
# 8. Data Quality Score
# ============================================================


class QualityMetrics(BaseModel):
    completeness: float
    duplicate_score: float
    uniqueness_score: float
    consistency_score: float


class QualitySummary(BaseModel):
    rows: int
    columns: int
    total_cells: int
    missing_cells: int
    duplicate_rows: int
    inconsistent_columns: int


class DatasetQualityResponse(BaseModel):
    quality_score: float
    rating: str
    metrics: QualityMetrics
    summary: QualitySummary


# ============================================================
# 9. AI Insights (rule-based)
# ============================================================


class DatasetInsightsResponse(BaseModel):
    total_insights: int
    insights: list[str]


# ============================================================
# 10. Unified EDA Report
# ============================================================


class DatasetReportResponse(BaseModel):
    """
    The single consolidated report -- mirrors app.services.eda.report.report()
    exactly, which itself just calls the other nine functions and combines
    their output under these same nine keys.
    """

    preview: DatasetPreviewResponse
    summary: DatasetSummaryResponse
    statistics: DatasetStatisticsResponse
    missing_values: DatasetMissingValuesResponse
    correlation: DatasetCorrelationResponse
    outliers: DatasetOutlierResponse
    distribution: DatasetDistributionResponse
    quality: DatasetQualityResponse
    insights: DatasetInsightsResponse
