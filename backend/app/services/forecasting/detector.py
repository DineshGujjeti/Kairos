"""
Smart auto-detection of datetime and numeric target columns for forecasting.
Recognizes common enterprise naming patterns.
"""
import pandas as pd

from app.core.exceptions import (
    InsufficientDataError,
    NoDatetimeColumnError,
    NoNumericColumnsError,
)
from app.core.pandas_compat import is_text_dtype


# Common datetime column names in enterprise datasets
DATETIME_PATTERNS = [
    "date",
    "datetime",
    "timestamp",
    "order_date",
    "invoice_date",
    "transaction_date",
    "purchase_date",
    "sales_date",
    "pickup",
    "dropoff",
    "created_at",
    "updated_at",
    "ds",
    "time",
    "period",
    "day",
    "month",
    "year",
]

# Common target column names in enterprise datasets
TARGET_PATTERNS = [
    "sales",
    "revenue",
    "amount",
    "total",
    "profit",
    "income",
    "quantity",
    "demand",
    "orders",
    "cost",
    "expense",
    "y",
    "value",
    "price",
    "count",
]


def _score_column_name(col_name: str, patterns: list[str]) -> float:
    """Score how well a column name matches patterns (0-1)."""
    col_lower = col_name.lower()
    
    for pattern in patterns:
        if col_lower == pattern:
            return 1.0
        if pattern in col_lower or col_lower in pattern:
            return 0.8
    
    return 0.0


def detect_datetime_column(df: pd.DataFrame) -> str | None:
    """
    Returns the name of a datetime column if one exists, None otherwise.
    Strategy: 
    1. Check for native datetime types (high priority)
    2. Check column names against DATETIME_PATTERNS
    3. Try parsing object columns (>90% success rate)
    """
    candidates = []
    
    # Check native datetime types
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            score = _score_column_name(column, DATETIME_PATTERNS)
            candidates.append((column, 1.0 + score, "native_type"))
    
    # Check column names
    for column in df.columns:
        if not is_text_dtype(df[column]):
            continue
        score = _score_column_name(column, DATETIME_PATTERNS)
        if score > 0.5:
            candidates.append((column, score, "name_pattern"))
    
    # Try parsing text columns (covers both legacy `object` and the
    # pandas-3 default `str` dtype -- see app.core.pandas_compat)
    for column in df.columns:
        if not is_text_dtype(df[column]):
            continue
        sample = df[column].dropna().head(50)
        if sample.empty:
            continue
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        success_rate = parsed.notna().sum() / len(sample)
        if success_rate >= 0.9:
            score = _score_column_name(column, DATETIME_PATTERNS)
            candidates.append((column, success_rate + score, "parse_success"))
    
    if not candidates:
        return None
    
    # Return highest scoring candidate
    candidates.sort(key=lambda x: -x[1])
    return candidates[0][0]


def detect_target_column(df: pd.DataFrame, exclude: list[str] | None = None) -> str:
    """
    Returns the name of a numeric column suitable for forecasting.
    Strategy:
    1. Score all numeric columns against TARGET_PATTERNS
    2. Return highest scoring column
    3. Fall back to first numeric column if no matches
    """
    if exclude is None:
        exclude = []
    
    numeric_cols = [
        col for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col]) and col not in exclude
    ]
    
    if not numeric_cols:
        raise NoNumericColumnsError()
    
    # Score each numeric column
    candidates = []
    for col in numeric_cols:
        score = _score_column_name(col, TARGET_PATTERNS)
        candidates.append((col, score))
    
    # Sort by score (descending)
    candidates.sort(key=lambda x: -x[1])
    
    # Return highest score or first numeric if no pattern matches
    if candidates[0][1] > 0:
        return candidates[0][0]
    
    return numeric_cols[0]


