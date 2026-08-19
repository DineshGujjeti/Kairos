import pandas as pd

from app.core.pandas_compat import TEXT_DTYPES


def insights(df: pd.DataFrame) -> dict:
    """
    Generate automatic insights about the dataset.

    The insights are rule-based and can later be replaced
    by an LLM-powered insight engine without changing the API.
    """

    insights = []

    total_rows = len(df)

    # --------------------------------------------------
    # Dataset Size
    # --------------------------------------------------
    insights.append(
        f"The dataset contains {total_rows} rows and {len(df.columns)} columns."
    )

    # --------------------------------------------------
    # Missing Values
    # --------------------------------------------------
    missing = df.isna().sum()

    for column, count in missing.items():
        if count == 0:
            continue

        percentage = (
            (count / total_rows) * 100
            if total_rows > 0
            else 0
        )

        if percentage >= 50:
            insights.append(
                f"Column '{column}' has {percentage:.2f}% missing values. Consider removing or imputing it."
            )
        elif percentage >= 20:
            insights.append(
                f"Column '{column}' contains a significant amount of missing data ({percentage:.2f}%)."
            )
        else:
            insights.append(
                f"Column '{column}' has {count} missing values."
            )

    # --------------------------------------------------
    # Duplicate Rows
    # --------------------------------------------------
    duplicates = int(df.duplicated().sum())

    if duplicates > 0:
        insights.append(
            f"The dataset contains {duplicates} duplicate rows."
        )

    # --------------------------------------------------
    # Numeric Analysis
    # --------------------------------------------------
    numeric_df = df.select_dtypes(include="number")

    for column in numeric_df.columns:

        series = numeric_df[column].dropna()

        if series.empty:
            continue

        # Highly skewed
        skewness = series.skew()

        if abs(skewness) > 1:
            insights.append(
                f"'{column}' is highly skewed (skewness={skewness:.2f})."
            )

        # Constant column
        if series.nunique() == 1:
            insights.append(
                f"'{column}' contains only one unique value."
            )

        # Mostly zeros
        zero_percentage = (
            (series == 0).sum() / len(series)
        ) * 100

        if zero_percentage > 80:
            insights.append(
                f"'{column}' contains mostly zero values."
            )

        # High variance
        if series.std() > series.mean() * 2:
            insights.append(
                f"'{column}' shows high variability."
            )

    # --------------------------------------------------
    # Correlation
    # --------------------------------------------------
    if len(numeric_df.columns) >= 2:

        corr = numeric_df.corr()

        visited = set()

        for col1 in corr.columns:
            for col2 in corr.columns:

                if col1 == col2:
                    continue

                key = tuple(sorted((col1, col2)))

                if key in visited:
                    continue

                visited.add(key)

                value = corr.loc[col1, col2]

                if pd.isna(value):
                    continue

                if abs(value) >= 0.8:
                    insights.append(
                        f"'{col1}' and '{col2}' are strongly correlated ({value:.2f})."
                    )

    # --------------------------------------------------
    # Categorical Columns
    # --------------------------------------------------
    categorical_df = df.select_dtypes(include=TEXT_DTYPES)

    for column in categorical_df.columns:

        unique = df[column].nunique(dropna=True)

        if unique == total_rows:
            insights.append(
                f"'{column}' appears to be an identifier."
            )

        if unique == 1:
            insights.append(
                f"'{column}' has only one unique category."
            )

    # --------------------------------------------------
    # Empty Dataset
    # --------------------------------------------------
    if total_rows == 0:
        insights.append("The dataset is empty.")

    return {
        "total_insights": len(insights),
        "insights": insights,
    }