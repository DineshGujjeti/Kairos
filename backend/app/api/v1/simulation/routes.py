"""Module 8: What-If Simulation Engine — API routes (improved)."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.ai import (
    ChartMetadata,
    ConfidenceScore,
    ModelComparisonSchema,
    ModelMetricsSchema,
    MultiSimulationRequest,
    MultiSimulationResponse,
    ScenarioComparisonRequest,
    ScenarioComparisonResponse,
    ScenarioResult,
    SensitivityRequest,
    SensitivityResponse,
    SensitivityRanking,
    SimulateRequest,
    SimulationOverviewResponse,
    SingleSimulationRequest,
    SingleSimulationResponse,
    VariableImpact,
    PredictionInterval,
)
from app.services.ai.service import get_ai_service
from app.services.ai.prompt_engine import get_template
from app.services.ai.response_parser import parse_to_response
from app.services.kpi.loader import load_dataframe
from app.services.simulation.model_trainer import train_models_cached, ModelPackage
from app.services.simulation.prediction_engine import simulate_single, simulate_multi
from app.services.simulation.sensitivity_engine import run_sensitivity_analysis
from app.services.simulation.scenario_engine import compare_scenarios
from app.services.simulation.visualization_builder import (
    build_single_simulation_chart,
    build_multi_simulation_chart,
    build_sensitivity_chart,
    build_sensitivity_sweep_charts,
    build_scenario_comparison_chart,
    build_model_comparison_chart,
)

router = APIRouter(prefix="/simulation", tags=["simulation"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _auto_target(df, requested: Optional[str]) -> str:
    if requested and requested in df.columns:
        return requested
    numeric = list(df.select_dtypes(include="number").columns)
    if not numeric:
        raise ValueError("No numeric columns found for simulation")
    preferred = ["revenue", "sales", "profit", "amount", "total",
                 "income", "quantity", "demand", "orders", "cost"]
    found = False
    for pref in preferred:
        for col in numeric:
            if pref.lower() in col.lower():
                return col
    return numeric[0]


def _train(dataset_id, df, target_column: str, feature_columns: Optional[list]) -> ModelPackage:
    return train_models_cached(str(dataset_id), df, target_column, feature_columns)


def _to_chart(v: dict) -> ChartMetadata:
    return ChartMetadata(
        chart_type=v.get("chart_type", "bar"),
        title=v.get("title", ""),
        subtitle=v.get("subtitle"),
        data=v.get("data"),
    )


def _to_confidence(c: dict) -> ConfidenceScore:
    return ConfidenceScore(level=c.get("level", "Medium"), score=c.get("score", 50.0))


def _simulation_ai_insight(service, ai_context: str, template: str) -> Optional[dict]:
    """
    Generate AI insight from simulation-specific context.

    Returns a structured dict parsed from Gemini's JSON response, or a
    graceful fallback dict on parse failure, or None when Gemini is unavailable.
    The dict is serialised directly by FastAPI — never returned as a string.
    """
    if not service.is_available():
        return None
    try:
        tmpl = get_template(template)
        sys_instruction, user_prompt = tmpl.format(ai_context, "")
        response_text, error_info = service.gemini.generate_content(
            prompt=user_prompt,
            system_instruction=sys_instruction,
            temperature=0.4,
            max_tokens=2000,
        )
        if error_info or not response_text:
            return None
        return _parse_simulation_insight(response_text)
    except Exception:
        return None


def _parse_simulation_insight(raw_text: str) -> dict:
    """
    Safely extract a structured dict from a Gemini response.

    Strategy:
    1. Strip markdown fences (```json ... ```).
    2. Direct JSON parse.
    3. Find first complete { ... } block and parse that.
    4. Return a graceful fallback dict if all else fails — never a broken string.
    """
    import json
    import re

    if not raw_text:
        return _ai_fallback("Empty response from AI")

    # Step 1 – strip markdown fences
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Step 2 – direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Step 3 – scan for first complete JSON object
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        result = json.loads(text[start: i + 1])
                        if isinstance(result, dict):
                            return result
                    except json.JSONDecodeError:
                        break

    # Step 4 – graceful fallback: wrap raw text in structured envelope
    summary = text[:500] if len(text) > 500 else text
    return _ai_fallback(summary)


def _ai_fallback(message: str) -> dict:
    """Return a structured fallback when AI response cannot be parsed."""
    return {
        "executive_summary": message,
        "key_findings": [],
        "recommended_actions": [],
        "risks_of_this_scenario": [],
        "executive_conclusion": "Review simulation results manually.",
        "confidence": "Low",
        "_parse_error": True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/{dataset_id}/train", response_model=SimulationOverviewResponse)
def train_simulation_model(
    dataset_id: uuid.UUID,
    body: SimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Train LR + RF models and return comparative metrics."""
    df = load_dataframe(dataset_id, db, current_user)
    target = _auto_target(df, body.target_column)
    pkg = _train(dataset_id, df, target, body.feature_columns)

    cmp = pkg.comparison()
    lr_m = cmp["linear_regression"]
    rf_m = cmp.get("random_forest")

    feature_stats = {
        col: {
            "mean": round(pkg.feature_means.get(col, 0.0), 4),
            "std": round(pkg.feature_stds.get(col, 0.0), 4),
            "min": round(pkg.feature_mins.get(col, 0.0), 4),
            "max": round(pkg.feature_maxs.get(col, 0.0), 4),
        }
        for col in pkg.feature_columns
    }

    chart = build_model_comparison_chart(cmp)
    return SimulationOverviewResponse(
        target_column=target,
        feature_columns=pkg.feature_columns,
        model_comparison=ModelComparisonSchema(
            selected_model=pkg.selected_model_name,
            linear_regression=ModelMetricsSchema(**lr_m),
            random_forest=ModelMetricsSchema(**rf_m) if rf_m else None,
            rows_trained=cmp["rows_trained"],
            train_r2=cmp["train_r2"],
            test_r2=cmp["test_r2"],
        ),
        feature_stats=feature_stats,
        visualizations=[_to_chart(chart)],
    )


