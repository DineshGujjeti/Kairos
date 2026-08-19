"""
Smart KPI Cards.

The rest of this module (overview.py, calculator.py) exposes raw
per-column statistics -- useful as a reference table, but not what a
person means when they ask "what are my KPIs?". A KPI is a curated
metric with a trend and a plain-language read on whether that trend is
good, bad, or unremarkable. This module builds that layer on top of the
existing dataset_intelligence profiler and trend.detect_datetime_columns,
rather than duplicating detection logic that already exists elsewhere.

Design
------
1. Pick candidate measure columns from the dataset profile -- prefer
   ranked target_candidates (business-pattern matches like "revenue",
   "cost") over the broader primary_measures list, capped at max_cards.
2. For each candidate, decide sum vs. mean aggregation from the column
   name (rate/price/score-like columns are averaged; volume/revenue-like
   columns are summed) -- this is a heuristic, not a guarantee, so it's
   kept simple and explainable rather than trying to be clever.
3. If a real datetime column exists, compare the most recent half of the
   (date-sorted) data against the earlier half for a genuine
   period-over-period trend. If there's no datetime column, the same
   comparison is done over row order instead -- but the description
   always says "earlier vs. later records" in that case, never implying
   calendar time that isn't there (same honesty principle as the
   forecasting module's synthetic-datetime fallback).
4. Every card gets a human-readable label (humanized column name), a
   formatted value (currency/percent guessed from the name), and one
   plain-language sentence describing what's going on -- this is the
   part that makes a KPI page actually readable by a business user
   instead of an analyst staring at a stats table.
"""
from __future__ import annotations

import re

import pandas as pd

from app.services.dataset_intelligence import profile_dataset
from app.services.kpi.trend import detect_datetime_columns

_RATE_WORDS = {
    "rate", "ratio", "score", "pct", "percent", "percentage", "avg", "average",
    "margin", "index", "satisfaction", "confidence", "probability", "age", "duration",
}
_CURRENCY_WORDS = {
    "price", "cost", "revenue", "amount", "salary", "budget", "fee", "spend",
    "balance", "tax", "income", "expense", "profit", "value", "sales",
}
_PERCENT_WORDS = {"rate", "pct", "percent", "percentage", "margin", "ratio"}
_BAD_WHEN_UP_WORDS = {
    "cost", "expense", "churn", "defect", "complaint", "delay", "downtime",
    "error", "return", "refund", "cancellation", "attrition", "risk",
}


def _humanize(col_name: str) -> str:
    """order_total -> Order Total, avgResponseTime -> Avg Response Time."""
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", col_name)  # camelCase -> spaced
    spaced = spaced.replace("_", " ").replace("-", " ")
    words = [w for w in spaced.split() if w]
    return " ".join(w.capitalize() for w in words) or col_name


def _tokens(col_name: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9]+", "_", col_name.lower()).split("_"))


def _preferred_aggregation(col_name: str) -> str:
    return "mean" if _tokens(col_name) & _RATE_WORDS else "sum"


def _format_value(value: float, col_name: str) -> str:
    tokens = _tokens(col_name)
    if tokens & _PERCENT_WORDS:
        return f"{value:,.1f}%"
    if tokens & _CURRENCY_WORDS:
        return f"${value:,.0f}" if abs(value) >= 100 else f"${value:,.2f}"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if float(value).is_integer():
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _sentiment_for_change(col_name: str, pct_change: float) -> str:
    """'positive' | 'negative' | 'neutral' -- whether a rise in this
    column is good news, bad news, or not inherently either."""
    is_bad_when_up = bool(_tokens(col_name) & _BAD_WHEN_UP_WORDS)
    if abs(pct_change) < 3:
        return "neutral"
    rising = pct_change > 0
    if is_bad_when_up:
        return "negative" if rising else "positive"
    return "positive" if rising else "negative"


def _aggregate(series: pd.Series, how: str) -> float | None:
    non_null = series.dropna()
    if non_null.empty:
        return None
    return float(non_null.mean()) if how == "mean" else float(non_null.sum())


