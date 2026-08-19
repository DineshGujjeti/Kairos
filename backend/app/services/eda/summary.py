import pandas as pd

from app.core.pandas_compat import TEXT_DTYPES_NO_CATEGORY


def summary(df: pd.DataFrame) -> dict:
    """
    Returns high-level information about the dataset.
    """

    memory_usage = (
        df.memory_usage(deep=True).sum() / (1024 * 1024)
    )

    numeric_columns = len(
        df.select_dtypes(include="number").columns
    )

    categorical_columns = len(
        df.select_dtypes(include=TEXT_DTYPES_NO_CATEGORY).columns
    )

    datetime_columns = len(
        df.select_dtypes(include=["datetime", "datetimetz"]).columns
    )

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "memory_usage_mb": round(memory_usage, 2),
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "datetime_columns": datetime_columns,
    }