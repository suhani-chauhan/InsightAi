"""LLM narrative + "Ask InsightMind" layer (master spec §20 / §21 / §43).

The LLM only ever *explains* numbers this package already computed. Every call
is wrapped so the feature degrades to a deterministic fallback if the model or
a credential is unavailable — the workspace never hard-depends on it.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.db.models.llm import LlmExecutionContext
from app.integrations.llm_client import invoke_chat_llm

logger = logging.getLogger("insightmind.data_science.llm")

_GROUNDING_RULE = (
    "You are InsightMind AI's analytical assistant. You are given a JSON payload of "
    "statistics, data-quality findings, and model metrics that were computed deterministically "
    "in Python. Rules: (1) Use ONLY numbers present in the payload — never invent or recompute "
    "figures. (2) Say 'associated with', not 'causes', unless the payload states a causal test. "
    "(3) Be concise and specific. (4) If the payload lacks what's needed to answer, say so."
)


def _ask(context: LlmExecutionContext, system: str, user: str, *, max_tokens: int = 500) -> str | None:
    try:
        return invoke_chat_llm(
            context,
            [SystemMessage(content=system), HumanMessage(content=user)],
            temperature=0.2,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001 - narrative is always optional
        logger.info("[data-science-llm] narrative unavailable: %s", exc)
        return None


def narrate_quality(context: LlmExecutionContext, quality: dict[str, Any]) -> str | None:
    payload = {
        "score": quality.get("score"),
        "issues": [
            {k: i[k] for k in ("title", "severity", "dimension", "recommendation", "evidence")}
            for i in quality.get("issues", [])[:15]
        ],
    }
    return _ask(
        context,
        _GROUNDING_RULE,
        "Summarise the most important data-quality problems and what to fix first, in 3-5 sentences.\n\n"
        + json.dumps(payload, default=str),
    )


def narrate_cleaning_change(context: LlmExecutionContext, before: dict, after: dict, steps: list[dict]) -> str | None:
    payload = {"quality_before": before, "quality_after": after, "operations": steps}
    return _ask(
        context,
        _GROUNDING_RULE,
        "In 1-2 sentences, explain how data quality changed and why, referencing the operations applied.\n\n"
        + json.dumps(payload, default=str),
    )


def narrate_eda(context: LlmExecutionContext, eda: dict[str, Any]) -> str | None:
    payload = {
        "insights": eda.get("insights", []),
        "top_correlations": (eda.get("correlations") or {}).get("top_pairs", [])[:5],
        "numeric_summary": eda.get("numeric_summary", [])[:8],
    }
    return _ask(
        context,
        _GROUNDING_RULE,
        "Write a short narrative (4-6 sentences) of the key exploratory findings for a business reader.\n\n"
        + json.dumps(payload, default=str),
    )


def narrate_model_results(context: LlmExecutionContext, ml: dict[str, Any]) -> str | None:
    payload = {
        "task": ml.get("task"),
        "target": ml.get("target"),
        "primary_metric": ml.get("primary_metric"),
        "best_model": ml.get("best_model_name"),
        "comparison": ml.get("comparison", []),
        "feature_importance": ml.get("feature_importance", [])[:8],
    }
    return _ask(
        context,
        _GROUNDING_RULE,
        "Explain which model won and why, what the headline metric means in plain terms, and which "
        "features drove predictions. 4-6 sentences.\n\n" + json.dumps(payload, default=str),
    )


def answer_question(context: LlmExecutionContext, question: str, artifacts: dict[str, Any]) -> dict[str, Any]:
    """Free-form 'Ask InsightMind' over whatever artifacts the session has."""
    text = _ask(
        context,
        _GROUNDING_RULE
        + " The payload may contain: dataset overview, data-quality report, cleaning history, EDA "
        "statistics, and model results. Answer the user's question grounded strictly in it.",
        f"Question: {question}\n\nAvailable analysis:\n" + json.dumps(artifacts, default=str)[:24000],
        max_tokens=700,
    )
    if text is None:
        return {
            "answer": "The AI narrative layer is unavailable right now, but the computed analysis on this "
            "page (profiling, quality score, EDA statistics, model metrics) is still accurate.",
            "grounded": True,
            "llm_available": False,
        }
    return {"answer": text, "grounded": True, "llm_available": True}


__all__ = [
    "narrate_quality",
    "narrate_cleaning_change",
    "narrate_eda",
    "narrate_model_results",
    "answer_question",
]
