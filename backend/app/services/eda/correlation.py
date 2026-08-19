from itertools import combinations

import pandas as pd


def correlation(
    df: pd.DataFrame,
    method: str = "pearson",
    threshold: float = 0.8,
) -> dict:
    """
    Perform correlation analysis on numeric columns.

    Returns:
        - Correlation matrix
        - Highly correlated feature pairs
        - Strongest positive correlations
        - Strongest negative correlations
    """

    numeric_df = df.select_dtypes(include="number")

    if numeric_df.shape[1] < 2:
        return {
            "method": method,
            "threshold": threshold,
            "total_numeric_columns": numeric_df.shape[1],
            "correlation_matrix": {},
            "highly_correlated_pairs": [],
            "strongest_positive": [],
            "strongest_negative": [],
        }

    corr_matrix = numeric_df.corr(method=method)

    matrix = {
        row: {
            col: (
                round(float(value), 4)
                if not pd.isna(value)
                else None
            )
            for col, value in corr_matrix.loc[row].items()
        }
        for row in corr_matrix.index
    }

    pairs = []

    for col1, col2 in combinations(corr_matrix.columns, 2):
        value = corr_matrix.loc[col1, col2]

        if pd.isna(value):
            continue

        pairs.append(
            {
                "column_1": col1,
                "column_2": col2,
                "correlation": round(float(value), 4),
                "absolute_correlation": round(abs(float(value)), 4),
            }
        )

    pairs.sort(
        key=lambda x: x["absolute_correlation"],
        reverse=True,
    )

    highly_correlated = [
        pair
        for pair in pairs
        if pair["absolute_correlation"] >= threshold
    ]

    positive = sorted(
        [p for p in pairs if p["correlation"] > 0],
        key=lambda x: x["correlation"],
        reverse=True,
    )[:10]

    negative = sorted(
        [p for p in pairs if p["correlation"] < 0],
        key=lambda x: x["correlation"],
    )[:10]

    return {
        "method": method,
        "threshold": threshold,
        "total_numeric_columns": numeric_df.shape[1],
        "correlation_matrix": matrix,
        "highly_correlated_pairs": highly_correlated,
        "strongest_positive": positive,
        "strongest_negative": negative,
    }