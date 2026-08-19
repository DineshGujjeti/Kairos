"""
Feature 3: Ranking Engine.

"Top Products by Revenue" = rank(df, dimension="product_name",
metric="revenue", top_n=10, aggregation="sum"). Validates both column
names and the metric's type up front so a bad request produces a clear
404/422 (via the domain exceptions below, mapped centrally in
app/main.py) instead of a pandas KeyError/TypeError surfacing as a
raw 500.
"""
import pandas as pd

from app.core.exceptions import ColumnNotFoundError, InvalidColumnTypeError, InvalidParameterError

VALID_AGGREGATIONS = ("sum", "mean", "count", "min", "max")


def rank(
    df: pd.DataFrame,
    dimension: str,
    metric: str,
    top_n: int = 10,
    aggregation: str = "sum",
) -> dict:
    if dimension not in df.columns:
        raise ColumnNotFoundError(dimension)
    if metric not in df.columns:
        raise ColumnNotFoundError(metric)
    if not pd.api.types.is_numeric_dtype(df[metric]):
        raise InvalidColumnTypeError(metric, expected="numeric")
    if aggregation not in VALID_AGGREGATIONS:
        raise InvalidParameterError(
            f"aggregation must be one of {VALID_AGGREGATIONS}, got '{aggregation}'"
        )
    if top_n < 1:
        raise InvalidParameterError("top_n must be at least 1")

    grouped = df.groupby(dimension)[metric].agg(aggregation).sort_values(ascending=False)
    total = float(df[metric].sum()) if aggregation == "sum" else None

    top = grouped.head(top_n)

    items = []
    for name, value in top.items():
        value_f = float(value) if pd.notna(value) else None
        item = {
            "dimension_value": str(name),
            "metric_value": round(value_f, 4) if value_f is not None else None,
        }
        if total and value_f is not None:
            item["percentage_of_total"] = round((value_f / total) * 100, 2)
        else:
            item["percentage_of_total"] = None
        items.append(item)

    return {
        "dimension": dimension,
        "metric": metric,
        "aggregation": aggregation,
        "top_n": top_n,
        "total_groups": int(df[dimension].nunique(dropna=True)),
        "items": items,
    }
