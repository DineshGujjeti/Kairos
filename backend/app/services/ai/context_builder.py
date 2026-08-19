"""
Enterprise AI Context Builder — Module 6.

Assembles a rich, structured analytical context from every analytics engine
(EDA, KPI, Forecasting) so that Gemini NEVER receives raw CSV rows.
Gemini receives pre-computed business intelligence instead.
"""
from __future__ import annotations

import pandas as pd

from app.core.logging import get_logger
from app.core.pandas_compat import TEXT_DTYPES_NO_CATEGORY
from app.services.eda.quality import quality as eda_quality
from app.services.eda.statistics import statistics as eda_statistics
from app.services.eda.outliers import outliers as eda_outliers
from app.services.eda.correlation import correlation as eda_correlation
from app.services.eda.insights import insights as eda_insights
from app.services.eda.missing_values import missing_values as eda_missing
from app.services.kpi.overview import overview as kpi_overview
from app.services.kpi.calculator import compute_column_metrics
from app.services.forecasting.detector import validate_for_forecasting
from app.services.forecasting.orchestrator import forecast_overview, analyze_series

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Individual context builders
# ─────────────────────────────────────────────────────────────

def _safe(fn, *args, fallback=None, **kwargs):
    """Call fn(*args, **kwargs), return fallback on any exception."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.warning("context_builder_error", fn=fn.__name__, error=str(exc))
        return fallback


def _dataset_meta(df: pd.DataFrame) -> dict:
    numeric_cols = list(df.select_dtypes(include="number").columns)
    categorical_cols = list(df.select_dtypes(include=TEXT_DTYPES_NO_CATEGORY).columns)
    datetime_cols = list(df.select_dtypes(include=["datetime", "datetimetz"]).columns)
    total_cells = len(df) * len(df.columns)
    missing_cells = int(df.isna().sum().sum())

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "missing_rate_pct": round(missing_cells / total_cells * 100, 2) if total_cells else 0,
        "duplicate_rows": int(df.duplicated().sum()),
    }


def _top_categories(df: pd.DataFrame, top_n: int = 5) -> dict:
    """Return top-N value counts for each categorical column."""
    result = {}
    for col in df.select_dtypes(include=TEXT_DTYPES_NO_CATEGORY).columns:
        counts = df[col].value_counts(dropna=True).head(top_n)
        result[col] = {str(k): int(v) for k, v in counts.items()}
    return result


def _numeric_ranges(df: pd.DataFrame) -> dict:
    """Return min/max/mean for each numeric column — compact for the prompt."""
    result = {}
    for col in df.select_dtypes(include="number").columns:
        s = df[col].dropna()
        if s.empty:
            continue
        result[col] = {
            "min": round(float(s.min()), 4),
            "max": round(float(s.max()), 4),
            "mean": round(float(s.mean()), 4),
            "sum": round(float(s.sum()), 4),
            "std": round(float(s.std()), 4) if len(s) > 1 else 0.0,
        }
    return result


def _business_health_score(
    quality_score: float,
    missing_rate: float,
    duplicate_rows: int,
    total_rows: int,
    trend_direction: str | None,
    outlier_pct: float,
) -> dict:
    """
    Compute Business Health Score (0–100) from multiple signals.

    Components
    ----------
    data_quality_score  : from EDA quality engine (completeness, uniqueness…)
    missing_penalty     : −1 point per 1 % missing data (max −20)
    duplicate_penalty   : −10 if >5 % rows are duplicates
    trend_bonus         : +5 if trend is increasing, −5 if decreasing
    outlier_penalty     : −0.5 per 1 % outlier rate (max −10)
    """
    score = quality_score  # 0–100 baseline

    # Missing data
    score -= min(missing_rate, 20)

    # Duplicate rows
    dup_pct = (duplicate_rows / total_rows * 100) if total_rows else 0
    if dup_pct > 5:
        score -= 10

    # Trend
    if trend_direction == "increasing":
        score += 5
    elif trend_direction == "decreasing":
        score -= 5

    # Outliers
    score -= min(outlier_pct * 0.5, 10)

    score = max(0.0, min(100.0, score))

    if score >= 85:
        rating = "Excellent"
    elif score >= 70:
        rating = "Good"
    elif score >= 55:
        rating = "Fair"
    elif score >= 40:
        rating = "Needs Attention"
    else:
        rating = "Critical"

    financial_score = round(min(100, score + (5 if trend_direction == "increasing" else 0)), 1)
    operational_score = round(
        max(0.0, min(100.0, quality_score - (duplicate_rows / max(total_rows, 1)) * 20)), 1
    )
    risk_score = round(max(0, 100 - score), 1)

    return {
        "overall": round(score, 1),
        "rating": rating,
        "financial_score": financial_score,
        "operational_score": operational_score,
        "risk_score": risk_score,
        "components": {
            "data_quality_base": round(quality_score, 1),
            "missing_penalty": round(min(missing_rate, 20), 1),
            "duplicate_penalty": round(10.0 if dup_pct > 5 else 0.0, 1),
            "trend_adjustment": 5 if trend_direction == "increasing" else (-5 if trend_direction == "decreasing" else 0),
            "outlier_penalty": round(min(outlier_pct * 0.5, 10), 1),
        },
    }


# ─────────────────────────────────────────────────────────────
# Master context assembler
# ─────────────────────────────────────────────────────────────

def build_complete_context(
    df: pd.DataFrame,
    dataset_name: str,
    include_metrics: bool = True,
) -> dict:
    """
    Build a rich analytical context for Gemini.

    Assembles data from:
    - Dataset metadata
    - EDA (quality, statistics, outliers, correlation, missing values, insights)
    - KPI metrics
    - Forecasting (trend, seasonality, overview)
    - Business Health Score

    Returns a fully structured dict — never passes raw rows to Gemini.
    """

    # ── Dataset metadata ──────────────────────────────────────
    meta = _dataset_meta(df)
    top_cats = _safe(_top_categories, df, fallback={})
    num_ranges = _numeric_ranges(df)

    # ── EDA ──────────────────────────────────────────────────
    quality_result = _safe(eda_quality, df, fallback={})
    statistics_result = _safe(eda_statistics, df, fallback={})
    outliers_result = _safe(eda_outliers, df, fallback={})
    correlation_result = _safe(eda_correlation, df, fallback={})
    missing_result = _safe(eda_missing, df, fallback={})
    insights_result = _safe(eda_insights, df, fallback={"insights": [], "total_insights": 0})

    quality_score = quality_result.get("quality_score", 75.0) if quality_result else 75.0
    total_outliers = outliers_result.get("total_outliers", 0) if outliers_result else 0
    outlier_pct = (total_outliers / max(len(df), 1)) * 100

    # ── KPI ──────────────────────────────────────────────────
    kpi_overview_result = _safe(kpi_overview, df, fallback={})
    kpi_metrics = _safe(compute_column_metrics, df, fallback={}) if include_metrics else {}

    # ── Forecasting ──────────────────────────────────────────
    trend_direction = None
    forecast_ctx: dict = {"suitable": False}

    try:
        dt_col, tgt_col, auto_dt, auto_tgt = validate_for_forecasting(df)
        f_overview = _safe(forecast_overview, df, dt_col, tgt_col, fallback={})
        f_analysis = _safe(analyze_series, df, dt_col, tgt_col, fallback={})
        trend = (f_analysis or {}).get("trend", {})
        seasonality = (f_analysis or {}).get("seasonality", {})
        trend_direction = trend.get("direction")

        forecast_ctx = {
            "suitable": True,
            "datetime_column": dt_col,
            "target_column": tgt_col,
            "auto_detected": {"datetime": auto_dt, "target": auto_tgt},
            "overview": f_overview,
            "trend": trend,
            "seasonality": seasonality,
        }
    except Exception:
        pass

    # ── Business Health Score ─────────────────────────────────
    health = _business_health_score(
        quality_score=quality_score,
        missing_rate=meta["missing_rate_pct"],
        duplicate_rows=meta["duplicate_rows"],
        total_rows=meta["rows"],
        trend_direction=trend_direction,
        outlier_pct=outlier_pct,
    )

    return {
        "dataset_name": dataset_name,
        "metadata": meta,
        "top_categories": top_cats,
        "numeric_ranges": num_ranges,
        "eda": {
            "quality": quality_result,
            "statistics": statistics_result,
            "outliers": outliers_result,
            "correlation": correlation_result,
            "missing_values": missing_result,
            "insights": insights_result,
        },
        "kpi": {
            "overview": kpi_overview_result,
            "metrics": kpi_metrics,
        },
        "forecast": forecast_ctx,
        "health_score": health,
    }


# ─────────────────────────────────────────────────────────────
# Context → prompt text formatter
# ─────────────────────────────────────────────────────────────

def format_context_for_prompt(context: dict) -> str:  # noqa: C901
    """
    Render the analytics context as structured text for Gemini prompts.

    The output is human-readable and LLM-friendly — no raw JSON blobs.
    """
    lines: list[str] = []

    def section(title: str):
        lines.append("")
        lines.append(f"{'─' * 60}")
        lines.append(f"  {title}")
        lines.append(f"{'─' * 60}")

    # ── Dataset overview ──────────────────────────────────────
    meta = context.get("metadata", {})
    section("DATASET OVERVIEW")
    lines.append(f"  Rows              : {meta.get('rows', 'N/A'):,}")
    lines.append(f"  Columns           : {meta.get('columns', 'N/A')}")
    lines.append(f"  Numeric columns   : {len(meta.get('numeric_columns', []))}")
    lines.append(f"  Categorical cols  : {len(meta.get('categorical_columns', []))}")
    lines.append(f"  Datetime columns  : {len(meta.get('datetime_columns', []))}")
    lines.append(f"  Missing values    : {meta.get('missing_cells', 0):,} ({meta.get('missing_rate_pct', 0)}%)")
    lines.append(f"  Duplicate rows    : {meta.get('duplicate_rows', 0):,}")
    lines.append(f"  Column names      : {', '.join(meta.get('column_names', []))}")

    # ── Business Health Score ─────────────────────────────────
    health = context.get("health_score", {})
    section("BUSINESS HEALTH SCORE")
    lines.append(f"  Overall Score     : {health.get('overall', 'N/A')} / 100  ({health.get('rating', 'N/A')})")
    lines.append(f"  Financial Score   : {health.get('financial_score', 'N/A')}")
    lines.append(f"  Operational Score : {health.get('operational_score', 'N/A')}")
    lines.append(f"  Risk Score        : {health.get('risk_score', 'N/A')} (higher = more risk)")

    # ── Data Quality ──────────────────────────────────────────
    eda = context.get("eda", {})
    q = eda.get("quality") or {}
    if q:
        section("DATA QUALITY")
        lines.append(f"  Quality Score  : {q.get('quality_score', 'N/A')} / 100  ({q.get('rating', 'N/A')})")
        m = q.get("metrics", {})
        lines.append(f"  Completeness   : {m.get('completeness', 'N/A')}%")
        lines.append(f"  Consistency    : {m.get('consistency_score', 'N/A')}%")
        lines.append(f"  Uniqueness     : {m.get('uniqueness_score', 'N/A')}%")
        lines.append(f"  Duplicate-free : {m.get('duplicate_score', 'N/A')}%")

    # ── KPI Metrics ───────────────────────────────────────────
    kpi = context.get("kpi", {})
    kpi_ov = kpi.get("overview") or {}
    if kpi_ov:
        section("KPI OVERVIEW")
        for k, v in kpi_ov.items():
            lines.append(f"  {k:<30}: {v}")

    kpi_metrics = (kpi.get("metrics") or {}).get("columns", {})
    if kpi_metrics:
        section("KPI METRICS (per numeric column)")
        for col, m in kpi_metrics.items():
            lines.append(
                f"  {col}: sum={m.get('sum')}, mean={m.get('mean')}, "
                f"min={m.get('min')}, max={m.get('max')}, std={m.get('std')}"
            )

    # ── Numeric Ranges ────────────────────────────────────────
    ranges = context.get("numeric_ranges", {})
    if ranges:
        section("NUMERIC COLUMN RANGES")
        for col, r in ranges.items():
            lines.append(
            f"  {col}: min={r.get('min', 'N/A')}, max={r.get('max', 'N/A')}, "
            f"mean={r.get('mean', 'N/A')}, sum={r.get('sum', 'N/A')}"
        )

    # ── Top Categories ────────────────────────────────────────
    cats = context.get("top_categories", {})
    if cats:
        section("TOP CATEGORIES")
        for col, vals in cats.items():
            top = ", ".join(f"{k}={v}" for k, v in list(vals.items())[:3])
            lines.append(f"  {col}: {top}")

    # ── EDA Insights ──────────────────────────────────────────
    ins = (eda.get("insights") or {}).get("insights", [])
    if ins:
        section("EDA AUTO-INSIGHTS")
        for i in ins[:8]:
            lines.append(f"  • {i}")

    # ── Correlation ───────────────────────────────────────────
    corr = eda.get("correlation") or {}
    pairs = corr.get("highly_correlated_pairs", [])
    if pairs:
        section("HIGHLY CORRELATED VARIABLES")
        for p in pairs[:5]:
            lines.append(
                f"  {p.get('column_1')} ↔ {p.get('column_2')}: r={p.get('correlation')}"
            )

    # ── Outliers ──────────────────────────────────────────────
    out = eda.get("outliers") or {}
    if out.get("total_outliers"):
        section("OUTLIER SUMMARY")
        lines.append(f"  Total outliers detected : {out.get('total_outliers', 0)}")
        lines.append(f"  Columns with outliers   : {out.get('columns_with_outliers', 0)}")
        for col_name in out.get("column_names_with_outliers", [])[:4]:
            cd = out.get("columns", {}).get(col_name, {})
            lines.append(
                f"  {col_name}: {cd.get('outlier_count', '?')} outliers "
                f"(lower={cd.get('lower_bound')}, upper={cd.get('upper_bound')})"
            )

    # ── Missing Values ────────────────────────────────────────
    mv = eda.get("missing_values") or {}
    mv_cols = {
        col: info
        for col, info in (mv.get("columns") or {}).items()
        if info.get("missing_count", 0) > 0
    }
    if mv_cols:
        section("MISSING VALUE DETAILS")
        for col, info in list(mv_cols.items())[:6]:
            lines.append(
                f"  {col}: {info.get('missing_count')} missing "
                f"({info.get('missing_percentage', 0):.1f}%)"
            )

    # ── Forecasting ───────────────────────────────────────────
    fc = context.get("forecast", {})
    if fc.get("suitable"):
        section("TIME-SERIES & FORECAST")
        lines.append(f"  DateTime column : {fc.get('datetime_column')}")
        lines.append(f"  Target metric   : {fc.get('target_column')}")
        trend = fc.get("trend", {})
        lines.append(
            f"  Trend           : {trend.get('direction', 'N/A').upper()} "
            f"(slope={trend.get('slope', 0):.4f}, strength={trend.get('strength', 0):.4f})"
        )
        season = fc.get("seasonality", {})
        lines.append(
            f"  Seasonality     : {'YES — period=' + str(season.get('detected_period')) if season.get('is_seasonal') else 'None detected'}"
        )
        ov = fc.get("overview", {})
        lines.append(f"  Date range      : {ov.get('date_range_start', '?')} → {ov.get('date_range_end', '?')}")
    else:
        lines.append("")
        lines.append("  Forecasting: Dataset is not time-series or insufficient rows.")

    lines.append("")
    return "\n".join(lines)
