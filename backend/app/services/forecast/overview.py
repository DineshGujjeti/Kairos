"""
Feature 1: Forecasting Overview.

High-level characteristics of the time series for the dashboard.
"""
import pandas as pd


def overview(df: pd.DataFrame, datetime_col: str, target_col: str) -> dict:
    """
    Time-series overview: date range, frequency, target stats, missing values.
    """
    date_col = pd.to_datetime(df[datetime_col], errors="coerce", format="mixed")
    target_series = df[target_col].dropna()

    date_range = date_col.dropna()
    if len(date_range) > 1:
        min_date = str(date_range.min().date())
        max_date = str(date_range.max().date())
        days_span = (date_range.max() - date_range.min()).days
    else:
        min_date = max_date = None
        days_span = 0

    return {
        "total_rows": len(df),
        "date_range": {"start": min_date, "end": max_date, "days": days_span},
        "target_column": target_col,
        "target_stats": {
            "mean": float(target_series.mean()) if len(target_series) > 0 else None,
            "median": float(target_series.median()) if len(target_series) > 0 else None,
            "std": float(target_series.std()) if len(target_series) > 1 else None,
            "min": float(target_series.min()) if len(target_series) > 0 else None,
            "max": float(target_series.max()) if len(target_series) > 0 else None,
        },
        "missing_values": int(df[target_col].isna().sum()),
        "data_quality": round(
            (1 - df[target_col].isna().sum() / len(df)) * 100, 2
        ),
    }
