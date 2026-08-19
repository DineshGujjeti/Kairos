import pandas as pd


def outliers(df: pd.DataFrame) -> dict:
    """
    Detect outliers in numeric columns using the IQR method.

    Returns:
        - Q1
        - Q3
        - IQR
        - Lower bound
        - Upper bound
        - Outlier count
        - Outlier percentage
        - Outlier row indices
    """

    numeric_df = df.select_dtypes(include="number")

    if numeric_df.empty:
        return {
            "total_numeric_columns": 0,
            "columns_with_outliers": 0,
            "column_names_with_outliers": [],
            "total_outliers": 0,
            "columns": {},
        }

    results = {}

    total_rows = len(df)

    for column in numeric_df.columns:
        series = numeric_df[column].dropna()

        if series.empty:
            results[column] = {
                "q1": None,
                "q3": None,
                "iqr": None,
                "lower_bound": None,
                "upper_bound": None,
                "outlier_count": 0,
                "outlier_percentage": 0.0,
                "outlier_indices": [],
            }
            continue

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1

        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        mask = (df[column] < lower_bound) | (df[column] > upper_bound)

        outlier_indices = df.index[mask].tolist()
        outlier_count = len(outlier_indices)

        outlier_percentage = (
            round((outlier_count / total_rows) * 100, 2)
            if total_rows > 0
            else 0.0
        )

        results[column] = {
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
            "lower_bound": round(lower_bound, 4),
            "upper_bound": round(upper_bound, 4),
            "outlier_count": outlier_count,
            "outlier_percentage": outlier_percentage,
            "outlier_indices": outlier_indices,
        }

    total_outliers = sum(
        column["outlier_count"]
        for column in results.values()
    )

    columns_with_outliers = [
        column
        for column, data in results.items()
        if data["outlier_count"] > 0
    ]

    return {
        "total_numeric_columns": len(results),
        "columns_with_outliers": len(columns_with_outliers),
        "column_names_with_outliers": columns_with_outliers,
        "total_outliers": total_outliers,
        "columns": results,
    }