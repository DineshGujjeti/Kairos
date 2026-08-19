import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.user import User

from app.schemas.eda import (
    DatasetPreviewResponse,
    DatasetSummaryResponse,
    DatasetStatisticsResponse,
    DatasetMissingValuesResponse,
    DatasetCorrelationResponse,
    DatasetOutlierResponse,
    DatasetDistributionResponse,
    DatasetQualityResponse,
    DatasetInsightsResponse,
    DatasetReportResponse,
)

from app.services.dataset_service import get_dataset_or_404
from app.services.ingestion_service import read_dataset_file

from app.services.eda import (
    preview,
    summary,
    statistics,
    missing_values,
    correlation,
    outliers,
    distribution,
    quality,
    insights,
    report,
)

router = APIRouter(
    prefix="/eda",
    tags=["EDA"],
)


def load_dataframe(
    dataset_id: uuid.UUID,
    db: Session,
    current_user: User,
):
    dataset = get_dataset_or_404(
        db=db,
        dataset_id=dataset_id,
        org_id=current_user.org_id,
    )

    extension = dataset.original_filename.rsplit(".", 1)[-1].lower()

    df = read_dataset_file(
        dataset.file_path,
        extension,
    )

    return df


@router.get(
    "/{dataset_id}/preview",
    response_model=DatasetPreviewResponse,
)
def preview_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return preview(df)


@router.get(
    "/{dataset_id}/summary",
    response_model=DatasetSummaryResponse,
)
def dataset_summary(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return summary(df)


@router.get(
    "/{dataset_id}/statistics",
    response_model=DatasetStatisticsResponse,
)
def dataset_statistics(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return statistics(df)


@router.get(
    "/{dataset_id}/missing-values",
    response_model=DatasetMissingValuesResponse,
)
def dataset_missing_values(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return missing_values(df)


@router.get(
    "/{dataset_id}/correlation",
    response_model=DatasetCorrelationResponse,
)
def dataset_correlation(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return correlation(df)


@router.get(
    "/{dataset_id}/outliers",
    response_model=DatasetOutlierResponse,
)
def dataset_outliers(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return outliers(df)


@router.get(
    "/{dataset_id}/distribution",
    response_model=DatasetDistributionResponse,
)
def dataset_distribution(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return distribution(df)


@router.get(
    "/{dataset_id}/quality",
    response_model=DatasetQualityResponse,
)
def dataset_quality(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return quality(df)


@router.get(
    "/{dataset_id}/insights",
    response_model=DatasetInsightsResponse,
)
def dataset_insights(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return insights(df)


@router.get(
    "/{dataset_id}/report",
    response_model=DatasetReportResponse,
)
def dataset_report(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = load_dataframe(dataset_id, db, current_user)
    return report(df)