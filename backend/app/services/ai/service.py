"""
Enterprise AI Service — Module 6.

Orchestrates context building, prompt selection, Gemini generation,
and structured response parsing. All analysis endpoints delegate here.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from app.core.logging import get_logger
from app.services.ai.client import get_gemini_client
from app.services.ai.context_builder import build_complete_context, format_context_for_prompt
from app.services.ai.prompt_engine import get_template
from app.services.ai.response_parser import parse_to_response

logger = get_logger(__name__)


class AIService:
    """Enterprise AI service for business intelligence and decision support."""

    def __init__(self):
        self.gemini = get_gemini_client()

    # ─────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        return self.gemini.is_available()

    def get_status(self) -> dict:
        return self.gemini.get_status()

    def analyze_dataset(
        self,
        df: pd.DataFrame,
        dataset_name: str,
        template_name: str = "business_insights",
        custom_query: str = "",
    ) -> dict:
        """
        Core analysis pipeline:
        1. Build rich analytics context from EDA / KPI / Forecasting.
        2. Format context as structured text for Gemini.
        3. Call Gemini with enterprise prompt.
        4. Parse JSON response into canonical schema.
        5. Build visualization metadata from context.
        """
        try:
            # Step 1 — Analytics context (Gemini never sees raw CSV)
            context = build_complete_context(df, dataset_name)
            context_text = format_context_for_prompt(context)

            # Step 2 — Prompt template
            template = get_template(template_name)
            system_instruction, user_prompt = template.format(context_text, custom_query)

            # Step 3 — Gemini generation
            response_text, error_info = self._call_gemini(system_instruction, user_prompt)

            if error_info:
                return self._error_response(error_info, template_name, context)

            # Step 4+5 — Parse + visualizations
            return parse_to_response(response_text, template_name, context)

        except Exception as exc:
            logger.error(
                "ai_analysis_failed",
                template=template_name,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return self._exception_response(exc, template_name)

    # Convenience methods — each maps to a specific prompt template

    def generate_executive_summary(self, df: pd.DataFrame, dataset_name: str) -> dict:
        return self.analyze_dataset(df, dataset_name, "executive_summary")

    def get_recommendations(self, df: pd.DataFrame, dataset_name: str) -> dict:
        return self.analyze_dataset(df, dataset_name, "recommendations")

    def identify_risks(self, df: pd.DataFrame, dataset_name: str) -> dict:
        return self.analyze_dataset(df, dataset_name, "risk_analysis")

    def identify_opportunities(self, df: pd.DataFrame, dataset_name: str) -> dict:
        return self.analyze_dataset(df, dataset_name, "opportunity_analysis")

    def detect_anomalies(self, df: pd.DataFrame, dataset_name: str) -> dict:
        return self.analyze_dataset(df, dataset_name, "anomaly_detection")

    def answer_question(self, df: pd.DataFrame, dataset_name: str, question: str) -> dict:
        return self.analyze_dataset(df, dataset_name, "question_answering", question)

    # ─────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────

    def _call_gemini(
        self, system_instruction: str, user_prompt: str
    ) -> tuple[str, Optional[dict]]:
        """Call Gemini, returning (text, error_info)."""
        if not self.is_available():
            return "", {"error": "Gemini API not configured — set GEMINI_API_KEY in .env"}

        response_text, error_info = self.gemini.generate_content(
            prompt=user_prompt,
            system_instruction=system_instruction,
            temperature=0.4,   # Lower temperature → more consistent JSON
            max_tokens=3000,
        )

        if error_info:
            logger.warning("gemini_call_failed", error_info=error_info)
            return "", error_info

        return response_text, None

    def _error_response(
        self, error_info: dict, template_name: str, context: dict
    ) -> dict:
        """Return a structured error response that still satisfies the schema."""
        error_msg = error_info.get("error", "Unknown error")
        logger.error("ai_error_response", template=template_name, error=error_msg)

        # Still include context-derived insights as fallback
        eda_ins = (
            (context.get("eda", {}).get("insights") or {}).get("insights", [])
        )
        health = context.get("health_score", {})

        return {
            "summary": f"AI analysis unavailable: {error_msg}",
            "insights": eda_ins[:8] if eda_ins else [f"AI Error: {error_msg}"],
            "recommendations": [],
            "visualizations": [],
            "metadata": {
                "template": template_name,
                "parse_error": False,
                "insight_count": len(eda_ins),
                "recommendation_count": 0,
                "business_condition": None,
                "risk_level": None,
                "confidence": None,
                "health_score": health,
                "structured_data": {},
                "error": error_msg,
                "error_info": error_info,
            },
        }

    def _exception_response(self, exc: Exception, template_name: str) -> dict:
        """Return a structured exception response."""
        return {
            "summary": f"Analysis error: {type(exc).__name__}",
            "insights": [str(exc)],
            "recommendations": [],
            "visualizations": [],
            "metadata": {
                "template": template_name,
                "parse_error": False,
                "insight_count": 1,
                "recommendation_count": 0,
                "business_condition": None,
                "risk_level": None,
                "confidence": None,
                "health_score": {},
                "structured_data": {},
                "exception": str(exc),
            },
        }


# ─────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────

_ai_service: AIService | None = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
