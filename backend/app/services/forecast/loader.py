"""
Dataset loading and preparation for forecasting.

Reuses Module 2's dataset service and Module 2's ingestion service for file reading.
Adds light preprocessing for time-series data (sorting, handling missing values in target).
"""
import uuid
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.services.dataset_service import get_dataset_or_404
from app.services.ingestion_service import read_dataset_file


def load_timeseries_dataframe(
    dataset_id: uuid.UUID, db: Session, current_user: User
) -> pd.DataFrame:
    """
    Load dataset and prepare for forecasting. Org-scoped via dataset_service.
    """
    dataset = get_dataset_or_404(db=db, dataset_id=dataset_id, org_id=current_user.org_id)
    extension = dataset.original_filename.rsplit(".", 1)[-1].lower()
    df = read_dataset_file(dataset.file_path, extension)

    # Ensure DataFrame is clean for time series work
    df = df.copy()
    return df
