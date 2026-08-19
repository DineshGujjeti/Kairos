"""
AI Assistant — conversational help and support, distinct from the
board-report-style prompt templates in prompt_engine.py.

Every other AI feature in this platform (Root Cause narratives,
Decision recommendations, Executive advisories) asks Gemini for
structured JSON matching a fixed schema. The assistant is different on
purpose: it's a plain conversational chat -- a user asks "how do I
forecast without a date column?" or "what does this confidence score
mean?" and gets a normal sentence back, not a JSON object to be parsed
and rendered into cards.

Two things make this assistant useful even when Gemini isn't
configured, or the request fails:
  1. PRODUCT_KNOWLEDGE is written into every prompt as grounding, so the
     assistant explains *this specific product* accurately instead of
     generic BI-tool advice.
  2. answer_assistant_query() never raises and never returns an error
     the user has to interpret -- on any failure (no API key, network
     error, empty response) it degrades to a small keyword-matched FAQ
     lookup against the same PRODUCT_KNOWLEDGE, so the widget always
     replies with *something* genuinely relevant rather than "AI
     unavailable."
"""
from __future__ import annotations

import re

PRODUCT_KNOWLEDGE = """
Kairos is an AI-powered enterprise decision intelligence platform. A person uploads a business
dataset (CSV, Excel, or JSON, from any domain -- sales, HR, finance, healthcare, marketing,
inventory, anything) and Kairos automatically figures out its structure and generates analysis.
There is no dataset-type selection step -- Kairos detects the business domain, key measures,
dimensions, and date columns on its own after upload.

Pages in the product:
- Datasets: upload files here. After upload, Kairos shows what it detected (business domain,
  row/column counts, which columns are measures vs. dimensions vs. dates) before you continue.
- KPI Analytics: a small set of the metrics that actually matter for this dataset, each with a
  plain-language trend description (e.g. "Revenue is up 12% compared to the earlier period").
  Raw per-column statistics are available under "Advanced" for people who want the full table.
- EDA (Exploratory Data Analysis): automated data-quality scoring, outlier detection, and
  correlation analysis.
- Forecasting: predicts future values for a key metric. Works even without a date column (it
  falls back to using row order as a timeline, and always says so explicitly). If forecasting
  isn't possible for a dataset (too few rows, no numeric columns), it explains why instead of
  showing a blank chart.
- Root Cause Analysis: explains WHY a metric is behaving the way it is -- which variables are
  driving it, in plain language, with a confidence score.
- What-If Simulation: lets you try adjusting a variable (e.g. "what if I increase marketing
  spend by 20%?") and see the predicted effect on a key metric, using sliders on the variables
  that matter most rather than requiring you to know column names.
- Decision Advisor: automatically generates prioritized, scored recommendations (High/Medium/Low
  priority, with expected ROI and effort) as soon as a dataset is selected -- no button to press.
- Executive Advisor: a board-level report -- immediate actions, a 30/90-day plan, risks, and
  expected ROI, generated on request.
- History: past decision sessions.
- Settings: account info and AI configuration status.

General notes:
- Every page needs a dataset selected first (pick one from the dropdown at the top of the page,
  or upload one from the Datasets page).
- AI-generated insights (Decision Advisor, Executive Advisor, Root Cause explanations) require a
  Gemini API key to be configured; without one, the platform still works using its built-in
  statistical analysis, just without the AI-written narrative on top.
- Confidence scores throughout the product (0-100, High/Medium/Low) reflect how much data was
  available and how strong the statistical signal was -- not a guarantee of correctness.
""".strip()

