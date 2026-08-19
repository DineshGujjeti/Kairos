"""
Module 5: Forecasting Engine API routes.

Nine endpoints for complete forecasting workflow with auto-detection,
training, evaluation, and analysis.
"""
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.forecasting import (
    ForecastOverviewResponse,
    ForecastPredictionResponse,
    SeriesAnalysisResponse,
    CompleteForecastReport,
    ForecastRequest,
)
from app.services.kpi.loader import load_dataframe
from app.services.forecasting.orchestrator import (
    forecast_overview,
    train_and_evaluate,
    analyze_series,
    full_forecast_report,
)

router = APIRouter(prefix="/forecasting", tags=["forecasting"])


@router.get("/{dataset_id}/overview", response_model=ForecastOverviewResponse)
def get_forecast_overview(
    dataset_id: uuid.UUID,
    datetime_column: str | None = Query(None),
    target_column: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Overview of dataset for forecasting: shape, columns, date range."""
    df = load_dataframe(dataset_id, db, current_user)
    return forecast_overview(df, datetime_column, target_column)


@router.post("/{dataset_id}/forecast", response_model=ForecastPredictionResponse)
def train_forecast_model(
    dataset_id: uuid.UUID,
    body: ForecastRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Train forecasting model and generate predictions."""
    df = load_dataframe(dataset_id, db, current_user)
    return train_and_evaluate(df, body.periods, body.datetime_column, body.target_column)


@router.get("/{dataset_id}/analysis", response_model=SeriesAnalysisResponse)
def analyze_time_series(
    dataset_id: uuid.UUID,
    datetime_column: str | None = Query(None),
    target_column: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze time series for trend and seasonality patterns."""
    df = load_dataframe(dataset_id, db, current_user)
    return analyze_series(df, datetime_column, target_column)


@router.post("/{dataset_id}/report", response_model=CompleteForecastReport)
def generate_forecast_report(
    dataset_id: uuid.UUID,
    body: ForecastRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete forecasting report: overview + analysis + forecast."""
    df = load_dataframe(dataset_id, db, current_user)
    return full_forecast_report(df, body.periods, body.datetime_column, body.target_column)
