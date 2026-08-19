import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.logging import get_logger
from app.db.models.dataset import DatasetStatus, DatasetType
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.dataset import (
    DatasetListItem,
    DatasetListResponse,
    DatasetPreviewResponse,
    DatasetRead,
)
from app.services import dataset_service, ingestion_service
from app.services.dataset_intelligence import profile_dataset
from app.services.kpi.loader import invalidate_dataframe_cache
from app.services.root_cause.driver_detector import invalidate_driver_cache
from app.services.simulation.model_trainer import invalidate_model_cache

router = APIRouter(prefix="/datasets", tags=["datasets"])
logger = get_logger(__name__)


@router.post("/upload", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_type: DatasetType = Form(default=DatasetType.GENERAL),
    name: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    """
    Full ingestion flow, synchronous for Module 2: validate metadata ->
    stream to disk -> read with pandas -> clean -> infer schema ->
    structurally validate -> DuckDB cross-check -> persist result.

    Deliberately synchronous rather than a background task: uploads in
    this platform are expected to be at most tens of MB (see
    MAX_UPLOAD_SIZE_MB) and the user needs immediate pass/fail
    feedback to fix a bad file. Genuinely large/slow jobs (model
    training, PDF generation) are the ones that belong on the Celery
    queue mentioned in the architecture doc -- this isn't one of them.
    """
    extension = ingestion_service.validate_upload_metadata(file.filename)

    dataset_id = uuid.uuid4()
    file_path, size_bytes = await ingestion_service.store_upload(
        file, current_user.org_id, dataset_id, extension
    )

    dataset = dataset_service.create_dataset_record(
        db,
        org_id=current_user.org_id,
        uploaded_by=current_user.id,
        name=name or file.filename,
        dataset_type=dataset_type,
        original_filename=file.filename,
        stored_filename=f"{dataset_id}.{extension}",
        file_path=file_path,
        file_size_bytes=size_bytes,
    )
    # The DB row's own id (not our pre-generated dataset_id) is the
    # source of truth from here on, but they're the same value since
    # create_dataset_record doesn't override the PK default -- asserted
    # implicitly by using dataset.id below rather than dataset_id.

    try:
        df = ingestion_service.read_dataset_file(file_path, extension)
        df, cleaning_notes = ingestion_service.clean_dataframe(df)
        schema = ingestion_service.infer_schema(df)
        validation_errors = ingestion_service.validate_structure(df, dataset_type)
        duckdb_count = ingestion_service.duckdb_row_count_check(file_path, extension)

        # Dynamic, dataset-agnostic profiling -- runs for every dataset
        # regardless of dataset_type, so EDA/KPI/Forecasting/Root Cause/
        # Simulation/Decision all have a shared picture of detected
        # column roles even for datasets with no fixed schema. Never
        # allowed to fail the whole upload -- worst case it degrades to
        # an empty profile and the rest of the pipeline still runs.
        try:
            column_profile = profile_dataset(df)
        except Exception as exc:
            logger.warning("dataset_profiling_failed", dataset_id=str(dataset.id), error=str(exc))
            column_profile = None

        final_status = DatasetStatus.INVALID if validation_errors else DatasetStatus.VALID
        message = "; ".join(cleaning_notes) if cleaning_notes else None
        if duckdb_count is not None and duckdb_count != len(df):
            logger.warning(
                "duckdb_row_count_mismatch",
                dataset_id=str(dataset.id),
                pandas_count=len(df),
                duckdb_count=duckdb_count,
            )

        dataset = dataset_service.update_dataset_after_processing(
            db,
            dataset,
            row_count=len(df),
            column_count=df.shape[1],
            schema_json=schema,
            status=final_status,
            status_message=message,
            validation_errors=validation_errors,
            column_profile=column_profile,
        )
    except Exception as exc:
        # The file is safely stored and the metadata row exists even if
        # processing fails -- we mark it FAILED rather than losing the
        # upload, so the user can see what happened and re-upload
        # without wondering whether the first attempt silently vanished.
        logger.error("dataset_processing_failed", dataset_id=str(dataset.id), error=str(exc))
        dataset = dataset_service.update_dataset_after_processing(
            db,
            dataset,
            row_count=None,
            column_count=None,
            schema_json=None,
            status=DatasetStatus.FAILED,
            status_message=str(exc),
            validation_errors=None,
        )

    return dataset


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    dataset_type: DatasetType | None = Query(default=None),
    status_filter: DatasetStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200, ge=1),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = dataset_service.list_datasets(
        db,
        current_user.org_id,
        dataset_type=dataset_type,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    list_items = [
        DatasetListItem(
            id=d.id,
            name=d.name,
            dataset_type=d.dataset_type,
            status=d.status,
            row_count=d.row_count,
            column_count=d.column_count,
            file_size_bytes=d.file_size_bytes,
            domain_guess=(d.column_profile or {}).get("domain_guess"),
            created_at=d.created_at,
        )
        for d in items
    ]
    return DatasetListResponse(total=total, items=list_items)


@router.get("/{dataset_id}", response_model=DatasetRead)
def get_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return dataset_service.get_dataset_or_404(db, dataset_id, current_user.org_id)


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def preview_dataset(
    dataset_id: uuid.UUID,
    rows: int = Query(default=20, le=200, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = dataset_service.get_dataset_or_404(db, dataset_id, current_user.org_id)
    extension = dataset.original_filename.rsplit(".", 1)[-1].lower()
    df = ingestion_service.read_dataset_file(dataset.file_path, extension)
    preview_df = df.head(rows)
    return DatasetPreviewResponse(
        columns=list(preview_df.columns.astype(str)),
        rows=preview_df.to_dict(orient="records"),
        row_count_shown=len(preview_df),
        row_count_total=dataset.row_count,
    )


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    dataset = dataset_service.get_dataset_or_404(db, dataset_id, current_user.org_id)
    dataset_service.delete_dataset(db, dataset)
    invalidate_dataframe_cache(dataset_id)
    invalidate_driver_cache(dataset_id)
    invalidate_model_cache(dataset_id)
