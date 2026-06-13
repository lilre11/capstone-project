"""LLM-based explanation module using OpenRouter free models.

The explainer receives structured TOPSIS ranking data and AHP weights,
then generates natural-language explanations.  It strictly follows the
rules in PRD Section 16:

  * Only mentions AHP + TOPSIS (never Fuzzy AHP, Entropy, VIKOR, PROMETHEE).
  * Never invents phone specifications.
  * Never changes the ranking.
  * Explains results in simple, user-friendly language.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# OpenRouter's free router automatically selects a currently available free model.
_FREE_MODELS = [
    "openrouter/free",
]
SUPPORTED_EXPLAIN_MODELS = tuple(_FREE_MODELS)
DEFAULT_EXPLAIN_MODEL = _FREE_MODELS[0]

SYSTEM_PROMPT = """\
You are an AI smartphone recommendation assistant integrated into a \
decision-support system.  The system uses **AHP (Analytic Hierarchy Process)** \
to determine criterion weights and **TOPSIS (Technique for Order of Preference \
by Similarity to Ideal Solution)** to rank smartphone alternatives.

Rules you MUST follow:
1. You must ONLY reference the AHP + TOPSIS methodology.  NEVER mention \
   Fuzzy AHP, Entropy weighting, VIKOR, or PROMETHEE.
2. You must NOT invent or fabricate phone specifications.  Use only the data \
   provided in the context below.
3. You must NOT change or contradict the ranking.  The ranking is final.
4. Explain results in simple, clear language that a non-technical user can \
   understand.
5. When explaining why a phone ranked higher, reference its closeness \
   coefficient (C⁺), how close it is to the ideal solution, and which \
   criteria contributed most.
6. Use the criterion weights to explain what the user prioritised.
7. Keep answers concise but informative.  Use bullet points when helpful.

Key terminology:
- C⁺ (closeness coefficient): ranges 0–1; higher means the phone is closer \
  to the ideal solution.  Score = C⁺ × 100.
