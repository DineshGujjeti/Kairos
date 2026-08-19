"""
Automatic detection of datetime and target columns.

Datetime detection: tries native datetime types first, then string parsing.
Target detection: defaults to last numeric column if not specified.
"""
import pandas as pd
from app.core.exceptions import NoDatetimeColumnError, ColumnNotFoundError


def detect_datetime_column(df: pd.DataFrame, datetime_column: str | None = None) -> str:
    """
    Detect or validate datetime column.
    If datetime_column is specified, validate it exists and is datetime-like.
    Otherwise, auto-detect from the dataframe.
    """
    if datetime_column is not None:
        if datetime_column not in df.columns:
            raise ColumnNotFoundError(datetime_column)

        if pd.api.types.is_datetime64_any_dtype(df[datetime_column]):
            return datetime_column

        # Try parsing as datetime
        try:
            pd.to_datetime(df[datetime_column], errors="coerce", format="mixed")
            return datetime_column
        except Exception:
            raise ColumnNotFoundError(datetime_column)

    # Auto-detect: prefer native datetime types
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col

    # Try parsing object columns
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna().head(50)
            if sample.empty:
                continue
            try:
                parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
                success_rate = parsed.notna().sum() / len(sample)
                if success_rate >= 0.8:
                    return col
            except Exception:
                continue

    raise NoDatetimeColumnError()


def detect_target_column(
    df: pd.DataFrame, datetime_col: str, target_column: str | None = None
) -> str:
    """
    Detect or validate target column (numeric column to forecast).
    If target_column is specified, validate it's numeric.
    Otherwise, default to the last numeric column (excluding datetime).
    """
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]

    if target_column is not None:
        if target_column not in df.columns:
            raise ColumnNotFoundError(target_column)
        if not pd.api.types.is_numeric_dtype(df[target_column]):
            raise ColumnNotFoundError(target_column)
        return target_column

    if not numeric_cols:
        raise ColumnNotFoundError("no_numeric_columns")

    # Default to last numeric column
    return numeric_cols[-1]
