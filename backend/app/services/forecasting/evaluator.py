"""
Compute evaluation metrics: RMSE, MAE, MAPE.
"""
import numpy as np


def rmse(actual: list[float] | np.ndarray, predicted: list[float] | np.ndarray) -> float:
    """Root Mean Squared Error."""
    actual = np.array(actual)
    predicted = np.array(predicted)
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def mae(actual: list[float] | np.ndarray, predicted: list[float] | np.ndarray) -> float:
    """Mean Absolute Error."""
    actual = np.array(actual)
    predicted = np.array(predicted)
    return float(np.mean(np.abs(actual - predicted)))


def mape(actual: list[float] | np.ndarray, predicted: list[float] | np.ndarray) -> float:
    """Mean Absolute Percentage Error."""
    actual = np.array(actual)
    predicted = np.array(predicted)

    mask = actual != 0
    if not mask.any():
        return 0.0

    return float(100.0 * np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])))


def evaluate_model(
    actual: list[float] | np.ndarray,
    predicted: list[float] | np.ndarray,
) -> dict:
    """Compute all evaluation metrics."""
    return {
        "rmse": round(rmse(actual, predicted), 4),
        "mae": round(mae(actual, predicted), 4),
        "mape": round(mape(actual, predicted), 2),
    }


def backtest_model(model, df: object, datetime_col: str, target_col: str) -> dict:
    """Simple backtest: 80% train, 20% test."""
    cutoff_idx = int(len(df) * 0.8)
    train_df = df.iloc[:cutoff_idx]
    test_df = df.iloc[cutoff_idx:]

    if len(test_df) < 1:
        return {"rmse": None, "mae": None, "mape": None}

    try:
        model.fit(train_df, datetime_col, target_col)
        _, predictions, _, _ = model.predict(len(test_df))
        actual_values = test_df[target_col].values.tolist()

        return evaluate_model(actual_values, predictions)
    except Exception:
        return {"rmse": None, "mae": None, "mape": None}
