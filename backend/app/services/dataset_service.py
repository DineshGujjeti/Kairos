import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import DatasetNotFoundError
from app.core.logging import get_logger
from app.db.models.dataset import Dataset, DatasetStatus, DatasetType

logger = get_logger(__name__)


def create_dataset_record(
    db: Session,
    *,
    org_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    name: str,
    dataset_type: DatasetType,
    original_filename: str,
    stored_filename: str,
    file_path: str,
    file_size_bytes: int,
) -> Dataset:
    dataset = Dataset(
        org_id=org_id,
        uploaded_by=uploaded_by,
        name=name,
        dataset_type=dataset_type,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size_bytes=file_size_bytes,
        status=DatasetStatus.UPLOADED,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    logger.info(
        "dataset_created",
        dataset_id=str(dataset.id),
        org_id=str(org_id),
        dataset_type=dataset_type.value,
    )
    return dataset


def update_dataset_after_processing(
    db: Session,
    dataset: Dataset,
    *,
    row_count: int | None,
    column_count: int | None,
    schema_json: dict | None,
    status: DatasetStatus,
    status_message: str | None = None,
    validation_errors: dict | None = None,
    column_profile: dict | None = None,
) -> Dataset:
    dataset.row_count = row_count
    dataset.column_count = column_count
    dataset.schema_json = schema_json
    dataset.status = status
    dataset.status_message = status_message
    dataset.validation_errors = validation_errors
    dataset.column_profile = column_profile
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    logger.info(
        "dataset_processed",
        dataset_id=str(dataset.id),
        status=status.value,
        row_count=row_count,
    )
    return dataset


def get_dataset_or_404(db: Session, dataset_id: uuid.UUID, org_id: uuid.UUID) -> Dataset:
    """
    Scoped by org_id on purpose, not just dataset_id: a dataset that
    exists but belongs to a different organization must look identical
    to a dataset that doesn't exist at all -- this is what prevents
    cross-tenant enumeration/existence leaks.
    """
    dataset = db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.org_id == org_id)
    ).scalar_one_or_none()
    if dataset is None:
        raise DatasetNotFoundError(str(dataset_id))
    return dataset


def list_datasets(
    db: Session,
    org_id: uuid.UUID,
    *,
    dataset_type: DatasetType | None = None,
    status: DatasetStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Dataset], int]:
    query = select(Dataset).where(Dataset.org_id == org_id)
    count_query = select(func.count()).select_from(Dataset).where(Dataset.org_id == org_id)

    if dataset_type is not None:
        query = query.where(Dataset.dataset_type == dataset_type)
        count_query = count_query.where(Dataset.dataset_type == dataset_type)
    if status is not None:
        query = query.where(Dataset.status == status)
        count_query = count_query.where(Dataset.status == status)

    total = db.execute(count_query).scalar_one()
    items = (
        db.execute(query.order_by(Dataset.created_at.desc()).limit(limit).offset(offset))
        .scalars()
        .all()
    )
    return list(items), total


def delete_dataset(db: Session, dataset: Dataset) -> None:
    """Removes both the DB record and the underlying file -- deleting
    only one or the other would leave an orphan (a ghost DB row or an
    unreferenced file silently consuming disk)."""
    file_path = Path(dataset.file_path)
    dataset_id = str(dataset.id)

    db.delete(dataset)
    db.commit()

    if file_path.exists():
        file_path.unlink()

    logger.info("dataset_deleted", dataset_id=dataset_id)
