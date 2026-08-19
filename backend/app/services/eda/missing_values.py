import pandas as pd


def missing_values(df: pd.DataFrame) -> dict:
    """
    Analyze missing values in the dataset.

    Returns:
        - Missing count per column
        - Missing percentage
        - Total missing cells
        - Columns containing missing values
        - Complete columns
        - Dataset completeness
    """

    total_rows = len(df)
    total_columns = len(df.columns)
    total_cells = total_rows * total_columns

    columns = {}

    columns_with_missing = []
    complete_columns = []

    total_missing = 0

    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        total_missing += missing_count

        missing_percentage = (
            round((missing_count / total_rows) * 100, 2)
            if total_rows > 0
            else 0.0
        )

        columns[column] = {
            "missing_count": missing_count,
            "missing_percentage": missing_percentage,
            "is_complete": missing_count == 0,
        }

        if missing_count == 0:
            complete_columns.append(column)
        else:
            columns_with_missing.append(column)

    completeness_percentage = (
        round(
            ((total_cells - total_missing) / total_cells) * 100,
            2,
        )
        if total_cells > 0
        else 100.0
    )

    return {
        "dataset": {
            "rows": total_rows,
            "columns": total_columns,
            "total_cells": total_cells,
            "total_missing_cells": total_missing,
            "dataset_completeness": completeness_percentage,
        },
        "summary": {
            "columns_with_missing": len(columns_with_missing),
            "complete_columns": len(complete_columns),
            "missing_columns": columns_with_missing,
            "complete_column_names": complete_columns,
        },
        "columns": columns,
    }