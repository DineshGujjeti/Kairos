"""
Feature 3: Predict future values with confidence intervals.

Uses trained model metadata to generate predictions.
For Prophet-trained models, extracts CI from Prophet's forecast.
For Linear Regression, calculates CI based on residual variance.
"""
import pandas as pd
import numpy as np
from datetime import timedelta

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


def predict(
    df: pd.DataFrame,
    datetime_col: str,
    target_col: str,
    model_type: str,
    periods: int = 30,
    confidence_level: float = 0.95,
) -> dict:
    """
    Generate predictions with confidence intervals.
    """
    ts_df = df[[datetime_col, target_col]].copy()
    ts_df[datetime_col] = pd.to_datetime(ts_df[datetime_col], errors="coerce", format="mixed")
    ts_df = ts_df.dropna().sort_values(datetime_col)

    if model_type == "prophet" and PROPHET_AVAILABLE:
        return _predict_prophet(ts_df, datetime_col, target_col, periods)
    else:
        return _predict_linear_regression(ts_df, datetime_col, target_col, periods, confidence_level)


def _predict_prophet(
    ts_df: pd.DataFrame, datetime_col: str, target_col: str, periods: int
) -> dict:
    """Predict using Prophet."""
    prophet_df = ts_df[[datetime_col, target_col]].copy()
    prophet_df.columns = ["ds", "y"]

    model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)

    # Extract future predictions only
    future_forecast = forecast.iloc[-periods:].copy()

    predictions = []
    for _, row in future_forecast.iterrows():
        predictions.append({
            "date": str(row["ds"].date()),
            "forecast": round(float(row["yhat"]), 4),
            "lower_ci": round(float(row["yhat_lower"]), 4),
            "upper_ci": round(float(row["yhat_upper"]), 4),
        })

    return {
        "model_type": "prophet",
        "periods": periods,
        "confidence_level": 0.95,
        "predictions": predictions,
    }


def _predict_linear_regression(
    ts_df: pd.DataFrame,
    datetime_col: str,
    target_col: str,
    periods: int,
    confidence_level: float,
) -> dict:
    """Predict using Linear Regression with confidence intervals."""
    dates = ts_df[datetime_col].values
    target_series = ts_df[target_col].values
    n = len(target_series)

    # Fit linear regression
    x = np.arange(n)
    y = target_series
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    b = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
    a = y_mean - b * x_mean

    # Calculate residuals for CI
    y_pred = a + b * x
    residuals = y - y_pred
    residual_std = np.std(residuals)

    # Generate future predictions
    last_date = pd.to_datetime(dates[-1])
    last_x = n - 1

    predictions = []
    for i in range(1, periods + 1):
        future_x = last_x + i
        future_date = last_date + timedelta(days=1) * i
        forecast_value = a + b * future_x

        # Simple CI: ±1.96*residual_std for 95% confidence
        ci_margin = 1.96 * residual_std if confidence_level == 0.95 else 1.645 * residual_std

        predictions.append({
            "date": str(future_date.date()),
            "forecast": round(float(forecast_value), 4),
            "lower_ci": round(float(forecast_value - ci_margin), 4),
            "upper_ci": round(float(forecast_value + ci_margin), 4),
        })

    return {
        "model_type": "linear_regression",
        "periods": periods,
        "confidence_level": confidence_level,
        "predictions": predictions,
    }
