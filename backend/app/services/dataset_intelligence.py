"""
Dataset Intelligence — dynamic, dataset-agnostic column profiling.

Every uploaded dataset, regardless of business domain (sales, HR, finance,
healthcare, marketing, inventory, logistics, IoT, ...), gets profiled here
using name-pattern + statistical heuristics rather than hardcoded schemas.
Downstream modules (EDA, KPI, Forecasting, Root Cause, Simulation, Decision)
can consult this profile instead of guessing column meaning themselves.

This does not replace the domain-specific structural validation used for
the six built-in supply-chain dataset types (orders/products/inventory/
warehouses/suppliers/deliveries) -- it is the general-purpose counterpart
that runs for *every* dataset, including those six, so a single, consistent
picture of "what did we detect" is always available.

Column roles
------------
id                    Unique/near-unique identifier column (order_id, sku, ...)
datetime              Parseable date/time column
numeric_measure        Numeric column suitable for aggregation/forecasting
categorical_dimension  Low/medium-cardinality text column suitable for grouping
boolean               Two-valued column (True/False, Yes/No, 0/1, ...)
free_text             High-cardinality text column (notes, descriptions, ...)
constant              Column with a single repeated value (no signal)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from app.core.pandas_compat import is_text_dtype

# ── Vocabulary ──────────────────────────────────────────────────────────────
# Shared with forecasting/detector.py in spirit (kept separately because this
# module must stay import-light and dependency-free from the forecasting
# subsystem so every other module can use it without a circular import).

ID_PATTERNS = ["id", "_id", "code", "key", "uuid", "guid", "sku", "no", "num", "number", "ref"]

DATETIME_PATTERNS = [
    "date", "datetime", "timestamp", "time", "day", "month", "year",
    "created", "updated", "period", "ds", "pickup", "dropoff",
]

MEASURE_PATTERNS = [
    "sales", "revenue", "amount", "total", "profit", "income", "quantity",
    "demand", "orders", "cost", "expense", "price", "count", "value",
    "score", "rate", "duration", "hours", "salary", "spend", "budget",
    "units", "volume", "balance", "margin", "tax", "fee", "discount",
]

BOOLEAN_TOKENS = {
    "true", "false", "yes", "no", "y", "n", "0", "1", "active", "inactive",
}

# Lightweight domain vocabulary for a friendly "what kind of data is this"
# guess. This is intentionally simple keyword overlap, not real NLP -- it's
# meant to make the product feel like it understands context, not to be a
# rigorous classifier.
DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "Sales & Revenue": {"sales", "revenue", "order", "customer", "product", "price", "discount"},
    "Finance": {"invoice", "payment", "balance", "tax", "expense", "budget", "account", "transaction"},
    "Human Resources": {"employee", "salary", "department", "hire", "attrition", "performance", "manager"},
    "Healthcare": {"patient", "diagnosis", "treatment", "admission", "physician", "hospital", "prescription"},
    "Marketing": {"campaign", "click", "impression", "conversion", "lead", "channel", "engagement"},
    "Inventory & Supply Chain": {"warehouse", "supplier", "inventory", "stock", "shipment", "delivery", "sku"},
    "Customer Analytics": {"churn", "segment", "satisfaction", "retention", "nps", "ltv"},
    "Operations / IoT": {"sensor", "device", "reading", "temperature", "uptime", "latency", "status"},
}


def _score_name(col_name: str, patterns: list[str]) -> float:
    """0..1 score for how strongly a column name matches a pattern vocabulary."""
    name = re.sub(r"[^a-z0-9]+", "_", col_name.lower()).strip("_")
    tokens = set(name.split("_"))
    best = 0.0
    for pattern in patterns:
        if pattern == name:
            best = max(best, 1.0)
        elif pattern in tokens:
            best = max(best, 0.85)
        elif len(pattern) >= 4 and pattern in name:
            # Substring matching only for longer patterns -- short tokens
            # like "no", "id", "key" would otherwise false-positive inside
            # unrelated words ("notes", "acid", "monkey").
            best = max(best, 0.6)
    return best


@dataclass
class ColumnProfile:
    name: str
    role: str
    dtype: str
    null_rate: float
    unique_count: int
    unique_ratio: float
    sample_values: list = field(default_factory=list)
    is_target_candidate: bool = False
    target_score: float = 0.0
    is_datetime_candidate: bool = False
    datetime_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "dtype": self.dtype,
            "null_rate": self.null_rate,
            "unique_count": self.unique_count,
            "unique_ratio": self.unique_ratio,
            "sample_values": self.sample_values,
            "is_target_candidate": self.is_target_candidate,
            "target_score": self.target_score,
            "is_datetime_candidate": self.is_datetime_candidate,
            "datetime_score": self.datetime_score,
        }


def _classify_column(df: pd.DataFrame, col: str) -> ColumnProfile:
    series = df[col]
    n = len(series)
    non_null = series.dropna()
    null_rate = round(1 - len(non_null) / n, 4) if n else 0.0
    unique_count = int(non_null.nunique())
    unique_ratio = round(unique_count / len(non_null), 4) if len(non_null) else 0.0

    dtype_str = str(series.dtype)
    id_score = _score_name(col, ID_PATTERNS)
    dt_score = _score_name(col, DATETIME_PATTERNS)
    measure_score = _score_name(col, MEASURE_PATTERNS)

    sample = non_null.drop_duplicates().head(5).tolist()
    sample = [str(v) if not isinstance(v, (int, float, bool)) else v for v in sample]

    # Constant column — no signal regardless of dtype
    if unique_count <= 1:
        return ColumnProfile(col, "constant", dtype_str, null_rate, unique_count, unique_ratio, sample)

    # Native datetime dtype
    if pd.api.types.is_datetime64_any_dtype(series):
        return ColumnProfile(
            col, "datetime", dtype_str, null_rate, unique_count, unique_ratio, sample,
            is_datetime_candidate=True, datetime_score=1.0,
        )

    # Boolean: dtype bool, or exactly 2 unique values matching boolean-like tokens
    if pd.api.types.is_bool_dtype(series):
        return ColumnProfile(col, "boolean", dtype_str, null_rate, unique_count, unique_ratio, sample)
    if unique_count == 2:
        vals = {str(v).strip().lower() for v in non_null.unique()}
        if vals & BOOLEAN_TOKENS or vals <= BOOLEAN_TOKENS:
            return ColumnProfile(col, "boolean", dtype_str, null_rate, unique_count, unique_ratio, sample)

    # Numeric
    if pd.api.types.is_numeric_dtype(series):
        # High-uniqueness numeric column with an id-like name → id, not a measure
        if id_score >= 0.6 and unique_ratio > 0.9:
            return ColumnProfile(col, "id", dtype_str, null_rate, unique_count, unique_ratio, sample)
        is_target = measure_score >= 0.6 or (unique_ratio > 0.05 and id_score < 0.6)
        return ColumnProfile(
            col, "numeric_measure", dtype_str, null_rate, unique_count, unique_ratio, sample,
            is_target_candidate=is_target, target_score=measure_score,
        )

    # Text-like: could be id, datetime, categorical dimension, or free text
    if is_text_dtype(series):
        if id_score >= 0.6 and unique_ratio > 0.9:
            return ColumnProfile(col, "id", dtype_str, null_rate, unique_count, unique_ratio, sample)

        if dt_score > 0.5 or unique_ratio > 0.3:
            # Attempt a real parse before committing to "datetime" — cheap
            # sample-based check (parsing the whole column is done later,
            # only for the column ultimately selected for forecasting).
            try:
                parsed = pd.to_datetime(non_null.head(30), errors="coerce", format="mixed")
                parse_rate = parsed.notna().mean() if len(parsed) else 0
            except Exception:
                parse_rate = 0
            if parse_rate > 0.8 and (dt_score > 0.3 or parse_rate > 0.95):
                return ColumnProfile(
                    col, "datetime", dtype_str, null_rate, unique_count, unique_ratio, sample,
                    is_datetime_candidate=True, datetime_score=max(dt_score, parse_rate),
                )

        # High-cardinality text with no id/datetime signal → free text
        if unique_ratio > 0.6:
            return ColumnProfile(col, "free_text", dtype_str, null_rate, unique_count, unique_ratio, sample)

        # Otherwise: a categorical dimension (region, status, segment, ...)
        return ColumnProfile(col, "categorical_dimension", dtype_str, null_rate, unique_count, unique_ratio, sample)

    # Fallback — shouldn't normally hit this
    return ColumnProfile(col, "free_text", dtype_str, null_rate, unique_count, unique_ratio, sample)


def _guess_domain(columns: list[str]) -> tuple[str, float]:
    """Keyword-overlap heuristic for a friendly 'what kind of data is this' label."""
    tokens: set[str] = set()
    for col in columns:
        tokens |= set(re.sub(r"[^a-z0-9]+", "_", col.lower()).split("_"))

    best_domain, best_score = "General Business Data", 0.0
    for domain, keywords in DOMAIN_KEYWORDS.items():
        overlap = len(tokens & keywords)
        score = overlap / max(len(keywords), 1)
        if overlap >= 2 and score > best_score:
            best_domain, best_score = domain, score
    return best_domain, round(min(best_score, 1.0), 2)


def profile_dataset(df: pd.DataFrame) -> dict:
    """
    Profile every column in *df* and return a dataset-level summary.

    Never raises — degrades gracefully to conservative defaults on
    unexpected input so it is always safe to call at upload time.
    """
    if df is None or df.empty or len(df.columns) == 0:
        return {
            "row_count": 0,
            "column_count": 0,
            "domain_guess": "Unknown",
            "domain_confidence": 0.0,
            "columns": {},
            "roles": {},
            "best_datetime_column": None,
            "target_candidates": [],
            "primary_dimensions": [],
            "primary_measures": [],
        }

    profiles = {col: _classify_column(df, col) for col in df.columns}

    roles: dict[str, list[str]] = {}
    for name, p in profiles.items():
        roles.setdefault(p.role, []).append(name)

    # Rank datetime candidates
    dt_candidates = sorted(
        (p for p in profiles.values() if p.is_datetime_candidate),
        key=lambda p: -p.datetime_score,
    )
    best_datetime = dt_candidates[0].name if dt_candidates else None

    # Rank target (measure) candidates
    target_candidates = sorted(
        (p for p in profiles.values() if p.role == "numeric_measure" and p.is_target_candidate),
        key=lambda p: -p.target_score,
    )
    target_names = [p.name for p in target_candidates][:10]

    # Primary dimensions: categorical columns with reasonable cardinality,
    # ranked by how "groupable" they are (lower cardinality ratio = better).
    dims = sorted(
        (p for p in profiles.values() if p.role == "categorical_dimension"),
        key=lambda p: p.unique_ratio,
    )
    primary_dims = [p.name for p in dims][:10]

    measures = [p.name for p in profiles.values() if p.role == "numeric_measure"]

    domain, confidence = _guess_domain(list(df.columns))

    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "domain_guess": domain,
        "domain_confidence": confidence,
        "columns": {name: p.to_dict() for name, p in profiles.items()},
        "roles": roles,
        "best_datetime_column": best_datetime,
        "target_candidates": target_names,
        "primary_dimensions": primary_dims,
        "primary_measures": measures,
    }
