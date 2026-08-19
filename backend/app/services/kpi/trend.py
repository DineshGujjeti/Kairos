"""
Feature 4: Trend Engine.

Auto-detects datetime columns rather than requiring the caller to know
the schema. A column already typed as datetime is an obvious match;
an object column is also accepted if a high proportion of its
non-null values successfully parse as dates -- guards against false
positives on a free-text column that just happens to contain a date
somewhere in it.

Per the spec, a dataset with no datetime column returns a meaningful
response (has_datetime_column: False + a message), not an error. Every
branch below returns the exact same set of keys -- learned from the
Module 3 review: an early-return path with a *different* shape than
the normal path breaks strict response validation the moment real data
hits the smaller branch.
"""
import pandas as pd

from app.core.exceptions import ColumnNotFoundError, InvalidColumnTypeError, InvalidParameterError
from app.core.pandas_compat import is_text_dtype

FREQUENCY_MAP = {
    "daily": "D",
    "weekly": "W",
    "monthly": "MS",
    "yearly": "YS",
}


def detect_datetime_columns(df: pd.DataFrame) -> list[str]:
    detected = []
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            detected.append(column)
            continue
        if is_text_dtype(df[column]):
            sample = df[column].dropna().head(50)
            if sample.empty:
                continue
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
            success_rate = parsed.notna().sum() / len(sample)
            if success_rate >= 0.9:
                detected.append(column)
    return detected


def trend(
    df: pd.DataFrame,
    metric: str | None = None,
    frequency: str = "monthly",
    datetime_column: str | None = None,
) -> dict:
    if frequency not in FREQUENCY_MAP:
        raise InvalidParameterError(
            f"frequency must be one of {list(FREQUENCY_MAP)}, got '{frequency}'"
        )

    datetime_columns = detect_datetime_columns(df)

    if not datetime_columns:
        return {
            "has_datetime_column": False,
            "message": "No datetime column was detected in this dataset, so a trend analysis could not be generated.",
            "detected_datetime_columns": [],
            "datetime_column_used": None,
            "frequency": frequency,
            "metric": metric,
            "points": [],
        }

    if datetime_column is not None:
        if datetime_column not in datetime_columns:
            raise InvalidColumnTypeError(datetime_column, expected="datetime")
        selected_column = datetime_column
    else:
        selected_column = datetime_columns[0]

    if metric is not None:
        if metric not in df.columns:
            raise ColumnNotFoundError(metric)
        if not pd.api.types.is_numeric_dtype(df[metric]):
            raise InvalidColumnTypeError(metric, expected="numeric")

    columns_to_keep = [selected_column] + ([metric] if metric and metric != selected_column else [])
    working = df[columns_to_keep].copy()
    working[selected_column] = pd.to_datetime(
        working[selected_column], errors="coerce", format="mixed"
    )
    working = working.dropna(subset=[selected_column])

    if working.empty:
        return {
            "has_datetime_column": True,
            "message": f"Column '{selected_column}' was detected as a datetime column but contained no parseable values.",
            "detected_datetime_columns": datetime_columns,
            "datetime_column_used": selected_column,
            "frequency": frequency,
            "metric": metric,
            "points": [],
        }

    working = working.set_index(selected_column).sort_index()

    if metric:
        series = working[metric].resample(FREQUENCY_MAP[frequency]).sum()
    else:
        series = working.resample(FREQUENCY_MAP[frequency]).size()

    points = [
        {
            "period": str(period.date()),
            "value": round(float(value), 4) if pd.notna(value) else None,
        }
        for period, value in series.items()
    ]

    return {
        "has_datetime_column": True,
        "message": None,
        "detected_datetime_columns": datetime_columns,
        "datetime_column_used": selected_column,
        "frequency": frequency,
        "metric": metric or "row_count",
        "points": points,
    }
