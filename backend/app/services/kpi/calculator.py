"""
Feature 2: KPI Metrics.

Computes the ten standard aggregate metrics for every numeric column.
Kept separate from overview.py (dataset-level shape) and distribution.py
(Module 3's shape/skew analysis) on purpose -- this is the flat,
dashboard-friendly "here are the numbers" view a KPI panel needs, not a
statistical characterization of the column's shape.
"""
import pandas as pd


def compute_column_metrics(df: pd.DataFrame) -> dict:
    numeric_df = df.select_dtypes(include="number")

    if numeric_df.empty:
        return {"total_numeric_columns": 0, "columns": {}}

    columns: dict[str, dict] = {}
    for column in numeric_df.columns:
        series = numeric_df[column]
        non_null = series.dropna()
        has_values = not non_null.empty

        columns[column] = {
            "count": int(non_null.count()),
            "sum": round(float(non_null.sum()), 4) if has_values else None,
            "mean": round(float(non_null.mean()), 4) if has_values else None,
            "median": round(float(non_null.median()), 4) if has_values else None,
            "variance": round(float(non_null.var()), 4) if len(non_null) > 1 else None,
            "std": round(float(non_null.std()), 4) if len(non_null) > 1 else None,
            "min": round(float(non_null.min()), 4) if has_values else None,
            "max": round(float(non_null.max()), 4) if has_values else None,
            "unique_values": int(series.nunique(dropna=True)),
            "missing_values": int(series.isna().sum()),
        }

    return {
        "total_numeric_columns": len(columns),
        "columns": columns,
    }
