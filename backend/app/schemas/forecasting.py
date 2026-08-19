"""
Response schemas for Module 5 (Forecasting Engine).
"""
from typing import Optional
from pydantic import BaseModel


class ForecastOverviewResponse(BaseModel):
    available: bool = True
    unavailable_reason: Optional[str] = None
    synthetic_datetime: bool = False
    rows: Optional[int] = None
    columns: Optional[int] = None
    datetime_column: Optional[str] = None
    target_column: Optional[str] = None
    datetime_auto_detected: bool = False
    target_auto_detected: bool = False
    numeric_columns: Optional[int] = None
    datetime_columns: Optional[int] = None
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None


class ConfidenceIntervals(BaseModel):
    confidence_level: int
    lower_bounds: list[float]
    upper_bounds: list[float]


class TrainingMetrics(BaseModel):
    rmse: Optional[float]
    mae: Optional[float]
    mape: Optional[float]


class ForecastPredictionResponse(BaseModel):
    available: bool = True
    unavailable_reason: Optional[str] = None
    synthetic_datetime: bool = False
    selected_model: Optional[str] = None
    datetime_auto_detected: bool = False
    target_auto_detected: bool = False
    detected_datetime_column: Optional[str] = None
    detected_target_column: Optional[str] = None
    training_metrics: Optional[TrainingMetrics] = None
    forecast_dates: list[str] = []
    forecast_values: list[float] = []
    confidence_intervals: Optional[ConfidenceIntervals] = None
    historical_dates: list[str] = []
    historical_values: list[float] = []


class TrendAnalysis(BaseModel):
    direction: str
    slope: float
    strength: float


class SeasonalityAnalysis(BaseModel):
    is_seasonal: bool
    detected_period: Optional[int]
    strength: float
    message: str


class SeriesAnalysisResponse(BaseModel):
    available: bool = True
    unavailable_reason: Optional[str] = None
    synthetic_datetime: bool = False
    datetime_column: Optional[str] = None
    target_column: Optional[str] = None
    datetime_auto_detected: bool = False
    target_auto_detected: bool = False
    total_observations: Optional[int] = None
    trend: Optional[TrendAnalysis] = None
    seasonality: Optional[SeasonalityAnalysis] = None


class CompleteForecastReport(BaseModel):
    available: bool = True
    unavailable_reason: Optional[str] = None
    overview: Optional[ForecastOverviewResponse] = None
    analysis: Optional[SeriesAnalysisResponse] = None
    forecast: Optional[ForecastPredictionResponse] = None


class ForecastRequest(BaseModel):
    periods: int = 12
    datetime_column: Optional[str] = None
    target_column: Optional[str] = None
