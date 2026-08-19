import pandas as pd


def quality(df: pd.DataFrame) -> dict:
    """
    Evaluate the overall quality of the dataset.

    Quality is calculated using four metrics:

    1. Completeness
    2. Uniqueness
    3. Duplicate Score
    4. Consistency

    Returns an overall quality score (0-100).
    """

    total_rows = len(df)
    total_columns = len(df.columns)

    total_cells = total_rows * total_columns

    missing_cells = int(df.isna().sum().sum())

    duplicate_rows = int(df.duplicated().sum())

    # -----------------------------
    # Completeness
    # -----------------------------
    completeness = (
        ((total_cells - missing_cells) / total_cells) * 100
        if total_cells > 0
        else 100.0
    )

    # -----------------------------
    # Duplicate Score
    # -----------------------------
    duplicate_score = (
        ((total_rows - duplicate_rows) / total_rows) * 100
        if total_rows > 0
        else 100.0
    )

    # -----------------------------
    # Uniqueness
    # -----------------------------
    uniqueness_scores = []

    for column in df.columns:
        uniqueness = (
            (df[column].nunique(dropna=True) / total_rows) * 100
            if total_rows > 0
            else 100.0
        )

        uniqueness_scores.append(uniqueness)

    uniqueness_score = (
        sum(uniqueness_scores) / len(uniqueness_scores)
        if uniqueness_scores
        else 100.0
    )

    # -----------------------------
    # Consistency
    # -----------------------------
    inconsistent_columns = 0

    for column in df.columns:
        non_null = df[column].dropna()

        if non_null.empty:
            continue

        inferred = pd.api.types.infer_dtype(non_null)

        if inferred in (
            "mixed",
            "mixed-integer",
            "mixed-integer-float",
        ):
            inconsistent_columns += 1

    consistency_score = (
        ((total_columns - inconsistent_columns) / total_columns) * 100
        if total_columns > 0
        else 100.0
    )

    # -----------------------------
    # Overall Score
    # -----------------------------
    overall_score = round(
        (
            completeness
            + duplicate_score
            + uniqueness_score
            + consistency_score
        )
        / 4,
        2,
    )

    # -----------------------------
    # Rating
    # -----------------------------
    if overall_score >= 90:
        rating = "Excellent"
    elif overall_score >= 75:
        rating = "Good"
    elif overall_score >= 60:
        rating = "Fair"
    else:
        rating = "Poor"

    return {
        "quality_score": overall_score,
        "rating": rating,
        "metrics": {
            "completeness": round(completeness, 2),
            "duplicate_score": round(duplicate_score, 2),
            "uniqueness_score": round(uniqueness_score, 2),
            "consistency_score": round(consistency_score, 2),
        },
        "summary": {
            "rows": total_rows,
            "columns": total_columns,
            "total_cells": total_cells,
            "missing_cells": missing_cells,
            "duplicate_rows": duplicate_rows,
            "inconsistent_columns": inconsistent_columns,
        },
    }