- S⁺: distance from ideal best (lower is better).
- S⁻: distance from ideal worst (higher is better).
- Ideal Best (A⁺): the best value for each criterion across all phones.
- Ideal Worst (A⁻): the worst value for each criterion across all phones.
"""


def _build_context(ranking_data: Dict[str, Any]) -> str:
    """Format the TOPSIS result data as structured context for the LLM."""
    lines = ["## Ranking Context\n"]

    # Weights
    weights = ranking_data.get("weights_used", {})
    if weights:
        lines.append("### AHP Criterion Weights")
        for crit, w in weights.items():
            lines.append(f"- {crit}: {w:.4f}")
        lines.append("")

    # Rankings
    rankings = ranking_data.get("rankings", [])
    if rankings:
        lines.append("### TOPSIS Rankings")
        for r in rankings:
            lines.append(
                f"- Rank {r['rank']}: {r['model_name']} "
                f"(C⁺={r['closeness_coefficient']:.4f}, "
                f"Score={r['score']:.2f}, "
                f"S⁺={r.get('s_plus', 'N/A')}, "
                f"S⁻={r.get('s_minus', 'N/A')})"
            )
        lines.append("")

    # Ideal solutions
    ideal_best = ranking_data.get("ideal_best", {})
    ideal_worst = ranking_data.get("ideal_worst", {})
    if ideal_best:
        lines.append("### Ideal Solutions")
        lines.append("| Criterion | A⁺ (Ideal Best) | A⁻ (Ideal Worst) |")
        lines.append("|---|---|---|")
        for crit in ideal_best:
            lines.append(
                f"| {crit} | {ideal_best[crit]:.5f} | {ideal_worst.get(crit, 'N/A')} |"
            )
        lines.append("")

    # Directions
    directions = ranking_data.get("criteria_directions", {})
    if directions:
        lines.append("### Criteria Directions")
        for crit, d in directions.items():
            label = "higher is better" if d == "max" else "lower is better"
            lines.append(f"- {crit}: {d} ({label})")

    return "\n".join(lines)


def _build_phone_specs_context(phone_specs: Optional[List[Dict]] = None) -> str:
    """Format raw phone specifications if available."""
    if not phone_specs:
        return ""
    lines = ["\n## Phone Specifications\n"]
    for phone in phone_specs:
        lines.append(f"### {phone.get('model_name', 'Unknown')}")
        specs = phone.get("specs", phone)
        for key, val in specs.items():
            if key not in ("id", "model_name", "brand", "image_url", "supported_by_cv"):
                lines.append(f"- {key}: {val}")
        lines.append("")
    return "\n".join(lines)


async def explain(
    question: str,
    ranking_data: Dict[str, Any],
    phone_specs: Optional[List[Dict]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    model_id: str = DEFAULT_EXPLAIN_MODEL,
) -> str:
    """Generate an LLM explanation for the ranking result.

    Parameters
    ----------
    question:
        The user's question (e.g. "Why was OnePlus 13 recommended?").
    ranking_data:
        The full TOPSIS result dict from ``rank_smartphones()``.
    phone_specs:
        Optional list of phone spec dicts for raw data context.
    conversation_history:
        Optional prior messages for multi-turn conversation.

    Returns
    -------
    str
        The LLM's explanation text.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set, using fallback explanation.")
        return explain_fallback(question, ranking_data)

    context = _build_context(ranking_data)
    specs_context = _build_phone_specs_context(phone_specs)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"{context}\n{specs_context}"},
    ]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": question})

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5173",
                    "X-Title": "Smartphone Decision Support System",
                },
                json={
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip()
    except Exception as e:
        logger.warning("OpenRouter model %s failed: %s", model_id, e)
        return explain_fallback(question, ranking_data)


def explain_fallback(
    question: str,
    ranking_data: Dict[str, Any],
) -> str:
    """Template-based fallback explanation when the LLM is unavailable.

    This ensures the user always gets an answer even if the API is down.
    """
    top = ranking_data.get("top_match", {})
    rankings = ranking_data.get("rankings", [])
    weights = ranking_data.get("weights_used", {})

    if not top:
        return "No ranking data available to explain."

    name = top.get("model_name", "Unknown")
    score = top.get("score", 0)
    cc = top.get("closeness_coefficient", 0)
    s_plus = top.get("s_plus", 0)
    s_minus = top.get("s_minus", 0)

    # Find the most important criterion
    top_criterion = max(weights, key=weights.get) if weights else "overall performance"
    top_weight = weights.get(top_criterion, 0)

    explanation = (
        f"**{name}** was recommended as your top match because it achieved the "
        f"highest TOPSIS closeness coefficient (C⁺ = {cc:.4f}), resulting in a "
        f"score of {score:.2f} out of 100.\n\n"
        f"In this system, **AHP (Analytic Hierarchy Process)** first determines "
        f"how important each criterion is based on your preferences. Your most "
        f"prioritised criterion was **{top_criterion}** (weight: {top_weight:.2%}).\n\n"
        f"Then, **TOPSIS** compares each phone against the ideal best and ideal "
        f"worst alternatives across all criteria. {name} had:\n"
        f"- Distance from ideal best (S⁺): {s_plus:.5f} (lower is better)\n"
        f"- Distance from ideal worst (S⁻): {s_minus:.5f} (higher is better)\n\n"
        f"Since {name} was closest to the ideal solution and farthest from the "
        f"worst solution overall, it ranked **#1**."
    )

    if len(rankings) >= 2:
        runner_up = rankings[1]
        explanation += (
            f"\n\nThe runner-up was **{runner_up['model_name']}** with a score of "
            f"{runner_up['score']:.2f}."
        )

    return explanation


__all__ = ["explain", "explain_fallback", "SYSTEM_PROMPT"]
