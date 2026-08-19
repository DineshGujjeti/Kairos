import pandas as pd


def distribution(df: pd.DataFrame) -> dict:
    """
    Analyze the statistical distribution of numeric columns.

    Returns:
        - Mean
        - Median
        - Mode
        - Variance
        - Standard Deviation
        - Skewness
        - Kurtosis
        - Range
        - Minimum
        - Maximum
        - Unique Values
        - Zero Count
        - Negative Count
        - Coefficient of Variation
    """

    numeric_df = df.select_dtypes(include="number")

    if numeric_df.empty:
        return {
            "total_numeric_columns": 0,
            "columns": {},
        }

    results = {}

    for column in numeric_df.columns:
        series = numeric_df[column].dropna()

        if series.empty:
            results[column] = {
                "count": 0,
                "mean": None,
                "median": None,
                "mode": None,
                "variance": None,
                "std": None,
                "min": None,
                "max": None,
                "range": None,
                "skewness": None,
                "kurtosis": None,
                "unique_values": 0,
                "zero_count": 0,
                "negative_count": 0,
                "coefficient_of_variation": None,
            }
            continue

        mean = float(series.mean())
        median = float(series.median())

        mode_values = series.mode()

        mode = (
            float(mode_values.iloc[0])
            if not mode_values.empty
            else None
        )

        variance = float(series.var())
        std = float(series.std())

        minimum = float(series.min())
        maximum = float(series.max())

        data_range = maximum - minimum

        skewness = float(series.skew())
        kurtosis = float(series.kurt())

        unique_values = int(series.nunique())

        zero_count = int((series == 0).sum())

        negative_count = int((series < 0).sum())

        coefficient_of_variation = (
            (std / mean) * 100
            if mean != 0
            else None
        )

        results[column] = {
            "count": int(series.count()),
            "mean": round(mean, 4),
            "median": round(median, 4),
            "mode": round(mode, 4) if mode is not None else None,
            "variance": round(variance, 4),
            "std": round(std, 4),
            "min": round(minimum, 4),
            "max": round(maximum, 4),
            "range": round(data_range, 4),
            "skewness": round(skewness, 4),
            "kurtosis": round(kurtosis, 4),
            "unique_values": unique_values,
            "zero_count": zero_count,
            "negative_count": negative_count,
            "coefficient_of_variation": (
                round(coefficient_of_variation, 4)
                if coefficient_of_variation is not None
                else None
            ),
        }

    return {
        "total_numeric_columns": len(results),
        "columns": results,
    }