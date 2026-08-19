import pandas as pd


def statistics(df: pd.DataFrame) -> dict:
    """
    Returns descriptive statistics for all numeric columns.

    Includes:
    - count
    - mean
    - standard deviation
    - minimum
    - 25th percentile
    - median
    - 75th percentile
    - maximum
    """

    numeric_df = df.select_dtypes(include="number")

    if numeric_df.empty:
        return {
            "columns": {},
            "total_numeric_columns": 0,
        }

    result = {}

    for column in numeric_df.columns:
        series = numeric_df[column]

        desc = series.describe()

        result[column] = {
            "count": int(desc["count"]),
            "mean": (
                round(float(desc["mean"]), 2)
                if not pd.isna(desc["mean"])
                else None
            ),
            "std": (
                round(float(desc["std"]), 2)
                if not pd.isna(desc["std"])
                else None
            ),
            "min": (
                round(float(desc["min"]), 2)
                if not pd.isna(desc["min"])
                else None
            ),
            "25%": (
                round(float(desc["25%"]), 2)
                if not pd.isna(desc["25%"])
                else None
            ),
            "50%": (
                round(float(desc["50%"]), 2)
                if not pd.isna(desc["50%"])
                else None
            ),
            "75%": (
                round(float(desc["75%"]), 2)
                if not pd.isna(desc["75%"])
                else None
            ),
            "max": (
                round(float(desc["max"]), 2)
                if not pd.isna(desc["max"])
                else None
            ),
        }

    return {
        "columns": result,
        "total_numeric_columns": len(result),
    }