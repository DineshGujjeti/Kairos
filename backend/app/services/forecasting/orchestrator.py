"""
Forecasting orchestrator: coordinates detection, training, evaluation, and analysis.

Every entry point here goes through safe_validate_for_forecasting()
rather than the raising validate_for_forecasting() directly, so a
dataset with no usable date column (or too little data) degrades to a
structured {"available": False, "unavailable_reason": "..."} response
instead of an HTTP 422 -- see detector.py for the graceful-degradation
logic itself, including the row-order synthetic datetime fallback for
datasets that have a real trend but no calendar dates.
"""
import pandas as pd

from app.services.forecasting.detector import (
    build_synthetic_datetime_column,
    safe_validate_for_forecasting,
    SYNTHETIC_DATETIME_COLUMN,
)
from app.services.forecasting.trainer import train_model
from app.services.forecasting.evaluator import backtest_model, evaluate_model
from app.services.forecasting.analysis import detect_trend, detect_seasonality, compute_confidence_interval


def _with_synthetic_column_if_needed(df: pd.DataFrame, validation: dict) -> pd.DataFrame:
    """Returns *df*, or a copy with the synthetic sequence column added
    when validation selected the synthetic-datetime fallback."""
    if not validation.get("synthetic_datetime"):
        return df
    working = df.copy()
    working[SYNTHETIC_DATETIME_COLUMN] = build_synthetic_datetime_column(working)
    return working


def forecast_overview(
    df: pd.DataFrame,
    datetime_col: str | None = None,
    target_col: str | None = None,
) -> dict:
    """Overview of dataset for forecasting with auto-detection info.
    Never raises -- returns {"available": False, "unavailable_reason": ...}
    when this dataset genuinely cannot be forecast."""
    validation = safe_validate_for_forecasting(df, datetime_col, target_col)
    if not validation["available"]:
        return {"available": False, "unavailable_reason": validation["unavailable_reason"]}

    working = _with_synthetic_column_if_needed(df, validation)
    dt_col = validation["datetime_column"]
    tgt_col = validation["target_column"]

    return {
        "available": True,
        "synthetic_datetime": validation["synthetic_datetime"],
        "rows": len(working),
        "columns": len(df.columns),  # original column count; synthetic col is internal
        "datetime_column": dt_col,
        "target_column": tgt_col,
        "datetime_auto_detected": validation["datetime_auto_detected"],
        "target_auto_detected": validation["target_auto_detected"],
        "numeric_columns": len(df.select_dtypes(include="number").columns),
        "datetime_columns": len(df.select_dtypes(include=["datetime", "datetimetz"]).columns),
        "date_range_start": str(pd.to_datetime(working[dt_col]).min()),
        "date_range_end": str(pd.to_datetime(working[dt_col]).max()),
    }


def train_and_evaluate(
    df: pd.DataFrame,
    periods: int = 12,
    datetime_col: str | None = None,
    target_col: str | None = None,
) -> dict:
    """Train, evaluate, and forecast with full metadata. Never raises --
    see forecast_overview for the unavailable-response contract."""
    validation = safe_validate_for_forecasting(df, datetime_col, target_col)
    if not validation["available"]:
        return {"available": False, "unavailable_reason": validation["unavailable_reason"]}

    working = _with_synthetic_column_if_needed(df, validation)
    dt_col = validation["datetime_column"]
    tgt_col = validation["target_column"]

    try:
        model, model_name = train_model(working, dt_col, tgt_col)
        backtest_metrics = backtest_model(model, working, dt_col, tgt_col)
        forecast_dates, forecast_values, lower_bounds, upper_bounds = model.predict(periods)
    except Exception as exc:
        # Model training/prediction failures (e.g. degenerate series,
        # every model in the fallback chain failing) are also reported
        # gracefully rather than surfacing a 500/422 to the frontend.
        return {
            "available": False,
            "unavailable_reason": f"Model training failed for this dataset: {exc}",
        }

    historical_df = working[[dt_col, tgt_col]].copy()
    historical_df[dt_col] = pd.to_datetime(historical_df[dt_col])
    historical_df = historical_df.sort_values(dt_col)
    historical_values = historical_df[tgt_col].tolist()
    historical_dates = [str(d.date()) for d in pd.to_datetime(historical_df[dt_col])]

    return {
        "available": True,
        "synthetic_datetime": validation["synthetic_datetime"],
        "selected_model": model_name,
        "datetime_auto_detected": validation["datetime_auto_detected"],
        "target_auto_detected": validation["target_auto_detected"],
        "detected_datetime_column": dt_col,
        "detected_target_column": tgt_col,
        "training_metrics": backtest_metrics,
        "forecast_dates": forecast_dates,
        "forecast_values": [round(v, 4) for v in forecast_values],
        "confidence_intervals": {
            "confidence_level": 95,
            "lower_bounds": [round(v, 4) for v in lower_bounds],
            "upper_bounds": [round(v, 4) for v in upper_bounds],
        },
        "historical_dates": historical_dates,
        "historical_values": [round(v, 4) for v in historical_values],
    }


