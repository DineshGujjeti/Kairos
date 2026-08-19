"""
Enterprise AI Prompt Engine — Module 6.

All prompts are defined here. No prompts are hardcoded inside services.

IMPORTANT: JSON example blocks inside user_prompt strings use {{ and }}
to escape literal braces — Python str.format() is used for {context}
and {query} substitution only.
"""
from __future__ import annotations


class PromptTemplate:
    """Reusable prompt template producing structured JSON output."""

    def __init__(self, name: str, system_instruction: str, user_prompt: str):
        self.name = name
        self.system_instruction = system_instruction
        self.user_prompt = user_prompt

    def format(self, context: str, query: str = "") -> tuple[str, str]:
        user = self.user_prompt.format(context=context, query=query)
        return self.system_instruction, user


# ─────────────────────────────────────────────────────────────
# Shared constants
# ─────────────────────────────────────────────────────────────

_JSON_INSTRUCTION = (
    "\n\nCRITICAL INSTRUCTIONS:\n"
    "- Return ONLY valid JSON. No markdown fences, no prose before or after.\n"
    "- If a numeric field is unknown, use null.\n"
    "- If a list field has nothing to say, use [].\n"
    "- Confidence values are integers 0-100.\n"
    "- Be specific and reference the actual metrics provided above.\n"
    "- Write like a partner at McKinsey, Deloitte, or Gartner.\n"
)

_SYSTEM_BASE = (
    "You are a Senior Partner at an elite management consulting firm "
    "with deep expertise in enterprise analytics, financial performance, "
    "operational excellence, and data-driven decision making. "
    "You have reviewed the analytics produced by Kairos and must now "
    "deliver a structured, board-level intelligence report. "
    "Your output is ALWAYS valid JSON — never prose, never markdown fences."
)


# ─────────────────────────────────────────────────────────────
# 1. Executive Summary
# ─────────────────────────────────────────────────────────────

EXECUTIVE_SUMMARY = PromptTemplate(
    name="executive_summary",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are reviewing the following enterprise analytics report:\n\n"
        "{context}"
        + _JSON_INSTRUCTION +
        "\n\nReturn exactly this JSON structure (replace all placeholder values):\n"
        '{{\n'
        '  "executive_summary": "2-3 sentences on business situation, performance, and risk.",\n'
        '  "business_condition": "one of: Excellent | Strong | Stable | Needs Attention | Critical",\n'
        '  "key_metrics": [\n'
        '    {{"metric": "metric name", "value": "value with unit", "signal": "positive|neutral|negative"}}\n'
        "  ],\n"
        '  "headline_findings": [\n'
        '    "Specific finding referencing actual numbers from the analytics"\n'
        "  ],\n"
        '  "strategic_priorities": [\n'
        '    "Specific priority based on the data"\n'
        "  ],\n"
        '  "executive_conclusion": "One confident concluding statement for the board.",\n'
        '  "confidence": 85\n'
        "}}"
    ),
)


# ─────────────────────────────────────────────────────────────
# 2. Business Insights
# ─────────────────────────────────────────────────────────────