_FAQ_KEYWORDS: list[tuple[list[str], str]] = [
    (["upload", "csv", "excel", "file", "import"],
     "Go to the Datasets page and drag in a CSV, Excel, or JSON file. Kairos detects the "
     "structure and business domain automatically -- there's no need to tell it what kind "
     "of data it is."),
    (["forecast", "predict", "future", "trend"],
     "The Forecasting page predicts future values for a key metric. It works even without a "
     "date column -- it'll use row order as a stand-in timeline and tell you when it's doing "
     "that. If it says forecasting isn't available, it's usually because there isn't enough "
     "data yet (it needs at least 10 rows)."),
    (["kpi", "metric", "dashboard"],
     "The KPI Analytics page shows a handful of the metrics that matter most for your "
     "dataset, each with a plain-language trend. Raw per-column stats are under the "
     "\"Advanced\" section if you need the full table."),
    (["root cause", "why", "driver", "explain"],
     "Root Cause Analysis identifies which variables are driving a metric's behavior, ranked "
     "by importance, with a plain-language explanation and a confidence score."),
    (["what if", "simulate", "simulation", "scenario"],
     "What-If Simulation lets you try adjusting the variables that matter most and see the "
     "predicted effect, using sliders rather than requiring you to pick raw column names."),
    (["decision", "recommend", "suggestion", "advisor"],
     "The Decision Advisor generates prioritized recommendations automatically as soon as "
     "you select a dataset -- no button to press. Each one is scored on impact, effort, and "
     "expected ROI."),
    (["confidence", "score", "accuracy", "reliable"],
     "Confidence scores (0-100, or High/Medium/Low) reflect how much data was available and "
     "how strong the statistical pattern was. They're a guide to how much to trust a result, "
     "not a guarantee."),
    (["ai", "gemini", "api key", "not working", "unavailable"],
     "Some features (AI-written narratives in Decision Advisor, Executive Advisor, and Root "
     "Cause) need a Gemini API key configured in Settings. Without one, the platform still "
     "runs its full statistical analysis -- you just won't get the AI-written summary on top."),
]

_DEFAULT_FALLBACK = (
    "I'm not sure about that specific question, but here's what I can tell you: Kairos "
    "automatically analyzes any business dataset you upload -- KPIs, forecasting, root cause "
    "analysis, what-if simulation, and decision recommendations, all without you needing to "
    "configure anything. Try asking about a specific page, like \"how does forecasting work\" "
    "or \"what is root cause analysis.\""
)


def _keyword_fallback(message: str) -> str:
    lowered = message.lower()
    for keywords, answer in _FAQ_KEYWORDS:
        if any(k in lowered for k in keywords):
            return answer
    return _DEFAULT_FALLBACK


def _build_prompt(
    message: str,
    history: list[dict],
    dataset_summary: str | None,
    current_page: str | None,
) -> str:
    parts = [f"Product knowledge:\n{PRODUCT_KNOWLEDGE}"]

    if dataset_summary:
        parts.append(f"\nThe user currently has this dataset selected:\n{dataset_summary}")

    if current_page:
        parts.append(f"\nThe user is currently on the '{current_page}' page.")

    if history:
        convo = "\n".join(
            f"{'User' if h.get('role') == 'user' else 'Assistant'}: {h.get('content', '')}"
            for h in history[-6:]  # last few turns only -- keep the prompt small
        )
        parts.append(f"\nConversation so far:\n{convo}")

    parts.append(f"\nUser's new message: {message}")
    return "\n".join(parts)


_SYSTEM_INSTRUCTION = (
    "You are the in-app help assistant for Kairos, an AI decision intelligence platform. "
    "Answer the user's question in 1-4 plain, friendly sentences -- no markdown, no bullet "
    "lists unless truly necessary, no JSON. Be concrete and specific to Kairos using the "
    "product knowledge provided; don't give generic advice about business intelligence tools "
    "in general. If the user asks something outside what Kairos does, say so briefly and "
    "redirect them to what the product can help with. Never invent features that aren't in "
    "the product knowledge you were given."
)


def answer_assistant_query(
    message: str,
    ai_service,
    history: list[dict] | None = None,
    dataset_summary: str | None = None,
    current_page: str | None = None,
) -> dict:
    """
    Returns {"reply": str, "source": "ai" | "fallback"}.

    Never raises: any failure (Gemini not configured, network error,
    empty response) degrades to a keyword-matched FAQ answer built from
    the same PRODUCT_KNOWLEDGE, so the chat widget always has something
    genuinely useful to say.
    """
    message = (message or "").strip()
    if not message:
        return {"reply": "What would you like help with?", "source": "fallback"}

    if ai_service is not None and ai_service.is_available():
        try:
            prompt = _build_prompt(message, history or [], dataset_summary, current_page)
            text, error_info = ai_service.gemini.generate_content(
                prompt=prompt,
                system_instruction=_SYSTEM_INSTRUCTION,
                temperature=0.5,
                max_tokens=400,
            )
            cleaned = (text or "").strip()
            if not error_info and cleaned:
                return {"reply": cleaned, "source": "ai"}
        except Exception:
            pass  # fall through to keyword fallback below

    return {"reply": _keyword_fallback(message), "source": "fallback"}