def analyze_series(
    df: pd.DataFrame,
    datetime_col: str | None = None,
    target_col: str | None = None,
) -> dict:
    """Analyze time series for trend and seasonality. Never raises --
    see forecast_overview for the unavailable-response contract."""
    validation = safe_validate_for_forecasting(df, datetime_col, target_col)
    if not validation["available"]:
        return {"available": False, "unavailable_reason": validation["unavailable_reason"]}

    working = _with_synthetic_column_if_needed(df, validation)
    dt_col = validation["datetime_column"]
    tgt_col = validation["target_column"]

    prepared = working[[dt_col, tgt_col]].copy()
    prepared[dt_col] = pd.to_datetime(prepared[dt_col])
    prepared = prepared.sort_values(dt_col).dropna()

    values = prepared[tgt_col].values.tolist()

    trend_analysis = detect_trend(values)
    seasonality_analysis = detect_seasonality(values)

    return {
        "available": True,
        "synthetic_datetime": validation["synthetic_datetime"],
        "datetime_column": dt_col,
        "target_column": tgt_col,
        "datetime_auto_detected": validation["datetime_auto_detected"],
        "target_auto_detected": validation["target_auto_detected"],
        "total_observations": len(values),
        "trend": trend_analysis,
        "seasonality": seasonality_analysis,
    }


def full_forecast_report(
    df: pd.DataFrame,
    periods: int = 12,
    datetime_col: str | None = None,
    target_col: str | None = None,
) -> dict:
    """Complete forecasting report: overview + analysis + forecast.
    Resolves datetime/target columns exactly once and threads the
    result through to all three sub-calls, so the synthetic-datetime
    fallback (when used) is identical across all three sections rather
    than being independently re-derived three times."""
    validation = safe_validate_for_forecasting(df, datetime_col, target_col)
    if not validation["available"]:
        return {"available": False, "unavailable_reason": validation["unavailable_reason"]}

    resolved_dt = validation["datetime_column"]
    resolved_tgt = validation["target_column"]
    # Pass the already-resolved real column name through explicitly so
    # each sub-call's own safe_validate_for_forecasting short-circuits
    # to the same result instead of re-detecting -- except when the
    # datetime column is synthetic, in which case there's no real column
    # name to pass down; each sub-call re-derives the same synthetic
    # column deterministically instead (see build_synthetic_datetime_column).
    passthrough_dt = None if validation["synthetic_datetime"] else resolved_dt

    overview = forecast_overview(df, passthrough_dt, resolved_tgt)
    training = train_and_evaluate(df, periods, passthrough_dt, resolved_tgt)
    analysis = analyze_series(df, passthrough_dt, resolved_tgt)

    if not (overview.get("available") and training.get("available") and analysis.get("available")):
        reason = (
            overview.get("unavailable_reason")
            or training.get("unavailable_reason")
            or analysis.get("unavailable_reason")
        )
        return {"available": False, "unavailable_reason": reason}

    return {
        "available": True,
        "overview": overview,
        "analysis": analysis,
        "forecast": training,
    }
