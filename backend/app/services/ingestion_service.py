"""
Ingestion pipeline: everything that happens to a file between "user
clicked upload" and "we have a validated Dataset row in Postgres".

Deliberately separate from dataset_service.py (CRUD/persistence) -- this
module owns file I/O and pandas/DuckDB logic, dataset_service owns the
database. Module 3 (EDA) reuses read_dataset_file()/DuckDB access here
rather than reinventing it.
"""
import uuid
from pathlib import Path

import pandas as pd
from fastapi import UploadFile
from pandera.errors import SchemaErrors

from app.core.config import settings
from app.core.exceptions import (
    DatasetParseError,
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.core.logging import get_logger
from app.db.duckdb_client import query_uploaded_file
from app.services.dataset_validation_schemas import get_schema_for

logger = get_logger(__name__)

CHUNK_SIZE = 1024 * 1024  # 1MB, used while streaming the upload to disk


def _extension_of(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()


def validate_upload_metadata(filename: str) -> str:
    """
    Cheap checks that don't require reading file content: extension
    allow-list. Full content validation (parseable, matches schema)
    happens later, after the file is safely on disk -- there's no
    point streaming a 2GB file to disk just to reject its extension,
    so this runs first.
    """
    extension = _extension_of(filename)
    if extension not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise UnsupportedFileTypeError(extension, settings.ALLOWED_UPLOAD_EXTENSIONS)
    return extension


async def store_upload(file: UploadFile, org_id: uuid.UUID, dataset_id: uuid.UUID, extension: str) -> tuple[str, int]:
    """
    Streams the upload to disk in chunks (never loads the whole file
    into memory at once) under a UUID-based filename, enforcing the
    size limit as it goes rather than after the fact -- this bounds
    memory AND disk usage for a file that turns out to be oversized,
    instead of writing the whole thing first and rejecting it after.

    Returns (absolute_file_path, size_in_bytes).
    """
    org_dir = Path(settings.DATASET_STORAGE_DIR) / str(org_id)
    org_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{dataset_id}.{extension}"
    destination = org_dir / stored_filename
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    size = 0
    try:
        with open(destination, "wb") as out_file:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise FileTooLargeError(size / (1024 * 1024), settings.MAX_UPLOAD_SIZE_MB)
                out_file.write(chunk)
    except FileTooLargeError:
        destination.unlink(missing_ok=True)  # don't leave a partial file behind
        raise

    if size == 0:
        destination.unlink(missing_ok=True)
        raise EmptyFileError()

    return str(destination), size


def read_dataset_file(file_path: str, extension: str) -> pd.DataFrame:
    """
    Single entry point for reading an uploaded dataset with pandas.
    Both CSV and Excel funnel through here so every other function in
    this module (and Module 3's EDA engine later) can stay format-agnostic.
    """
    try:
        if extension == "csv":
            return pd.read_csv(file_path)
        return pd.read_excel(file_path)  # covers .xls and .xlsx
    except Exception as exc:  # pandas raises many different exception types here
        raise DatasetParseError(str(exc)) from exc


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Minimal, safe, fully-reversible cleaning -- no imputation or row
    deletion based on business logic, since that's a judgment call that
    belongs to a human or to Module 3's EDA findings, not to a silent
    upload-time step. What's done here is purely structural hygiene:

    - normalize column names (strip whitespace, lowercase, snake_case)
    - drop rows that are entirely empty (artifacts of Excel exports)
    - drop columns that are entirely empty (same reason)

    Returns the cleaned dataframe and a human-readable list of what changed.
    """
    notes: list[str] = []

    original_columns = list(df.columns)
    df.columns = [
        str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns
    ]
    if list(df.columns) != original_columns:
        notes.append("Normalized column names to snake_case")

    before_rows = len(df)
    df = df.dropna(how="all")
    if len(df) != before_rows:
        notes.append(f"Dropped {before_rows - len(df)} fully-empty row(s)")

    before_cols = df.shape[1]
    df = df.dropna(axis=1, how="all")
    if df.shape[1] != before_cols:
        notes.append(f"Dropped {before_cols - df.shape[1]} fully-empty column(s)")

    return df, notes


def infer_schema(df: pd.DataFrame) -> dict:
    """Column-name -> pandas-dtype-as-string, stored as Dataset.schema_json."""
    return {col: str(dtype) for col, dtype in df.dtypes.items()}


def validate_structure(df: pd.DataFrame, dataset_type) -> dict | None:
    """
    Runs the Pandera schema for this dataset_type. Returns None if
    valid (or if dataset_type is GENERAL, which has no fixed schema and
    is always considered structurally valid -- see dataset_intelligence
    for its dynamic profiling instead), or a dict of
    {column: [error messages]} if not. Uses `.validate(lazy=True)` so
    ALL structural problems are collected and reported at once, rather
    than the user fixing one missing column, re-uploading, and
    immediately hitting the next one.
    """
    schema = get_schema_for(dataset_type)
    if schema is None:
        return None
    try:
        schema.validate(df, lazy=True)
        return None
    except SchemaErrors as exc:
        errors: dict[str, list[str]] = {}
        for _, row in exc.failure_cases.iterrows():
            col = str(row.get("column") or "dataframe")
            errors.setdefault(col, []).append(str(row.get("check")))
        return errors


def duckdb_row_count_check(file_path: str, extension: str) -> int | None:
    """
    Cross-checks the row count via DuckDB's read_csv_auto, independent
    of the pandas read above. This is a deliberately small use of
    DuckDB in Module 2 -- its real workload starts in Module 3 (EDA) --
    but it proves the integration end-to-end and gives us a second,
    faster opinion on row count without re-reading the file into pandas.
    XLSX isn't a DuckDB read_csv_auto source, so this check is CSV-only;
    Excel files just skip it (pandas' count is authoritative there).
    """
    if extension != "csv":
        return None
    try:
        result_df = query_uploaded_file(file_path, "SELECT COUNT(*) AS n FROM {source}")
        return int(result_df["n"].iloc[0])
    except Exception as exc:
        logger.warning("duckdb_row_count_check_failed", error=str(exc))
        return None
