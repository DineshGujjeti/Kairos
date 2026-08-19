"""
Feature 1: KPI Overview.

Dataset-level shape summary for a dashboard header. Overlaps in spirit
with Module 3's summary.py, but is intentionally its own small function
here (not imported from eda/) since the KPI module's spec calls for a
distinct set of fields (duplicate_rows, total missing_values) that
Module 3's summary.py doesn't compute -- reusing it would mean either
extending Module 3's output shape (touching a module we were told not
to change) or wrapping/re-deriving around it, which is more indirection
than just computing these six numbers directly from the DataFrame.
"""
import pandas as pd

from app.core.pandas_compat import TEXT_DTYPES_NO_CATEGORY


def overview(df: pd.DataFrame) -> dict:
    memory_usage_mb = round(float(df.memory_usage(deep=True).sum()) / (1024 * 1024), 4)

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "numeric_columns": len(df.select_dtypes(include="number").columns),
        "categorical_columns": len(df.select_dtypes(include=TEXT_DTYPES_NO_CATEGORY).columns),
        "datetime_columns": len(df.select_dtypes(include=["datetime", "datetimetz"]).columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_values": int(df.isna().sum().sum()),
        "memory_usage_mb": memory_usage_mb,
    }
