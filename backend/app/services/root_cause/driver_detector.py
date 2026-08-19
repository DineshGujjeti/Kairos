"""
Driver Detector — Module 7.

Identifies which variables most strongly drive a target metric using three
complementary methods, then synthesises them into a ranked list of drivers
with confidence scores grounded in agreement across methods.

Methods (selected automatically based on dataset characteristics):
  1. Pearson / Spearman correlation  — always computed
  2. Mutual Information              — always computed (captures nonlinear)
  3. Random Forest feature importance — computed when ≥ 20 rows
"""
from __future__ import annotations

import warnings
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.preprocessing import LabelEncoder

from app.core.logging import get_logger
from app.core.cache import TTLCache
from app.core.pandas_compat import TEXT_DTYPES

logger = get_logger(__name__)

# Suppress sklearn convergence / UndefinedMetricWarning in tests
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Label-encode all object/categorical columns so they can be used in models."""
    out = df.copy()
    le = LabelEncoder()
    for col in out.select_dtypes(include=TEXT_DTYPES).columns:
        out[col] = le.fit_transform(out[col].astype(str))
    return out


def _pearson_drivers(feature_df: pd.DataFrame, target: pd.Series) -> dict[str, float]:
    """Return Pearson correlations between every feature column and the target."""
    results: dict[str, float] = {}
    for col in feature_df.columns:
        s = feature_df[col].dropna()
        t = target.loc[s.index].dropna()
        idx = s.index.intersection(t.index)
        if len(idx) < 5:
            continue
        try:
            r = float(np.corrcoef(s.loc[idx].values, t.loc[idx].values)[0, 1])
            if not np.isnan(r):
                results[col] = round(r, 4)
        except Exception:
            pass
    return results


def _mutual_info_drivers(feature_df: pd.DataFrame, target: pd.Series) -> dict[str, float]:
    """Return normalised mutual information scores (0-1)."""
    results: dict[str, float] = {}
    valid_idx = target.dropna().index
    X = feature_df.loc[valid_idx].fillna(0)
    y = target.loc[valid_idx]
    if X.empty or len(X) < 5:
        return results
    try:
        mi = mutual_info_regression(X, y, random_state=42)
        total = mi.sum() or 1.0
        for col, score in zip(feature_df.columns, mi):
            results[col] = round(float(score / total), 4)
    except Exception as exc:
        logger.warning("mi_driver_failed", error=str(exc))
    return results


def _rf_drivers(feature_df: pd.DataFrame, target: pd.Series) -> dict[str, float]:
    """Return Random Forest feature importances (0-1, summing to 1)."""
    results: dict[str, float] = {}
    valid_idx = target.dropna().index
    X = feature_df.loc[valid_idx].fillna(0)
    y = target.loc[valid_idx]
    if len(X) < 20:
        return results
    try:
        rf = RandomForestRegressor(
            n_estimators=50,
            max_depth=5,
            random_state=42,
            n_jobs=-1,
        )
        rf.fit(X, y)
        for col, imp in zip(feature_df.columns, rf.feature_importances_):
            results[col] = round(float(imp), 4)
    except Exception as exc:
        logger.warning("rf_driver_failed", error=str(exc))
    return results


def _confidence(pearson: float, mi: float, rf: Optional[float]) -> str:
    """
    Derive confidence from method agreement.

    High   — all available methods agree (all signal > 0.2)
    Medium — most methods agree
    Low    — weak or conflicting signals
    """
    signals = [abs(pearson)]
    if mi is not None:
        signals.append(mi)
    if rf is not None:
        signals.append(rf)
    strong = sum(1 for s in signals if s >= 0.2)
    if strong == len(signals) and len(signals) >= 2:
        return "High"
    if strong >= 1:
        return "Medium"
    return "Low"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def detect_drivers(
    df: pd.DataFrame,
    target_column: str,
    top_n: int = 8,
) -> dict:
    """
    Identify the top drivers of *target_column* using three methods:
    correlation, mutual information, and Random Forest importance.

    Returns a driver report dict suitable for AI prompts and API responses.
    """
    if target_column not in df.columns:
        return {
            "target_column": target_column,
            "error": f"Column '{target_column}' not found",
            "drivers": [],
        }

    target = df[target_column].dropna()
    if len(target) < 5:
        return {
            "target_column": target_column,
            "error": "Insufficient data (< 5 rows) for driver analysis",
            "drivers": [],
        }

    # Build numeric feature matrix excluding the target
    encoded = _encode_categoricals(df.drop(columns=[target_column], errors="ignore"))
    feature_df = encoded.select_dtypes(include="number").dropna(axis=1, how="all")

    if feature_df.empty:
        return {
            "target_column": target_column,
            "error": "No usable feature columns after encoding",
            "drivers": [],
        }

    # Run all methods
    pearson = _pearson_drivers(feature_df, target)
    mi = _mutual_info_drivers(feature_df, target)
    rf = _rf_drivers(feature_df, target) if len(df) >= 20 else {}

    # Synthesise into ranked driver list
    all_cols = set(pearson) | set(mi) | set(rf)
    raw_drivers: list[dict] = []

    for col in all_cols:
        p = pearson.get(col, 0.0)
        m = mi.get(col, 0.0)
        r = rf.get(col) if rf else None

        # Composite importance: weighted average of available signals
        weights, values = [1.0, 1.0], [abs(p), m]
        if r is not None:
            weights.append(1.5)
            values.append(r)
        composite = float(np.average(values, weights=weights))

        raw_drivers.append({
            "column": col,
            "importance": round(composite, 4),
            "pearson_correlation": round(p, 4),
            "mutual_information": round(m, 4),
            "rf_importance": round(r, 4) if r is not None else None,
            "direction": "positive" if p >= 0 else "negative",
            "confidence": _confidence(p, m, r),
        })

    raw_drivers.sort(key=lambda x: -x["importance"])
    top_drivers = raw_drivers[:top_n]

    # Normalise importance to percentage contributions
    total_imp = sum(d["importance"] for d in top_drivers) or 1.0
    for d in top_drivers:
        d["contribution_pct"] = round(d["importance"] / total_imp * 100, 1)

    return {
        "target_column": target_column,
        "rows_analysed": len(target),
        "methods_used": ["correlation"] + (["mutual_information"] if mi else []) + (["random_forest"] if rf else []),
        "total_features_evaluated": len(all_cols),
        "top_drivers": top_drivers,
        "positive_drivers": [d for d in top_drivers if d["direction"] == "positive"][:5],
        "negative_drivers": [d for d in top_drivers if d["direction"] == "negative"][:5],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Cached entry point
# ─────────────────────────────────────────────────────────────────────────────
#
# detect_drivers() above trains a RandomForestRegressor and runs
# mutual_info_regression from scratch on every call -- the single most
# expensive step in Root Cause Analysis. The frontend calls both
# `/root-cause` and `/drivers` for the same dataset+target on a single
# page load, and a user re-opening the same analysis minutes later would
# otherwise pay full retraining cost again for identical input.
#
# detect_drivers() itself stays a pure, uncached function (existing
# tests call it directly and depend on that); this wrapper is the
# caching entry point every route/orchestrator should use instead.

_driver_cache: TTLCache[dict] = TTLCache(max_size=64, ttl_seconds=300.0)


def detect_drivers_cached(
    dataset_id: str,
    df: pd.DataFrame,
    target_column: str,
    top_n: int = 8,
) -> dict:
    """
    Same contract as detect_drivers(), cached per (dataset_id,
    target_column, top_n). Datasets are immutable once uploaded in this
    system (a re-upload gets a new id), so dataset_id alone is a safe
    cache key for content -- no need to hash the DataFrame itself.
    """
    cache_key = (str(dataset_id), target_column, top_n)
    return _driver_cache.get_or_compute(cache_key, lambda: detect_drivers(df, target_column, top_n))


def invalidate_driver_cache(dataset_id: str) -> None:
    """Called on dataset delete so a cached driver report can never
    outlive the dataset it was computed from."""
    _driver_cache.delete_prefix(f"('{dataset_id}'")
