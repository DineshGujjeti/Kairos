import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.kpi import (
    KPIOverviewResponse,
    KPIMetricsResponse,
    KPIRankingResponse,
    KPITrendResponse,
    KPIDashboardResponse,
    KPIAlertsResponse,
    KPIFormulaResponse,
    FormulaRequest,
    SmartKPICardsResponse,
)
from app.services.kpi.loader import load_dataframe
from app.services.kpi.overview import overview
from app.services.kpi.calculator import compute_column_metrics
from app.services.kpi.ranking import rank
from app.services.kpi.trend import trend
from app.services.kpi.dashboard import dashboard
from app.services.kpi.alerts import generate_alerts
from app.services.kpi.formula import safe_evaluate_formula
from app.services.kpi.smart_cards import generate_smart_kpi_cards

router = APIRouter(prefix="/kpi", tags=["kpi"])


@router.get("/{dataset_id}/smart-cards", response_model=SmartKPICardsResponse)
def get_smart_kpi_cards(
    dataset_id: uuid.UUID,
    max_cards: int = Query(6, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Curated, business-readable KPI cards: a handful of the metrics that
    actually matter for this dataset, each with a plain-language
    description and a trend where one can honestly be computed -- this
    is the response the KPI page's headline cards are built from,
    distinct from /metrics (the full per-column statistics table).
    """
    df = load_dataframe(dataset_id, db, current_user)
    return generate_smart_kpi_cards(df, max_cards=max_cards)



@router.get("/{dataset_id}/overview", response_model=KPIOverviewResponse)
def get_overview(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return overview(df)


@router.get("/{dataset_id}/metrics", response_model=KPIMetricsResponse)
def get_metrics(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return compute_column_metrics(df)


@router.get("/{dataset_id}/ranking", response_model=KPIRankingResponse)
def get_ranking(
    dataset_id: uuid.UUID,
    dimension: str = Query(...),
    metric: str = Query(...),
    top_n: int = Query(10, le=1000, ge=1),
    aggregation: str = Query("sum"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return rank(df, dimension=dimension, metric=metric, top_n=top_n, aggregation=aggregation)


@router.get("/{dataset_id}/trend", response_model=KPITrendResponse)
def get_trend(
    dataset_id: uuid.UUID,
    metric: str | None = Query(None),
    frequency: str = Query("monthly"),
    datetime_column: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return trend(df, metric=metric, frequency=frequency, datetime_column=datetime_column)


@router.get("/{dataset_id}/dashboard", response_model=KPIDashboardResponse)
def get_dashboard(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return dashboard(df)


@router.get("/{dataset_id}/alerts", response_model=KPIAlertsResponse)
def get_alerts(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return generate_alerts(df)


@router.post("/{dataset_id}/formula", response_model=KPIFormulaResponse)
def evaluate_formula(
    dataset_id: uuid.UUID,
    body: FormulaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return safe_evaluate_formula(df, body.formula)
