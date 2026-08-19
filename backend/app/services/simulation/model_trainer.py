"""
Model Trainer — Module 8.

Trains Linear Regression and Random Forest models on a prepared feature
matrix, selects the better model by R², and returns a serialisable model
package used by the prediction and sensitivity engines.

Design decisions
----------------
- Both models are always trained so the caller receives comparative metrics.
- Random Forest is capped at max_depth=6, n_estimators=100 to stay fast on
  upload-size datasets (typically < 100k rows).
- Categorical columns are label-encoded; datetime columns are dropped (time-
  series forecasting lives in Module 5).
- The returned ModelPackage is a plain dataclass — nothing is persisted to
  disk; models are re-trained per-request (datasets are small, training is
  sub-second in practice).
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from app.core.logging import get_logger
from app.core.cache import TTLCache
from app.core.pandas_compat import TEXT_DTYPES

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

logger = get_logger(__name__)

# Minimum rows required for model training
_MIN_TRAIN_ROWS = 10


@dataclass
class ModelMetrics:
    r2: float
    rmse: float
    mae: float
    mape: Optional[float]

    def to_dict(self) -> dict:
        return {
            "r2": round(self.r2, 4),
            "rmse": round(self.rmse, 4),
            "mae": round(self.mae, 4),
            "mape": round(self.mape, 2) if self.mape is not None else None,
        }


@dataclass
class ModelPackage:
    """
    Trained model bundle returned by train_models().

    Contains the winning model plus both individual models so callers
    can present comparison metrics to users.
    """
    target_column: str
    feature_columns: list[str]
    selected_model_name: str        # "Linear Regression" or "Random Forest"
    selected_model: object          # sklearn estimator
    lr_model: LinearRegression
    rf_model: Optional[RandomForestRegressor]
    lr_metrics: ModelMetrics
    rf_metrics: Optional[ModelMetrics]
    encoders: dict[str, LabelEncoder] = field(default_factory=dict)
    feature_means: dict[str, float] = field(default_factory=dict)
    feature_stds: dict[str, float] = field(default_factory=dict)
    feature_mins: dict[str, float] = field(default_factory=dict)
    feature_maxs: dict[str, float] = field(default_factory=dict)
    rows_trained: int = 0
    train_r2: float = 0.0
    test_r2: float = 0.0

    def comparison(self) -> dict:
        return {
            "selected_model": self.selected_model_name,
            "linear_regression": self.lr_metrics.to_dict(),
            "random_forest": self.rf_metrics.to_dict() if self.rf_metrics else None,
            "rows_trained": self.rows_trained,
            "train_r2": round(self.train_r2, 4),
            "test_r2": round(self.test_r2, 4),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _encode(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, LabelEncoder]]:
    """Label-encode all object/category columns in-place."""
    out = df.copy()
    encoders: dict[str, LabelEncoder] = {}
    for col in out.select_dtypes(include=TEXT_DTYPES).columns:
        le = LabelEncoder()
        out[col] = le.fit_transform(out[col].astype(str))
        encoders[col] = le
    return out, encoders


def _mape(actual: np.ndarray, predicted: np.ndarray) -> Optional[float]:
    mask = actual != 0
    if not mask.any():
        return None
    return float(100.0 * np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])))


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> ModelMetrics:
    r2 = float(r2_score(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae_val = float(mean_absolute_error(y_true, y_pred))
    mape_val = _mape(y_true, y_pred)
    return ModelMetrics(r2=r2, rmse=rmse, mae=mae_val, mape=mape_val)


def _prepare(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: Optional[list[str]] = None,
) -> tuple[pd.DataFrame, pd.Series, list[str], dict[str, LabelEncoder]]:
    """
    Prepare feature matrix X and target series y.

    - Drops datetime columns (not suitable for regression features).
    - Label-encodes categoricals.
    - Drops rows with NaN in target or any feature.
    """
    # Drop datetime columns from features
    dt_cols = list(df.select_dtypes(include=["datetime", "datetimetz"]).columns)
    working = df.drop(columns=dt_cols, errors="ignore")

    target = working[target_column].copy()

    if feature_columns:
        available = [c for c in feature_columns if c in working.columns and c != target_column]
    else:
        available = [c for c in working.columns if c != target_column]

    if not available:
        raise ValueError(f"No usable feature columns found for target '{target_column}'")

    feature_df = working[available].copy()
    encoded_features, encoders = _encode(feature_df)

    # Align indices and drop NaN rows
    combined = encoded_features.copy()
    combined["__target__"] = target
    combined = combined.dropna()

    X = combined[available]
    y = combined["__target__"]

    return X, y, available, encoders


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def train_models(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: Optional[list[str]] = None,
    test_size: float = 0.2,
    random_state: int = 42,
) -> ModelPackage:
    """
    Train Linear Regression and Random Forest on the dataset.

    Selects the better model by test-set R². Returns a ModelPackage
    containing both models, their metrics, and feature metadata.

    Raises
    ------
    ValueError  if the target column is missing, no features are available,
                or there are fewer than _MIN_TRAIN_ROWS clean rows.
    """
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset")

    if not pd.api.types.is_numeric_dtype(df[target_column]):
        raise ValueError(f"Target column '{target_column}' must be numeric")

    X, y, feature_cols, encoders = _prepare(df, target_column, feature_columns)

    if len(X) < _MIN_TRAIN_ROWS:
        raise ValueError(
            f"Insufficient data: {len(X)} clean rows (need ≥ {_MIN_TRAIN_ROWS})"
        )

    # Gather feature stats for simulation bounds
    feature_means = {c: float(X[c].mean()) for c in feature_cols}
    feature_stds = {c: float(X[c].std()) if X[c].std() > 0 else 1.0 for c in feature_cols}
    feature_mins = {c: float(X[c].min()) for c in feature_cols}
    feature_maxs = {c: float(X[c].max()) for c in feature_cols}

    # Train/test split
    if len(X) >= 20:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
    else:
        # Too few rows for a split — evaluate on train set
        X_train, X_test, y_train, y_test = X, X, y, y

    # ── Linear Regression ─────────────────────────────────────
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_pred_test = lr.predict(X_test)
    lr_pred_train = lr.predict(X_train)
    lr_metrics = _metrics(y_test.values, lr_pred_test)

    # ── Random Forest ─────────────────────────────────────────
    rf: Optional[RandomForestRegressor] = None
    rf_metrics: Optional[ModelMetrics] = None

    if len(X_train) >= _MIN_TRAIN_ROWS:
        try:
            rf = RandomForestRegressor(
                n_estimators=100,
                max_depth=6,
                min_samples_leaf=2,
                random_state=random_state,
                n_jobs=-1,
            )
            rf.fit(X_train, y_train)
            rf_pred_test = rf.predict(X_test)
            rf_metrics = _metrics(y_test.values, rf_pred_test)
        except Exception as exc:
            logger.warning("rf_training_failed", error=str(exc))
            rf = None
            rf_metrics = None

    # ── Model selection ───────────────────────────────────────
    use_rf = (
        rf is not None
        and rf_metrics is not None
        and rf_metrics.r2 > lr_metrics.r2
    )

    selected_model = rf if use_rf else lr
    selected_name = "Random Forest" if use_rf else "Linear Regression"

    train_r2 = float(r2_score(y_train.values, selected_model.predict(X_train)))
    test_r2 = float(r2_score(y_test.values, selected_model.predict(X_test)))

    logger.info(
        "simulation_model_trained",
        target=target_column,
        selected=selected_name,
        test_r2=round(test_r2, 4),
        rows=len(X),
    )

    return ModelPackage(
        target_column=target_column,
        feature_columns=feature_cols,
        selected_model_name=selected_name,
        selected_model=selected_model,
        lr_model=lr,
        rf_model=rf,
        lr_metrics=lr_metrics,
        rf_metrics=rf_metrics,
        encoders=encoders,
        feature_means=feature_means,
        feature_stds=feature_stds,
        feature_mins=feature_mins,
        feature_maxs=feature_maxs,
        rows_trained=len(X),
        train_r2=train_r2,
        test_r2=test_r2,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cached entry point
# ─────────────────────────────────────────────────────────────────────────────
#
# train_models() above fits both a Linear Regression and a Random Forest
# from scratch -- the most expensive step in the What-If flow. Every
# simulation endpoint (/train, /single, /multi, /sensitivity, /compare)
# independently called train_models() with zero caching, so exploring a
# handful of scenarios for the same dataset retrained the model every
# single time. That's the same class of problem Root Cause Analysis had
# (see driver_detector.detect_drivers_cached) -- same fix here.
#
# This is also what makes a responsive slider-based "drag and see the
# prediction update" UI viable on the frontend: training happens once
# per (dataset, target, features) combination, and every subsequent
# prediction against the cached ModelPackage is just a fast
# .predict() call, not a full retrain.

_model_cache: TTLCache[ModelPackage] = TTLCache(max_size=32, ttl_seconds=300.0)


def train_models_cached(
    dataset_id: str,
    df: pd.DataFrame,
    target_column: str,
    feature_columns: Optional[list[str]] = None,
) -> ModelPackage:
    """
    Same contract as train_models(), cached per (dataset_id,
    target_column, feature_columns). Datasets are immutable once
    uploaded in this system, so dataset_id alone is safe cache-key
    material for content -- no need to hash the DataFrame itself.
    """
    features_key = tuple(sorted(feature_columns)) if feature_columns else None
    cache_key = (str(dataset_id), target_column, features_key)
    return _model_cache.get_or_compute(
        cache_key, lambda: train_models(df, target_column, feature_columns)
    )


def invalidate_model_cache(dataset_id: str) -> None:
    """Called on dataset delete so a cached model can never outlive the
    dataset it was trained on."""
    _model_cache.delete_prefix(f"('{dataset_id}'")
