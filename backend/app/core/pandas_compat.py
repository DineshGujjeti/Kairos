"""
pandas 3.x compatibility helpers.

pandas 3.0 changed the *default* inferred dtype for text columns coming
out of ``pd.read_csv`` / ``pd.read_excel`` from the legacy ``object``
dtype to a native ``str`` dtype. Any code written against the old
assumption -- ``df[col].dtype == "object"`` or
``df.select_dtypes(include="object")`` -- now silently matches **zero**
columns for freshly-ingested data, even though those columns are still
plainly text.

This module centralises the correct, version-proof way to detect text
columns so the fix only has to be made once and reused everywhere,
rather than every call site guessing at the right incantation.

Anywhere in this codebase that used to write:

    df.select_dtypes(include="object")
    df.select_dtypes(include=["object", "category"])
    df[col].dtype == "object"

should now use ``TEXT_DTYPES`` / ``is_text_dtype`` from this module
instead. Both legacy ``object`` and the new pandas-3 ``str`` dtype are
covered, so the same code works correctly on pandas 2.x and 3.x.
"""
from __future__ import annotations

import pandas as pd

# Pass this list to select_dtypes(include=...) anywhere the code
# previously passed "object" (with or without "category" alongside it).
TEXT_DTYPES = ["object", "string", "category"]

# Same, but without "category" -- for call sites that handle category
# dtype separately or don't want it included.
TEXT_DTYPES_NO_CATEGORY = ["object", "string"]


def is_text_dtype(series: pd.Series) -> bool:
    """
    True for legacy ``object`` columns, pandas-3 ``str`` columns, and
    pandas ``category`` columns -- i.e. anything that should be treated
    as text/categorical rather than numeric or datetime.

    Prefer this over ``series.dtype == "object"``, which silently
    returns False for pandas-3 string columns.
    """
    return (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
        or isinstance(series.dtype, pd.CategoricalDtype)
    )


def text_columns(df: pd.DataFrame) -> list[str]:
    """Return column names that are text/categorical, pandas-version-proof."""
    return [c for c in df.columns if is_text_dtype(df[c])]
