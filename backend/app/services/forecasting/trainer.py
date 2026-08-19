"""
Forecasting models: Prophet (primary if available) > Linear Regression > Moving Average.
Each model implements fit() and predict() interface.
"""
import numpy as np
import pandas as pd

from app.core.exceptions import ForecastingModelError

# Try importing Prophet, but don't fail if unavailable
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


class ProphetForecaster:
    """Facebook Prophet for time series forecasting."""

    def __init__(self):
        self.model = None
        self.df = None
        self.end_date = None

    def fit(self, df: pd.DataFrame, datetime_col: str, target_col: str):
        if not PROPHET_AVAILABLE:
            raise ForecastingModelError("Prophet not installed")

        try:
            working = df[[datetime_col, target_col]].copy()
            working[datetime_col] = pd.to_datetime(working[datetime_col], errors="coerce")
            working = working.dropna()

            if len(working) < 10:
                raise ForecastingModelError("Insufficient data for Prophet")

            # Prophet requires 'ds' (datetime) and 'y' (target) columns
            prophet_df = working.rename(columns={
                datetime_col: "ds",
                target_col: "y"
            })
            prophet_df = prophet_df[["ds", "y"]].sort_values("ds").reset_index(drop=True)

            self.model = Prophet(interval_width=0.95, daily_seasonality=False)
            with open('/dev/null', 'w') as f:
                import sys
                old_stdout = sys.stdout
                sys.stdout = f
                try:
                    self.model.fit(prophet_df)
                finally:
                    sys.stdout = old_stdout

            self.df = prophet_df
            self.end_date = prophet_df["ds"].max()
        except Exception as e:
            raise ForecastingModelError(f"Prophet training failed: {str(e)}")

    def predict(self, periods: int = 12) -> tuple[list[str], list[float], list[float], list[float]]:
        if self.model is None:
            raise ForecastingModelError("Model not fitted")

        try:
            future = self.model.make_future_dataframe(periods=periods)
            forecast = self.model.predict(future)

            # Get forecast values for future periods only
            future_forecast = forecast.tail(periods)[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()

            dates = [str(d.date()) for d in pd.to_datetime(future_forecast["ds"])]
            values = future_forecast["yhat"].tolist()
            lower_bounds = future_forecast["yhat_lower"].tolist()
            upper_bounds = future_forecast["yhat_upper"].tolist()

            return dates, values, lower_bounds, upper_bounds
        except Exception as e:
            raise ForecastingModelError(f"Prophet prediction failed: {str(e)}")


class LinearRegressionForecaster:
    """Linear Regression on time index using numpy."""

    def __init__(self):
        self.slope = None
        self.intercept = None
        self.df = None
        self.end_date = None

    def fit(self, df: pd.DataFrame, datetime_col: str, target_col: str):
        try:
            working = df[[datetime_col, target_col]].copy()
            working[datetime_col] = pd.to_datetime(working[datetime_col], errors="coerce")
            working = working.dropna()

            if len(working) < 2:
                raise ForecastingModelError("Insufficient non-null rows")

            working = working.sort_values(datetime_col).reset_index(drop=True)

            X = np.arange(len(working)).astype(float)
            y = working[target_col].values.astype(float)

            mean_x = np.mean(X)
            mean_y = np.mean(y)

            numerator = np.sum((X - mean_x) * (y - mean_y))
            denominator = np.sum((X - mean_x) ** 2)

            self.slope = numerator / denominator if denominator != 0 else 0.0
            self.intercept = mean_y - self.slope * mean_x

            self.df = working
            self.end_date = working[datetime_col].max()
        except Exception as e:
            raise ForecastingModelError(f"Linear Regression training failed: {str(e)}")

    def predict(self, periods: int = 12) -> tuple[list[str], list[float], list[float], list[float]]:
        if self.slope is None:
            raise ForecastingModelError("Model not fitted")

        last_idx = len(self.df) - 1
        future_idx = np.arange(last_idx + 1, last_idx + 1 + periods).astype(float)
        future_values = self.slope * future_idx + self.intercept

        # Estimate std from recent data
        recent_values = self.df[self.df.columns[-1]].tail(10).values
        std_error = float(np.std(recent_values)) if len(recent_values) > 1 else 0.0
        margin = 1.96 * std_error  # 95% CI

        lower_bounds = [v - margin for v in future_values]
        upper_bounds = [v + margin for v in future_values]

        date_range = pd.date_range(start=self.end_date, periods=periods + 1, freq="D")[1:]

        return (
            [str(d.date()) for d in date_range],
            future_values.tolist(),
            lower_bounds,
            upper_bounds,
        )


class MovingAverageForecaster:
    """Moving average with exponential smoothing."""

    def __init__(self, window: int = 7):
        self.window = window
        self.values = None
        self.end_date = None

    def fit(self, df: pd.DataFrame, datetime_col: str, target_col: str):
        try:
            working = df[[datetime_col, target_col]].copy()
            working[datetime_col] = pd.to_datetime(working[datetime_col], errors="coerce")
            working = working.dropna()

            if len(working) < self.window:
                self.window = max(2, len(working) // 2)

            working = working.sort_values(datetime_col).reset_index(drop=True)
            self.values = working[target_col].values.astype(float)
            self.end_date = working[datetime_col].max()
        except Exception as e:
            raise ForecastingModelError(f"Moving Average training failed: {str(e)}")

    def predict(self, periods: int = 12) -> tuple[list[str], list[float], list[float], list[float]]:
        if self.values is None:
            raise ForecastingModelError("Model not fitted")

        ma = float(np.mean(self.values[-self.window:]))
        trend = 0.0
        if len(self.values) >= 2:
            trend = float((self.values[-1] - self.values[-2]) / len(self.values) * 0.1)

        forecasts = [ma + trend * (i + 1) for i in range(periods)]

        # Estimate std for bounds
        std_error = float(np.std(self.values[-self.window:]))
        margin = 1.96 * std_error

        lower_bounds = [max(0, v - margin) for v in forecasts]
        upper_bounds = [v + margin for v in forecasts]

        date_range = pd.date_range(start=self.end_date, periods=periods + 1, freq="D")[1:]

        return (
            [str(d.date()) for d in date_range],
            forecasts,
            lower_bounds,
            upper_bounds,
        )


def train_model(
    df: pd.DataFrame,
    datetime_col: str,
    target_col: str,
) -> tuple[object, str]:
    """
    Train the best available forecasting model.
    Priority: Prophet > Linear Regression > Moving Average.
    Returns (fitted_model, model_name).
    """
    # Try Prophet if available
    if PROPHET_AVAILABLE:
        try:
            model = ProphetForecaster()
            model.fit(df, datetime_col, target_col)
            return model, "Prophet"
        except Exception:
            pass

    # Try Linear Regression
    try:
        model = LinearRegressionForecaster()
        model.fit(df, datetime_col, target_col)
        return model, "Linear Regression"
    except Exception:
        pass

    # Fall back to Moving Average
    try:
        model = MovingAverageForecaster()
        model.fit(df, datetime_col, target_col)
        return model, "Moving Average"
    except Exception as e:
        raise ForecastingModelError(f"All forecasting models failed: {str(e)}")