def _build_card(df: pd.DataFrame, col: str, datetime_col: str | None) -> dict | None:
    how = _preferred_aggregation(col)
    overall = _aggregate(df[col], how)
    if overall is None:
        return None

    label = _humanize(col)
    formatted_value = _format_value(overall, col)

    # ── Trend: real dates if we have them, row order otherwise ────
    trend_available = len(df) >= 6
    pct_change = None
    direction = "flat"
    comparison_basis = None

    if trend_available:
        if datetime_col:
            ordered = df[[datetime_col, col]].copy()
            ordered[datetime_col] = pd.to_datetime(ordered[datetime_col], errors="coerce", format="mixed")
            ordered = ordered.dropna(subset=[datetime_col]).sort_values(datetime_col)
            comparison_basis = "period"
        else:
            ordered = df[[col]].copy()
            comparison_basis = "sequence"

        n = len(ordered)
        if n >= 6:
            midpoint = n // 2
            earlier = _aggregate(ordered[col].iloc[:midpoint], how)
            later = _aggregate(ordered[col].iloc[midpoint:], how)
            if earlier is not None and later is not None and earlier != 0:
                pct_change = round((later - earlier) / abs(earlier) * 100, 1)
                if pct_change > 2:
                    direction = "up"
                elif pct_change < -2:
                    direction = "down"
        else:
            trend_available = False

    sentiment = _sentiment_for_change(col, pct_change) if pct_change is not None else "neutral"

    # ── Plain-language description ─────────────────────────────
    subject = "on average" if how == "mean" else "in total"
    if pct_change is None:
        description = f"{label} is {formatted_value} {subject} across {len(df):,} records."
    else:
        time_phrase = "compared to the earlier period" if comparison_basis == "period" else "compared to earlier records in this dataset"
        change_word = "up" if direction == "up" else "down" if direction == "down" else "roughly flat"
        description = (
            f"{label} is {formatted_value} {subject}, {change_word} "
            f"{abs(pct_change):.1f}% {time_phrase}."
            if direction != "flat"
            else f"{label} is {formatted_value} {subject} and has stayed roughly flat {time_phrase}."
        )

    return {
        "key": col,
        "label": label,
        "value": round(overall, 4),
        "formatted_value": formatted_value,
        "aggregation": how,
        "trend_available": pct_change is not None,
        "direction": direction,
        "change_pct": pct_change,
        "sentiment": sentiment,
        "comparison_basis": comparison_basis,
        "description": description,
        "is_notable": pct_change is not None and abs(pct_change) >= 20,
    }


def generate_smart_kpi_cards(df: pd.DataFrame, max_cards: int = 6) -> dict:
    """
    Returns curated, business-readable KPI cards for *df*.

    Never raises: an unprofilable or empty dataset returns an empty
    card list with has_measures=False rather than an error, so the KPI
    page can render a clean "not enough data" state instead of crashing.
    """
    if df is None or df.empty:
        return {"cards": [], "has_measures": False, "has_time_comparison": False, "summary": None}

    try:
        profile = profile_dataset(df)
    except Exception:
        profile = {"target_candidates": [], "primary_measures": []}

    ranked_columns = list(dict.fromkeys(
        (profile.get("target_candidates") or []) + (profile.get("primary_measures") or [])
    ))
    ranked_columns = [c for c in ranked_columns if c in df.columns][:max_cards]

    if not ranked_columns:
        return {"cards": [], "has_measures": False, "has_time_comparison": False, "summary": None}

    datetime_cols = detect_datetime_columns(df)
    datetime_col = datetime_cols[0] if datetime_cols else None

    cards = []
    for col in ranked_columns:
        card = _build_card(df, col, datetime_col)
        if card:
            cards.append(card)

    trending_up = sum(1 for c in cards if c["direction"] == "up")
    trending_down = sum(1 for c in cards if c["direction"] == "down")
    notable = [c for c in cards if c["is_notable"]]

    if not cards:
        summary = None
    elif not any(c["trend_available"] for c in cards):
        summary = f"Showing {len(cards)} key metric{'s' if len(cards) != 1 else ''} — not enough data yet for trend comparison."
    elif notable:
        lead = notable[0]
        summary = f"{lead['label']} moved {abs(lead['change_pct']):.0f}% — the most significant change among {len(cards)} tracked metrics."
    elif trending_up or trending_down:
        summary = f"{trending_up} metric{'s' if trending_up != 1 else ''} trending up, {trending_down} trending down, across {len(cards)} tracked."
    else:
        summary = f"{len(cards)} key metrics tracked — all holding steady."

    return {
        "cards": cards,
        "has_measures": True,
        "has_time_comparison": datetime_col is not None,
        "datetime_column": datetime_col,
        "summary": summary,
    }