@router.post("/{dataset_id}/single", response_model=SingleSimulationResponse)
def single_variable_simulation(
    dataset_id: uuid.UUID,
    body: SingleSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """What-If: change ONE variable and predict the new target value."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    target = _auto_target(df, body.target_column)
    pkg = _train(dataset_id, df, target, body.feature_columns)

    result = simulate_single(pkg, body.variable, body.new_value, body.base_overrides)
    ai_context = result.pop("_ai_context", "")

    chart = build_single_simulation_chart(result)
    ai_txt = _simulation_ai_insight(service, ai_context, "simulation_insight")

    pi = result["prediction_interval"]
    return SingleSimulationResponse(
        **{k: v for k, v in result.items()
           if k not in ("prediction_interval", "confidence", "recommendations")},
        prediction_interval=PredictionInterval(**pi),
        confidence=_to_confidence(result["confidence"]),
        recommendations=result.get("recommendations", []),
        visualizations=[_to_chart(chart)],
        ai_insight=ai_txt,
    )


@router.post("/{dataset_id}/multi", response_model=MultiSimulationResponse)
def multi_variable_simulation(
    dataset_id: uuid.UUID,
    body: MultiSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """What-If: change MULTIPLE variables simultaneously and predict the new target."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    target = _auto_target(df, body.target_column)
    pkg = _train(dataset_id, df, target, body.feature_columns)

    result = simulate_multi(pkg, body.scenario)
    ai_context = result.pop("_ai_context", "")

    chart = build_multi_simulation_chart(result)
    ai_txt = _simulation_ai_insight(service, ai_context, "simulation_insight")

    pi = result["prediction_interval"]
    impacts = [VariableImpact(**i) for i in result.get("variable_impacts", [])]

    return MultiSimulationResponse(
        **{k: v for k, v in result.items()
           if k not in ("prediction_interval", "variable_impacts",
                        "confidence", "recommendations")},
        prediction_interval=PredictionInterval(**pi),
        variable_impacts=impacts,
        confidence=_to_confidence(result["confidence"]),
        recommendations=result.get("recommendations", []),
        visualizations=[_to_chart(chart)],
        ai_insight=ai_txt,
    )


@router.post("/{dataset_id}/sensitivity", response_model=SensitivityResponse)
def sensitivity_analysis(
    dataset_id: uuid.UUID,
    body: SensitivityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sweep every feature variable across its range and rank by sensitivity."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    target = _auto_target(df, body.target_column)
    pkg = _train(dataset_id, df, target, body.feature_columns)

    result = run_sensitivity_analysis(
        pkg,
        columns=body.columns,
        n_steps=max(5, min(50, body.n_steps)),
        top_n=max(1, min(20, body.top_n)),
    )
    ai_context = result.pop("_ai_context", "")

    bar_chart = build_sensitivity_chart(result)
    sweep_charts = build_sensitivity_sweep_charts(result)
    charts = [_to_chart(bar_chart)] + [_to_chart(c) for c in sweep_charts]

    ai_txt = _simulation_ai_insight(service, ai_context, "sensitivity_insight")
    ranking = [SensitivityRanking(**r) for r in result.get("sensitivity_ranking", [])]

    return SensitivityResponse(
        target_column=result["target_column"],
        model_used=result["model_used"],
        model_r2=result["model_r2"],
        confidence=_to_confidence(result["confidence"]) if result.get("confidence") else None,
        columns_analysed=result["columns_analysed"],
        sensitivity_ranking=ranking,
        most_sensitive=result.get("most_sensitive"),
        least_sensitive=result.get("least_sensitive"),
        recommendations=result.get("recommendations", []),
        visualizations=charts,
        ai_insight=ai_txt,
    )


@router.post("/{dataset_id}/compare", response_model=ScenarioComparisonResponse)
def compare_what_if_scenarios(
    dataset_id: uuid.UUID,
    body: ScenarioComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare multiple named what-if scenarios side-by-side."""
    service = get_ai_service()
    df = load_dataframe(dataset_id, db, current_user)
    target = _auto_target(df, body.target_column)
    pkg = _train(dataset_id, df, target, body.feature_columns)

    scenario_dicts = [{"name": s.name, "variables": s.variables} for s in body.scenarios]
    result = compare_scenarios(pkg, scenario_dicts)
    ai_context = result.pop("_ai_context", "")

    chart = build_scenario_comparison_chart(result)
    ai_txt = _simulation_ai_insight(service, ai_context, "scenario_comparison_insight")

    scenario_results = [ScenarioResult(**r) for r in result.get("results", [])]

    return ScenarioComparisonResponse(
        target_column=result["target_column"],
        baseline_prediction=result["baseline_prediction"],
        model_used=result["model_used"],
        model_r2=result["model_r2"],
        confidence=_to_confidence(result["confidence"]),
        scenario_count=result["scenario_count"],
        results=scenario_results,
        best_scenario=result.get("best_scenario"),
        worst_scenario=result.get("worst_scenario"),
        chart_data=result["chart_data"],
        recommendations=result.get("recommendations", []),
        visualizations=[_to_chart(chart)],
        ai_insight=ai_txt,
    )