BUSINESS_INSIGHTS = PromptTemplate(
    name="business_insights",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "Enterprise analytics context:\n\n"
        "{context}"
        + _JSON_INSTRUCTION +
        "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Overall business intelligence summary in 2 sentences.",\n'
        '  "key_insights": [\n'
        '    {{\n'
        '      "title": "Insight title",\n'
        '      "finding": "What the data shows — reference specific numbers.",\n'
        '      "business_impact": "What this means for the business.",\n'
        '      "recommended_action": "What leadership should do about it.",\n'
        '      "priority": "High|Medium|Low",\n'
        '      "confidence": 80\n'
        '    }}\n'
        "  ],\n"
        '  "performance_summary": {{\n'
        '    "strengths": ["strength with data reference"],\n'
        '    "weaknesses": ["weakness with data reference"]\n'
        "  }},\n"
        '  "executive_conclusion": "One sentence closing statement.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)


# ─────────────────────────────────────────────────────────────
# 3. Recommendations
# ─────────────────────────────────────────────────────────────

RECOMMENDATIONS = PromptTemplate(
    name="recommendations",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "Enterprise analytics:\n\n"
        "{context}"
        + _JSON_INSTRUCTION +
        "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Why these recommendations matter — 1-2 sentences.",\n'
        '  "recommendations": [\n'
        '    {{\n'
        '      "title": "Recommendation title",\n'
        '      "problem": "What specific data signal identified this problem.",\n'
        '      "business_impact": "Financial or operational impact if unaddressed.",\n'
        '      "recommended_action": "Precise, actionable step for leadership.",\n'
        '      "expected_benefit": "Quantified or qualified expected outcome.",\n'
        '      "implementation_effort": "Low|Medium|High",\n'
        '      "priority": "Critical|High|Medium|Low",\n'
        '      "confidence": 80\n'
        '    }}\n'
        "  ],\n"
        '  "priority_matrix": {{\n'
        '    "immediate": ["action within 30 days"],\n'
        '    "short_term": ["action within 90 days"],\n'
        '    "long_term": ["action within 12 months"]\n'
        "  }},\n"
        '  "executive_conclusion": "One sentence closing statement.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)


# ─────────────────────────────────────────────────────────────
# 4. Risk Analysis
# ─────────────────────────────────────────────────────────────

RISK_ANALYSIS = PromptTemplate(
    name="risk_analysis",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "Enterprise analytics:\n\n"
        "{context}"
        + _JSON_INSTRUCTION +
        "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Overall risk posture assessment in 1-2 sentences.",\n'
        '  "risk_level": "Critical|High|Medium|Low",\n'
        '  "business_risks": [\n'
        '    {{\n'
        '      "risk_title": "Risk name",\n'
        '      "description": "What the data shows and why this is a risk.",\n'
        '      "affected_kpis": ["KPI names that would be impacted"],\n'
        '      "likelihood": "High|Medium|Low",\n'
        '      "severity": "Critical|High|Medium|Low",\n'
        '      "mitigation": "Specific mitigation action.",\n'
        '      "urgency": "Immediate|Short-term|Monitor"\n'
        '    }}\n'
        "  ],\n"
        '  "data_quality_risks": [\n'
        '    "Specific data quality issue that could distort decisions"\n'
        "  ],\n"
        '  "executive_conclusion": "One sentence closing risk statement.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)


# ─────────────────────────────────────────────────────────────
# 5. Opportunity Analysis
# ─────────────────────────────────────────────────────────────

OPPORTUNITY_ANALYSIS = PromptTemplate(
    name="opportunity_analysis",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "Enterprise analytics:\n\n"
        "{context}"
        + _JSON_INSTRUCTION +
        "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Growth opportunity landscape in 1-2 sentences.",\n'
        '  "growth_opportunities": [\n'
        '    {{\n'
        '      "opportunity_title": "Opportunity name",\n'
        '      "description": "What the data reveals as an opportunity.",\n'
        '      "revenue_drivers": ["specific metrics that support this"],\n'
        '      "recommended_action": "How to capitalize on this.",\n'
        '      "estimated_impact": "Qualitative or quantitative expected benefit.",\n'
        '      "implementation_difficulty": "Low|Medium|High",\n'
        '      "time_to_value": "Immediate|3 months|6 months|12+ months",\n'
        '      "confidence": 75\n'
        '    }}\n'
        "  ],\n"
        '  "market_signals": [\n'
        '    "Positive signal from the data that suggests opportunity"\n'
        "  ],\n"
        '  "executive_conclusion": "One sentence growth recommendation.",\n'
        '  "confidence": 75\n'
        "}}"
    ),
)


# ─────────────────────────────────────────────────────────────
# 6. Anomaly Detection
# ─────────────────────────────────────────────────────────────

ANOMALY_DETECTION = PromptTemplate(
    name="anomaly_detection",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "Enterprise analytics (including outlier and correlation data):\n\n"
        "{context}"
        + _JSON_INSTRUCTION +
        "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Anomaly situation overview in 1-2 sentences.",\n'
        '  "anomaly_count": 0,\n'
        '  "anomalies": [\n'
        '    {{\n'
        '      "anomaly_title": "What is unusual",\n'
        '      "description": "What the data shows — reference actual numbers.",\n'
        '      "affected_columns": ["column names"],\n'
        '      "possible_causes": ["cause 1", "cause 2"],\n'
        '      "correlated_variables": ["variable that may be driving this"],\n'
        '      "business_impact": "What this means for operations or revenue.",\n'
        '      "affected_kpis": ["KPIs impacted"],\n'
        '      "recommended_investigation": "What to do next.",\n'
        '      "severity": "Critical|High|Medium|Low"\n'
        '    }}\n'
        "  ],\n"
        '  "root_cause_hypotheses": [\n'
        '    "Hypothesis grounded in the analytics provided"\n'
        "  ],\n"
        '  "executive_conclusion": "One sentence anomaly risk statement.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)


# ─────────────────────────────────────────────────────────────
# 7. Question Answering
# ─────────────────────────────────────────────────────────────

QUESTION_ANSWERING = PromptTemplate(
    name="question_answering",
    system_instruction=(
        "You are a Senior Business Analyst and data expert. "
        "You have full access to the analytics below and must answer "
        "the user's business question precisely, citing actual figures. "
        "Your output is ALWAYS valid JSON — never prose, never markdown fences."
    ),
    user_prompt=(
        "Enterprise analytics context:\n\n"
        "{context}\n\n"
        "Business Question: {query}"
        + _JSON_INSTRUCTION +
        "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "question": "restate the question here",\n'
        '  "executive_summary": "Direct answer to the question in 1-2 sentences.",\n'
        '  "detailed_answer": "Full analytical response referencing specific metrics, trends, and data points.",\n'
        '  "supporting_evidence": [\n'
        '    "Specific metric or data point that supports the answer"\n'
        "  ],\n"
        '  "caveats": [\n'
        '    "Limitation or caveat if the data does not fully answer the question"\n'
        "  ],\n"
        '  "follow_up_questions": [\n'
        '    "Related question the business should also investigate"\n'
        "  ],\n"
        '  "confidence": 80\n'
        "}}"
    ),
)


# ─────────────────────────────────────────────────────────────
# 8. Root Cause Analysis
# ─────────────────────────────────────────────────────────────

ROOT_CAUSE_ANALYSIS = PromptTemplate(
    name="root_cause_analysis",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "Enterprise analytics:\n\n"
        "{context}\n\n"
        "Issue to investigate: {query}"
        + _JSON_INSTRUCTION +
        "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Root cause situation in 1-2 sentences.",\n'
        '  "root_causes": [\n'
        '    {{\n'
        '      "cause": "Root cause description",\n'
        '      "evidence": "Data that supports this hypothesis.",\n'
        '      "correlated_variables": ["variable names"],\n'
        '      "likelihood": "High|Medium|Low",\n'
        '      "business_impact": "Impact on operations or revenue."\n'
        '    }}\n'
        "  ],\n"
        '  "affected_kpis": ["KPI names impacted by this issue"],\n'
        '  "recommended_actions": [\n'
        '    "Specific action to address root cause"\n'
        "  ],\n"
        '  "executive_conclusion": "One sentence closing.",\n'
        '  "confidence": 75\n'
        "}}"
    ),
)


# ─────────────────────────────────────────────────────────────
# Template registry
# ─────────────────────────────────────────────────────────────

TEMPLATES: dict[str, PromptTemplate] = {
    "executive_summary": EXECUTIVE_SUMMARY,
    "business_insights": BUSINESS_INSIGHTS,
    "root_cause_analysis": ROOT_CAUSE_ANALYSIS,
    "recommendations": RECOMMENDATIONS,
    "risk_analysis": RISK_ANALYSIS,
    "opportunity_analysis": OPPORTUNITY_ANALYSIS,
    "question_answering": QUESTION_ANSWERING,
    "anomaly_detection": ANOMALY_DETECTION,
}


def get_template(name: str) -> PromptTemplate:
    if name not in TEMPLATES:
        raise ValueError(f"Unknown template: '{name}'. Available: {list(TEMPLATES)}")
    return TEMPLATES[name]


def list_templates() -> list[str]:
    return list(TEMPLATES.keys())


# ─────────────────────────────────────────────────────────────
# Module 7: Root Cause Intelligence prompt templates
# ─────────────────────────────────────────────────────────────

ROOT_CAUSE = PromptTemplate(
    name="root_cause",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are analysing why a business metric is behaving as observed.\n\n"
        "Enterprise analytics and root cause pre-analysis:\n\n"
        "{context}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "1-2 sentences: what is the metric doing and the primary reason why.",\n'
        '  "primary_root_cause": "The single most important driver with a business explanation.",\n'
        '  "root_causes": [\n'
        '    {{\n'
        '      "cause": "Root cause title",\n'
        '      "evidence": "Specific data evidence (numbers, correlations, trends).",\n'
        '      "business_explanation": "Plain-language explanation a CEO would understand.",\n'
        '      "correlated_variables": ["variable names"],\n'
        '      "likelihood": "High|Medium|Low",\n'
        '      "business_impact": "Financial or operational impact.",\n'
        '      "recommended_action": "Specific next step.",\n'
        '      "confidence": 80\n'
        '    }}\n'
        "  ],\n"
        '  "affected_kpis": ["KPI names impacted"],\n'
        '  "why_chain": [\n'
        '    {{"level": 1, "question": "WHY?", "answer": "Because X drove Y by Z%"}}\n'
        "  ],\n"
        '  "data_limitations": ["Any caveat about data quality or coverage"],\n'
        '  "executive_conclusion": "One sentence closing.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)

DRIVER_ANALYSIS = PromptTemplate(
    name="driver_analysis",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are identifying which variables DRIVE the target business metric.\n\n"
        "Driver analysis and analytics context:\n\n"
        "{context}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Which variables most strongly drive the metric and why.",\n'
        '  "target_metric": "name of the metric being explained",\n'
        '  "key_drivers": [\n'
        '    {{\n'
        '      "driver": "variable name",\n'
        '      "importance": "High|Medium|Low",\n'
        '      "direction": "positive|negative",\n'
        '      "business_interpretation": "Plain-language explanation of what this driver means.",\n'
        '      "contribution_pct": 30,\n'
        '      "supporting_evidence": "Data reference (correlation value, RF importance, etc.)",\n'
        '      "confidence": 80\n'
        '    }}\n'
        "  ],\n"
        '  "revenue_drivers": ["Top drivers linked to revenue"],\n'
        '  "risk_drivers": ["Drivers that represent a risk if they move adversely"],\n'
        '  "hidden_drivers": ["Non-obvious drivers the business may not be monitoring"],\n'
        '  "executive_conclusion": "One sentence action recommendation.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)

CONTRIBUTION_ANALYSIS = PromptTemplate(
    name="contribution_analysis",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are explaining HOW MUCH each variable contributed to the observed metric value.\n\n"
        "Contribution breakdown and analytics context:\n\n"
        "{context}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Overall contribution narrative in 1-2 sentences.",\n'
        '  "target_metric": "metric name",\n'
        '  "positive_contributors": [\n'
        '    {{\n'
        '      "variable": "name",\n'
        '      "contribution_pct": 40,\n'
        '      "business_impact": "What this positive contribution means.",\n'
        '      "confidence": 80\n'
        '    }}\n'
        "  ],\n"
        '  "negative_contributors": [\n'
        '    {{\n'
        '      "variable": "name",\n'
        '      "contribution_pct": -20,\n'
        '      "business_impact": "What this drag means for the business.",\n'
        '      "confidence": 75\n'
        '    }}\n'
        "  ],\n"
        '  "net_assessment": "Is the overall contribution balance positive or negative for the business?",\n'
        '  "recommended_actions": ["Action to amplify positive contributors or reduce negative ones"],\n'
        '  "executive_conclusion": "One sentence closing.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)

ANOMALY_EXPLANATION = PromptTemplate(
    name="anomaly_explanation",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are explaining WHY anomalies occurred in the business data.\n\n"
        "Anomaly detection results and analytics:\n\n"
        "{context}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "What anomalies exist and why they are important.",\n'
        '  "anomaly_count": 0,\n'
        '  "anomalies": [\n'
        '    {{\n'
        '      "variable": "column name",\n'
        '      "description": "What is anomalous and to what degree.",\n'
        '      "likely_business_cause": "Most probable business explanation (not data error).",\n'
        '      "alternative_causes": ["Other possible explanations"],\n'
        '      "correlated_variables": ["Variables that also showed unusual values"],\n'
        '      "business_impact": "Revenue, operations, or customer impact.",\n'
        '      "affected_kpis": ["KPI names"],\n'
        '      "investigation_steps": ["What to check first"],\n'
        '      "severity": "Critical|High|Medium|Low",\n'
        '      "confidence": 80\n'
        '    }}\n'
        "  ],\n"
        '  "systemic_risk": "Is this isolated or a systemic pattern?",\n'
        '  "executive_conclusion": "One sentence risk statement.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)

EXECUTIVE_WHY = PromptTemplate(
    name="executive_why",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "A business executive has asked the following question about their data.\n"
        "Answer in board-level language using the analytics provided.\n\n"
        "Analytics context:\n\n"
        "{context}\n\n"
        "Executive Question: {query}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "question": "restate the question",\n'
        '  "direct_answer": "1-2 sentence direct answer a CEO can act on immediately.",\n'
        '  "explanation": "Detailed explanation with specific data references.",\n'
        '  "causal_chain": [\n'
        '    {{"step": 1, "because": "Specific data-grounded reason"}}\n'
        "  ],\n"
        '  "supporting_evidence": ["Metric or data point that supports this answer"],\n'
        '  "business_implications": ["What this means for revenue, operations, or strategy"],\n'
        '  "recommended_next_steps": ["Specific action with expected outcome"],\n'
        '  "caveats": ["What we cannot conclude from the data"],\n'
        '  "confidence": 80\n'
        "}}"
    ),
)

BUSINESS_DIAGNOSTICS = PromptTemplate(
    name="business_diagnostics",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "Perform a comprehensive business diagnostic — identify what is working, "
        "what is broken, and what needs urgent attention.\n\n"
        "Full analytics context:\n\n"
        "{context}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Overall business health diagnostic in 2-3 sentences.",\n'
        '  "business_condition": "Excellent|Strong|Stable|Needs Attention|Critical",\n'
        '  "what_is_working": [\n'
        '    {{"finding": "specific positive finding", "evidence": "data reference", "impact": "business impact"}}\n'
        "  ],\n"
        '  "what_is_broken": [\n'
        '    {{\n'
        '      "issue": "specific problem", "root_cause": "WHY this is happening",\n'
        '      "evidence": "data reference", "urgency": "Immediate|Short-term|Monitor"\n'
        '    }}\n'
        "  ],\n"
        '  "operational_bottlenecks": ["Process or metric that is constraining performance"],\n'
        '  "revenue_leakage": ["Areas where revenue or value is being lost"],\n'
        '  "growth_signals": ["Positive leading indicators"],\n'
        '  "priority_actions": [\n'
        '    {{\n'
        '      "action": "specific action", "expected_outcome": "measurable result",\n'
        '      "timeframe": "30 days|90 days|6 months", "priority": "Critical|High|Medium"\n'
        '    }}\n'
        "  ],\n"
        '  "executive_conclusion": "One sentence board-level recommendation.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)


# ── Update template registry with Module 7 additions ─────────

TEMPLATES["root_cause"] = ROOT_CAUSE
TEMPLATES["driver_analysis"] = DRIVER_ANALYSIS
TEMPLATES["contribution_analysis"] = CONTRIBUTION_ANALYSIS
TEMPLATES["anomaly_explanation"] = ANOMALY_EXPLANATION
TEMPLATES["executive_why"] = EXECUTIVE_WHY
TEMPLATES["business_diagnostics"] = BUSINESS_DIAGNOSTICS


# ─────────────────────────────────────────────────────────────
# Module 8: What-If Simulation prompt templates
# ─────────────────────────────────────────────────────────────

SIMULATION_INSIGHT = PromptTemplate(
    name="simulation_insight",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are interpreting what-if simulation results for a business executive.\n\n"
        "Simulation results and context:\n\n"
        "{context}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Plain-language explanation of what the simulation reveals in 2 sentences.",\n'
        '  "business_interpretation": "What this scenario means for the business — specific and actionable.",\n'
        '  "key_findings": [\n'
        '    {{"finding": "specific finding", "implication": "business implication", "confidence": "High|Medium|Low"}}\n'
        "  ],\n"
        '  "recommended_actions": ["Specific action leadership should take"],\n'
        '  "risks_of_this_scenario": ["Downside risk if this scenario is pursued"],\n'
        '  "executive_conclusion": "One sentence board-level recommendation.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)

SENSITIVITY_INSIGHT = PromptTemplate(
    name="sensitivity_insight",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are interpreting sensitivity analysis results for a business team.\n\n"
        "Sensitivity analysis context:\n\n"
        "{context}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Which variables matter most and why — 2 sentences.",\n'
        '  "leverage_points": [\n'
        '    {{\n'
        '      "variable": "column name",\n'
        '      "why_it_matters": "Business explanation of why this is a high-leverage variable.",\n'
        '      "recommended_action": "How management can exploit or protect this lever.",\n'
        '      "confidence": 80\n'
        '    }}\n'
        "  ],\n"
        '  "low_impact_variables": ["Variables the business should deprioritise — with reason"],\n'
        '  "strategic_insight": "One strategic insight from the sensitivity pattern.",\n'
        '  "executive_conclusion": "One sentence closing.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)

SCENARIO_COMPARISON_INSIGHT = PromptTemplate(
    name="scenario_comparison_insight",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are advising a business on which scenario to choose based on what-if analysis.\n\n"
        "Scenario comparison results:\n\n"
        "{context}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Which scenario to choose and why — 2 sentences.",\n'
        '  "recommended_scenario": "Name of the scenario you recommend.",\n'
        '  "rationale": "Why this scenario is preferred over the others — data-grounded.",\n'
        '  "scenario_assessments": [\n'
        '    {{\n'
        '      "name": "scenario name",\n'
        '      "assessment": "Brief assessment: upside, downside, fit.",\n'
        '      "verdict": "Recommended|Viable|Risky|Avoid"\n'
        '    }}\n'
        "  ],\n"
        '  "implementation_risks": ["Risk specific to the recommended scenario"],\n'
        '  "executive_conclusion": "One sentence decision recommendation.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)


# Update registry
TEMPLATES["simulation_insight"] = SIMULATION_INSIGHT
TEMPLATES["sensitivity_insight"] = SENSITIVITY_INSIGHT
TEMPLATES["scenario_comparison_insight"] = SCENARIO_COMPARISON_INSIGHT


# ─────────────────────────────────────────────────────────────
# Module 9: Decision Advisor prompt templates
# ─────────────────────────────────────────────────────────────

DECISION_RECOMMENDATIONS = PromptTemplate(
    name="decision_recommendations",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are a Chief Decision Officer at an elite management consultancy.\n\n"
        "Business analytics context:\n\n"
        "{context}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "2-3 sentences: overall business situation and top priority.",\n'
        '  "recommendations": [\n'
        '    {{\n'
        '      "title": "Specific action title",\n'
        '      "description": "Precise description of what to do and how.",\n'
        '      "category": "financial|sales|marketing|operations|customer|supply_chain|hr|executive",\n'
        '      "priority": "high|medium|low",\n'
        '      "reason": "Why this is recommended — data reference.",\n'
        '      "business_impact": "Revenue, cost, or operational impact.",\n'
        '      "expected_gain": "Quantified or qualified expected benefit.",\n'
        '      "risk": "Main downside risk.",\n'
        '      "implementation_difficulty": "low|medium|high",\n'
        '      "timeline": "immediate|30 days|90 days|6 months|12 months",\n'
        '      "priority_score": 85,\n'
        '      "impact_score": 80,\n'
        '      "confidence_score": 75,\n'
        '      "urgency_score": 90,\n'
        '      "effort_score": 40,\n'
        '      "roi_score": 82,\n'
        '      "overall_score": 78\n'
        '    }}\n'
        '  ],\n'
        '  "executive_conclusion": "One sentence board-level decision.",\n'
        '  "confidence": 85\n'
        "}}"
    ),
)

EXECUTIVE_ADVISOR = PromptTemplate(
    name="executive_advisor",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are a Board-Level Executive Advisor.\n\n"
        "Complete business intelligence context:\n\n"
        "{context}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Board-level situation summary in 2-3 sentences.",\n'
        '  "immediate_actions": [\n'
        '    {{"action": "specific action", "rationale": "why now", "owner": "who"}}\n'
        "  ],\n"
        '  "plan_30_days": [\n'
        '    {{"initiative": "initiative title", "expected_outcome": "measurable result"}}\n'
        "  ],\n"
        '  "plan_90_days": [\n'
        '    {{"initiative": "initiative title", "expected_outcome": "measurable result"}}\n'
        "  ],\n"
        '  "long_term_strategy": [\n'
        '    {{"strategy": "strategic direction", "horizon": "6-24 months", "expected_roi": "qualitative or %"}}\n'
        "  ],\n"
        '  "risks": [\n'
        '    {{"risk": "risk title", "likelihood": "High|Medium|Low", "mitigation": "action"}}\n'
        "  ],\n"
        '  "expected_roi": "Overall expected return if recommendations are implemented.",\n'
        '  "executive_conclusion": "One sentence closing board recommendation.",\n'
        '  "confidence": 85\n'
        "}}"
    ),
)

PRESCRIPTIVE_ANALYTICS = PromptTemplate(
    name="prescriptive_analytics",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are a Prescriptive Analytics Expert.\n\n"
        "Business metrics and root cause context:\n\n"
        "{context}\n\n"
        "Specific metric to address: {query}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "What should be done and why — 2 sentences.",\n'
        '  "root_causes_identified": [\n'
        '    {{"cause": "cause description", "evidence": "data reference", "impact": "business impact"}}\n'
        "  ],\n"
        '  "prescribed_actions": [\n'
        '    {{\n'
        '      "action": "specific action to take",\n'
        '      "addresses_cause": "which root cause this fixes",\n'
        '      "expected_outcome": "measurable result",\n'
        '      "timeline": "when to implement",\n'
        '      "difficulty": "low|medium|high",\n'
        '      "confidence": 80\n'
        '    }}\n'
        "  ],\n"
        '  "kpis_to_monitor": ["KPI names to track progress"],\n'
        '  "success_criteria": "How to know recommendations worked.",\n'
        '  "executive_conclusion": "One sentence closing.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)

DECISION_ROOT_CAUSE = PromptTemplate(
    name="decision_root_cause",
    system_instruction=_SYSTEM_BASE,
    user_prompt=(
        "You are diagnosing why a business metric declined and what to do about it.\n\n"
        "Root cause analysis data:\n\n"
        "{context}\n\n"
        "Problem statement: {query}"
        + _JSON_INSTRUCTION
        + "\n\nReturn exactly this JSON structure:\n"
        '{{\n'
        '  "executive_summary": "Problem diagnosis and top recommendation in 2 sentences.",\n'
        '  "diagnosed_causes": [\n'
        '    {{\n'
        '      "cause": "root cause",\n'
        '      "evidence": "data supporting this",\n'
        '      "contribution_pct": 30,\n'
        '      "recommended_action": "specific countermeasure"\n'
        '    }}\n'
        "  ],\n"
        '  "decision_recommendations": [\n'
        '    {{\n'
        '      "action": "what to do",\n'
        '      "priority": "high|medium|low",\n'
        '      "expected_impact": "quantified outcome",\n'
        '      "timeline": "when"\n'
        '    }}\n'
        "  ],\n"
        '  "prevention_measures": ["How to prevent recurrence"],\n'
        '  "executive_conclusion": "One sentence closing.",\n'
        '  "confidence": 80\n'
        "}}"
    ),
)


# Update registry
TEMPLATES["decision_recommendations"] = DECISION_RECOMMENDATIONS
TEMPLATES["executive_advisor"] = EXECUTIVE_ADVISOR
TEMPLATES["prescriptive_analytics"] = PRESCRIPTIVE_ANALYTICS
TEMPLATES["decision_root_cause"] = DECISION_ROOT_CAUSE
