import pandas as pd


def preview(df: pd.DataFrame) -> dict:
    """
    Returns a preview of the uploaded dataset.
    """

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),

        "dtypes": {
            column: str(dtype)
            for column, dtype in df.dtypes.items()
        },

        "missing_values": (
            df.isnull()
            .sum()
            .astype(int)
            .to_dict()
        ),

        "duplicate_rows": int(
            df.duplicated().sum()
        ),

        "sample_rows": (
            df.head(10)
            .to_dict(orient="records")
        ),
    }