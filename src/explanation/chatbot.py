from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from src.explanation.llm_explainer import _OPENROUTER_URL

logger = logging.getLogger(__name__)

DEFAULT_CHAT_MODEL = "openrouter/free"
CURATED_FREE_CHAT_MODELS = [
    DEFAULT_CHAT_MODEL,
    "google/gemma-4-31b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
]

CHATBOT_SYSTEM_PROMPT = """\
You are SmartPick AI, an in-app smartphone chatbot.

Rules you MUST follow:
1. You do not have live web access.
2. Do not claim current prices, current release dates, market availability, or recent news unless that information appears in the provided app context.
3. Use ranking context exactly as provided. Never change or contradict saved ranking results.
4. You may use general, non-time-sensitive smartphone knowledge, but app data takes priority when specific specs or ranking outputs are provided.
5. If the user asks for something you cannot know from the app context or stable background knowledge, say so clearly.
6. Keep answers practical, concise, and comparison-friendly.
"""


def _build_catalog_context(phone_specs: List[Dict[str, Any]]) -> str:
    lines = ["## Smartphone Catalog"]
    for phone in phone_specs:
        lines.append(f"### {phone.get('model_name', '')}".strip())
        specs = phone.get("specs", phone)
        for key, value in specs.items():
            if key not in {"id", "model_name", "brand", "image_url", "supported_by_cv"}:
                lines.append(f"- {key}: {value}")
        lines.append("")
    return "\n".join(lines)


def _build_ranking_context(ranking_data: Optional[Dict[str, Any]]) -> str:
    if not ranking_data:
        return "## Ranking Context\nNo saved ranking context was provided."

    lines = ["## Ranking Context"]
    top_match = ranking_data.get("top_match", {})
    if top_match:
        lines.append(
            f"Top match: {top_match.get('model_name', 'Unknown')} "
            f"(score={top_match.get('score', 0)}, "
            f"closeness={top_match.get('closeness_coefficient', 0)})"
        )

    lines.append("### Rankings")
    for item in ranking_data.get("rankings", []):
        lines.append(
            f"- Rank {item['rank']}: {item['model_name']} "
            f"(score={item['score']}, closeness={item['closeness_coefficient']})"
        )

    lines.append("### Weights")
    for criterion, weight in ranking_data.get("weights_used", {}).items():
        lines.append(f"- {criterion}: {weight}")

    return "\n".join(lines)


async def answer_chat(
    question: str,
    phone_specs: List[Dict[str, Any]],
    ranking_data: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    model_id: str = DEFAULT_CHAT_MODEL,
) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    catalog_context = _build_catalog_context(phone_specs)
    ranking_context = _build_ranking_context(ranking_data)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": CHATBOT_SYSTEM_PROMPT},
        {"role": "system", "content": f"{catalog_context}\n\n{ranking_context}"},
    ]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": question})

    if model_id not in CURATED_FREE_CHAT_MODELS:
        raise RuntimeError(f"Unsupported chat model: {model_id}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5173",
                    "X-Title": "SmartPick AI Chatbot",
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
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Chatbot model %s failed: %s", model_id, exc)
        raise RuntimeError(f"Chat model failed: {exc}") from exc


def fallback_chat_answer(question: str, ranking_data: Optional[Dict[str, Any]] = None) -> str:
    if ranking_data and ranking_data.get("top_match"):
        top = ranking_data["top_match"]
        return (
            f"I can still help based on your saved analysis. "
            f"Your top-ranked phone is {top.get('model_name', 'Unknown')} "
            f"with a score of {top.get('score', 0):.2f}. "
            f"Please try your question again once the chat model is available."
        )

    return (
        "I can help with smartphone guidance using the app's catalog and ranking data, "
        "but the chat model is unavailable right now. Please try again in a moment."
    )