def validate_datetime_column(df: pd.DataFrame, datetime_column: str) -> None:
    """Validate that a datetime column is usable for forecasting."""
    if datetime_column not in df.columns:
        raise NoDatetimeColumnError()
    
    # Try to parse as datetime
    try:
        parsed = pd.to_datetime(df[datetime_column], errors="coerce", format="mixed")
    except Exception:
        raise NoDatetimeColumnError()
    
    # Check success rate
    success_rate = parsed.notna().sum() / len(df)
    if success_rate < 0.5:
        raise NoDatetimeColumnError()
    
    # Check for duplicate timestamps
    unique_timestamps = parsed.dropna().nunique()
    if unique_timestamps < len(df) * 0.5:
        raise Exception("Too many duplicate timestamps in datetime column")


def validate_target_column(df: pd.DataFrame, target_column: str) -> None:
    """Validate that a target column is usable for forecasting."""
    if target_column not in df.columns:
        raise NoNumericColumnsError()
    
    if not pd.api.types.is_numeric_dtype(df[target_column]):
        raise NoNumericColumnsError()
    
    # Check for constant values
    non_null = df[target_column].dropna()
    if len(non_null) > 0:
        if non_null.std() == 0:
            raise Exception("Target column has constant values (no variance for forecasting)")
    
    # Check missing value rate
    missing_rate = df[target_column].isna().sum() / len(df)
    if missing_rate > 0.5:
        raise Exception("Target column has > 50% missing values")


def validate_for_forecasting(
    df: pd.DataFrame,
    datetime_column: str | None = None,
    target_column: str | None = None,
) -> tuple[str, str, bool, bool]:
    """
    Validates and detects columns for forecasting.
    Returns (datetime_column, target_column, auto_datetime, auto_target).
    auto_datetime/auto_target indicate whether auto-detection was used.
    """
    auto_datetime = False
    auto_target = False
    
    # Detect datetime column
    if datetime_column is None:
        datetime_column = detect_datetime_column(df)
        if datetime_column is None:
            raise NoDatetimeColumnError()
        auto_datetime = True
    else:
        validate_datetime_column(df, datetime_column)
    
    # Detect target column
    if target_column is None:
        target_column = detect_target_column(df, exclude=[datetime_column])
        auto_target = True
    else:
        validate_target_column(df, target_column)
    
    # Validate minimum rows
    if len(df) < 10:
        raise InsufficientDataError(required=10, actual=len(df))
    
    return datetime_column, target_column, auto_datetime, auto_target


# ─────────────────────────────────────────────────────────────────────────────
# Graceful degradation for datasets with no usable datetime column
# ─────────────────────────────────────────────────────────────────────────────
#
# Previously, any dataset without an obviously-named or parseable date
# column made the entire forecasting module unusable -- validate_for_
# forecasting() raised NoDatetimeColumnError, which propagated all the
# way to a bare HTTP 422 with no fallback. That's the right behaviour
# for a dataset that genuinely can't be forecast (e.g. 3 rows, no
# numeric columns at all), but it's needlessly hard-fail for something
# like an HR headcount table or a product catalogue that has a natural
# row order but no date column -- there's still a valid trend to detect
# against that sequence, it's just not calendar time.
#
# SYNTHETIC_DATETIME_COLUMN is injected as an evenly-spaced daily series
# anchored at a fixed epoch (not "now") so results are reproducible
# across repeated calls within the same request (see orchestrator.py,
# which may call validate_for_forecasting-derived logic more than once
# per report) and across test runs.

SYNTHETIC_DATETIME_COLUMN = "__row_sequence__"
_SYNTHETIC_ANCHOR = pd.Timestamp("2000-01-01")


def build_synthetic_datetime_column(df: pd.DataFrame) -> pd.Series:
    """One synthetic timestamp per row, evenly spaced, in the dataset's
    existing row order. Used only when no real datetime column exists."""
    return pd.Series(
        pd.date_range(start=_SYNTHETIC_ANCHOR, periods=len(df), freq="D"),
        index=df.index,
    )


