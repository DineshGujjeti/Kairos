"""
Tests for app.services.kpi.smart_cards -- curated, business-readable KPI
cards (distinct from the raw per-column statistics in calculator.py).
"""
import pandas as pd

from app.services.kpi.smart_cards import (
    _format_value,
    _humanize,
    _preferred_aggregation,
    _sentiment_for_change,
    generate_smart_kpi_cards,
)


# ── Unit tests for the small heuristic helpers ──────────────────────────────


def test_humanize_snake_case():
    assert _humanize("order_total") == "Order Total"


def test_humanize_camel_case():
    assert _humanize("avgResponseTime") == "Avg Response Time"


def test_humanize_single_word():
    assert _humanize("revenue") == "Revenue"


def test_preferred_aggregation_rate_word_uses_mean():
    assert _preferred_aggregation("discount_rate") == "mean"
    assert _preferred_aggregation("satisfaction_score") == "mean"


def test_preferred_aggregation_volume_word_uses_sum():
    assert _preferred_aggregation("revenue") == "sum"
    assert _preferred_aggregation("units_sold") == "sum"


def test_format_value_currency():
    assert _format_value(128450.0, "revenue") == "$128,450"


def test_format_value_percent():
    assert _format_value(7.2, "discount_rate") == "7.2%"


def test_format_value_plain_large_number():
    assert _format_value(4770.0, "units_sold") == "4,770"


def test_sentiment_revenue_up_is_positive():
    assert _sentiment_for_change("revenue", 15.0) == "positive"


def test_sentiment_cost_up_is_negative():
    assert _sentiment_for_change("support_cost", 15.0) == "negative"


def test_sentiment_cost_down_is_positive():
    assert _sentiment_for_change("support_cost", -15.0) == "positive"


def test_sentiment_small_change_is_neutral():
    assert _sentiment_for_change("revenue", 1.5) == "neutral"


# ── generate_smart_kpi_cards -- integration of the whole pipeline ──────────


def test_empty_dataframe_returns_no_measures():
    result = generate_smart_kpi_cards(pd.DataFrame())
    assert result["cards"] == []
    assert result["has_measures"] is False
    assert result["summary"] is None


def test_no_numeric_columns_returns_no_measures():
    df = pd.DataFrame({"name": ["a", "b", "c"], "category": ["x", "y", "z"]})
    result = generate_smart_kpi_cards(df)
    assert result["has_measures"] is False


def test_sales_dataset_with_real_dates_has_time_comparison():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=40).astype(str),
        "revenue": [1000 + i * 20 for i in range(40)],
        "units_sold": [50 + i for i in range(40)],
    })
    result = generate_smart_kpi_cards(df)
    assert result["has_measures"] is True
    assert result["has_time_comparison"] is True
    assert result["datetime_column"] == "date"
    assert len(result["cards"]) >= 1
    revenue_card = next(c for c in result["cards"] if c["key"] == "revenue")
    assert revenue_card["trend_available"] is True
    assert revenue_card["direction"] == "up"  # monotonically increasing revenue
    assert revenue_card["comparison_basis"] == "period"
    assert "Revenue" in revenue_card["description"]


def test_dataset_without_datetime_uses_row_order_honestly():
    df = pd.DataFrame({
        "employee_id": range(30),
        "salary": [50000 + i * 1000 for i in range(30)],
    })
    result = generate_smart_kpi_cards(df)
    assert result["has_time_comparison"] is False
    salary_card = next(c for c in result["cards"] if c["key"] == "salary")
    assert salary_card["comparison_basis"] == "sequence"
    # Must never claim calendar time when there isn't any
    assert "period" not in salary_card["description"].lower() or "earlier records" in salary_card["description"].lower()
    assert "earlier record" in salary_card["description"].lower()


def test_cards_capped_at_max_cards():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=20).astype(str),
        **{f"revenue_{i}": [100 + j for j in range(20)] for i in range(10)},
    })
    result = generate_smart_kpi_cards(df, max_cards=3)
    assert len(result["cards"]) <= 3


def test_flat_metric_reports_flat_direction():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=20).astype(str),
        # Small alternating noise (not perfectly constant -- a truly
        # constant column is correctly excluded as a "measure" by the
        # profiler, since there's nothing to track) but averaging out
        # to a well-under-2% change between halves.
        "steady_revenue": [1000 + (i % 2) for i in range(20)],
    })
    result = generate_smart_kpi_cards(df)
    card = next(c for c in result["cards"] if c["key"] == "steady_revenue")
    assert card["direction"] == "flat"


def test_notable_change_flagged():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=20).astype(str),
        "revenue": [100] * 10 + [500] * 10,  # dramatic jump
    })
    result = generate_smart_kpi_cards(df)
    card = next(c for c in result["cards"] if c["key"] == "revenue")
    assert card["is_notable"] is True
    assert abs(card["change_pct"]) >= 20


def test_summary_present_when_cards_exist():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=20).astype(str),
        "revenue": [1000 + i * 10 for i in range(20)],
    })
    result = generate_smart_kpi_cards(df)
    assert result["summary"] is not None
    assert isinstance(result["summary"], str)


def test_never_raises_on_malformed_data():
    """Defensive: weird/degenerate input must degrade gracefully, not crash."""
    df = pd.DataFrame({"revenue": [None, None, None]})
    result = generate_smart_kpi_cards(df)
    assert isinstance(result, dict)
    assert "cards" in result