def safe_validate_for_forecasting(
    df: pd.DataFrame,
    datetime_column: str | None = None,
    target_column: str | None = None,
    allow_synthetic_datetime: bool = True,
) -> dict:
    """
    Non-raising counterpart to validate_for_forecasting().

    Returns a dict with:
        available            bool -- True if forecasting can proceed
        datetime_column       str | None
        target_column         str | None
        datetime_auto_detected bool
        target_auto_detected  bool
        synthetic_datetime    bool -- True if datetime_column is a
                               row-order stand-in, not a real date
        unavailable_reason    str | None -- set only when available=False,
                               written for direct display in the UI

    Never raises. This is what forecasting/orchestrator.py should call
    instead of validate_for_forecasting() directly, so "no date column"
    or "too little data" degrade to a friendly, structured response
    instead of an HTTP 422.
    """
    try:
        dt_col, tgt_col, auto_dt, auto_tgt = validate_for_forecasting(
            df, datetime_column, target_column
        )
        return {
            "available": True,
            "datetime_column": dt_col,
            "target_column": tgt_col,
            "datetime_auto_detected": auto_dt,
            "target_auto_detected": auto_tgt,
            "synthetic_datetime": False,
            "unavailable_reason": None,
        }
    except NoDatetimeColumnError:
        if not allow_synthetic_datetime or datetime_column is not None:
            # A specific column was requested and still failed validation
            # some other way, or synthetic fallback was explicitly
            # disabled -- don't silently substitute in that case.
            return {
                "available": False,
                "datetime_column": None,
                "target_column": None,
                "datetime_auto_detected": False,
                "target_auto_detected": False,
                "synthetic_datetime": False,
                "unavailable_reason": (
                    "No date or time column was detected in this dataset. "
                    "Forecasting needs a column representing when each row "
                    "occurred."
                ),
            }
        # Fall back to a row-order sequence in place of a real date axis,
        # provided there's at least one usable numeric target and enough
        # rows to make a trend meaningful. Prefer dataset_intelligence's
        # ranked target_candidates over detect_target_column's cruder
        # "first numeric column" fallback here, since without a
        # name-pattern match detect_target_column can't tell an id-like
        # column (employee_id) from an actual measure (salary) -- the
        # profiler's id/measure role classification can.
        if target_column:
            tgt_col = target_column
        else:
            from app.services.dataset_intelligence import profile_dataset
            profile = profile_dataset(df)
            candidates = profile.get("target_candidates") or profile.get("primary_measures") or []
            if candidates:
                tgt_col = candidates[0]
            else:
                try:
                    tgt_col = detect_target_column(df, exclude=[])
                except NoNumericColumnsError:
                    return {
                        "available": False,
                        "datetime_column": None,
                        "target_column": None,
                        "datetime_auto_detected": False,
                        "target_auto_detected": False,
                        "synthetic_datetime": False,
                        "unavailable_reason": (
                            "No date/time column and no numeric column were found "
                            "in this dataset, so there is nothing to forecast."
                        ),
                    }
        if len(df) < 10:
            return {
                "available": False,
                "datetime_column": None,
                "target_column": None,
                "datetime_auto_detected": False,
                "target_auto_detected": False,
                "synthetic_datetime": False,
                "unavailable_reason": (
                    f"No date column was found, and there are only {len(df)} "
                    f"rows (at least 10 are needed) to build a sequence-based "
                    f"forecast instead."
                ),
            }
        return {
            "available": True,
            "datetime_column": SYNTHETIC_DATETIME_COLUMN,
            "target_column": tgt_col,
            "datetime_auto_detected": True,
            "target_auto_detected": target_column is None,
            "synthetic_datetime": True,
            "unavailable_reason": None,
        }
    except (NoNumericColumnsError, InsufficientDataError) as exc:
        reason = (
            "No numeric column suitable for forecasting was found in this dataset."
            if isinstance(exc, NoNumericColumnsError)
            else f"Not enough data to forecast reliably -- found {len(df)} rows, need at least 10."
        )
        return {
            "available": False,
            "datetime_column": None,
            "target_column": None,
            "datetime_auto_detected": False,
            "target_auto_detected": False,
            "synthetic_datetime": False,
            "unavailable_reason": reason,
        }
