"""AIService: OpenRouter-backed sentiment analysis, emotion extraction, and summarization.

Every public function sends one chat-completion request via `_chat_completion`,
which retries transient failures on the primary model (`openrouter_model`) and
falls back to `openrouter_fallback_model` once before giving up. LLM output is
untrusted free text, so every public function parses it defensively and raises
`AIServiceError` (502) instead of letting a malformed response bubble up as an
unhandled exception.
"""

from __future__ import annotations

import json
import re
import time

import httpx

from app.core.config import settings
from app.core.exceptions import AIServiceError, BadRequestError
from app.core.logging import get_logger

logger = get_logger(__name__)

_RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
_SENTIMENT_VALUES = {"positive", "neutral", "negative"}

_SENTIMENT_SYSTEM_PROMPT = (
    "You are a sentiment-analysis engine for a personal journaling app. Given a "
    "journal entry, respond with ONLY a single JSON object (no markdown, no "
    "commentary) of the exact shape: "
    '{"sentiment": "positive"|"neutral"|"negative", '
    '"mood": "<one or two word mood descriptor>", '
    '"emotion": "<single primary emotion, one word>", '
    '"confidence": <number between 0 and 1>}.'
)

_EMOTIONS_SYSTEM_PROMPT = (
    "You are an emotion-extraction engine for a personal journaling app. Given a "
    "journal entry, respond with ONLY a JSON array (no markdown, no commentary) of "
    "up to 5 short, lowercase emotion labels present in the text, ordered from "
    'strongest to weakest, e.g. ["gratitude", "relief"].'
)

_SUMMARY_SYSTEM_PROMPT = (
    "You are a reflective writing assistant for a personal journaling app. "
    "Summarize the journal entry/entries below in 2-4 concise sentences, "
    "capturing the overall mood and key events. Respond with plain prose only "
    "— no JSON, no headers, no bullet points."
)

_INSIGHTS_SYSTEM_PROMPT = (
    "You are an insightful journaling analyst. Given a summary of a user's journaling "
    "history and mood statistics, respond with ONLY a JSON array (no markdown, no "
    "commentary) of 3-5 short, specific, natural-language insights about the user's "
    "emotional patterns, habits, and trends. Each item is one sentence, addressed to "
    'the user, e.g. ["You tend to feel more positive on weekends.", "Your journaling '
    'has been highly consistent this month."].'
)

_WEEKLY_SUMMARY_SYSTEM_PROMPT = (
    "You are a supportive journaling coach. Given a user's journal entries from a "
    "single week, respond with ONLY a single JSON object (no markdown, no "
    "commentary) of the exact shape: "
    '{"summary": "<2-4 sentence reflective summary of the week\'s overall mood, '
    'themes, and key events>", '
    '"suggestions": ["<short, actionable, encouraging suggestion>", ...]}. '
    "Provide between 2 and 4 suggestions."
)


# --- HTTP plumbing: retries + timeout + fallback model -----------------------

def _client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.openrouter_base_url,
        timeout=settings.openrouter_timeout,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        },
    )


def _request_completion(
    client: httpx.Client, model: str, messages: list[dict], *, max_attempts: int
) -> str:
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            response = client.post(
                "/chat/completions",
                json={"model": model, "messages": messages, "temperature": 0.2},
            )
        except httpx.TimeoutException as exc:
            last_error = exc
        except httpx.TransportError as exc:
            last_error = exc
        else:
            if response.status_code == 200:
                data = response.json()
                try:
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise AIServiceError("AI service returned an unexpected response shape") from exc
            if response.status_code not in _RETRYABLE_STATUS_CODES:
                raise AIServiceError(f"AI service request failed ({response.status_code})")
            last_error = RuntimeError(f"AI service returned {response.status_code}")

        if attempt < max_attempts - 1:
            time.sleep(min(2**attempt * 0.5, 4.0))

    raise last_error or AIServiceError("AI service request failed")


def _chat_completion(messages: list[dict]) -> str:
    with _client() as client:
        try:
            return _request_completion(
                client,
                settings.openrouter_model,
                messages,
                max_attempts=settings.openrouter_max_retries,
            )
        except Exception as primary_exc:
            logger.warning(
                "Primary model %s failed (%s), falling back to %s",
                settings.openrouter_model,
                primary_exc,
                settings.openrouter_fallback_model,
            )
            try:
                return _request_completion(
                    client, settings.openrouter_fallback_model, messages, max_attempts=1
                )
            except Exception as fallback_exc:
                raise AIServiceError("AI service is currently unavailable") from fallback_exc


# --- Safe JSON parsing of LLM output -----------------------------------------

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
        text = text.removesuffix("```")
    return text.strip()


def _extract_json_object(raw: str) -> dict:
    text = _strip_code_fence(raw)
    match = _JSON_OBJECT_RE.search(text)
    candidate = match.group(0) if match else text
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AIServiceError("AI returned a malformed response") from exc
    if not isinstance(parsed, dict):
        raise AIServiceError("AI returned an unexpected response shape")
    return parsed


def _extract_json_array(raw: str) -> list:
    text = _strip_code_fence(raw)
    match = _JSON_ARRAY_RE.search(text)
    candidate = match.group(0) if match else text
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AIServiceError("AI returned a malformed response") from exc
    if not isinstance(parsed, list):
        raise AIServiceError("AI returned an unexpected response shape")
    return parsed


# --- Public API ---------------------------------------------------------------

def analyze_sentiment(text: str) -> dict:
    """Return {"sentiment", "mood", "emotion", "confidence", "raw_response"}."""
    raw = _chat_completion(
        [
            {"role": "system", "content": _SENTIMENT_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
    )
    data = _extract_json_object(raw)

    sentiment = str(data.get("sentiment", "")).strip().lower()
    if sentiment not in _SENTIMENT_VALUES:
        raise AIServiceError("AI returned an unrecognized sentiment value")

    mood = str(data.get("mood", "")).strip()
    emotion = str(data.get("emotion", "")).strip()
    if not mood or not emotion:
        raise AIServiceError("AI response is missing required fields")

    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        raise AIServiceError("AI returned a non-numeric confidence value")
    confidence = max(0.0, min(1.0, confidence))

    return {
        "sentiment": sentiment,
        "mood": mood,
        "emotion": emotion,
        "confidence": confidence,
        "raw_response": raw,
    }


def extract_emotions(text: str, *, max_emotions: int = 5) -> list[str]:
    """Return up to `max_emotions` lowercase emotion labels, strongest first."""
    raw = _chat_completion(
        [
            {"role": "system", "content": _EMOTIONS_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
    )
    data = _extract_json_array(raw)
    emotions = [str(item).strip().lower() for item in data if str(item).strip()]
    if not emotions:
        raise AIServiceError("AI returned no emotions")
    return emotions[:max_emotions]


def generate_summary(entries: list[str] | str) -> str:
    """Summarize one journal entry or a list of entries into a short paragraph."""
    texts = [entries] if isinstance(entries, str) else list(entries)
    if not texts:
        raise BadRequestError("At least one journal entry is required to summarize")

    joined = "\n\n---\n\n".join(texts)
    raw = _chat_completion(
        [
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": joined},
        ]
    )
    summary = raw.strip()
    if not summary:
        raise AIServiceError("AI returned an empty summary")
    return summary


def generate_weekly_summary(entries: list[str] | str) -> dict:
    """Return {"summary": str, "suggestions": list[str]} for a week of entries."""
    texts = [entries] if isinstance(entries, str) else list(entries)
    if not texts:
        raise BadRequestError("At least one journal entry is required to summarize")

    joined = "\n\n---\n\n".join(texts)
    raw = _chat_completion(
        [
            {"role": "system", "content": _WEEKLY_SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": joined},
        ]
    )
    data = _extract_json_object(raw)

    summary = str(data.get("summary", "")).strip()
    if not summary:
        raise AIServiceError("AI returned an empty weekly summary")

    raw_suggestions = data.get("suggestions", [])
    if isinstance(raw_suggestions, str):
        raw_suggestions = [raw_suggestions]
    if not isinstance(raw_suggestions, list):
        raw_suggestions = []
    suggestions = [str(item).strip() for item in raw_suggestions if str(item).strip()]

    return {"summary": summary, "suggestions": suggestions[:4]}


def generate_insights(context: str) -> list[str]:
    """Return up to 5 natural-language insight sentences from a history/stats summary."""
    raw = _chat_completion(
        [
            {"role": "system", "content": _INSIGHTS_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]
    )
    data = _extract_json_array(raw)
    insights = [str(item).strip() for item in data if str(item).strip()]
    if not insights:
        raise AIServiceError("AI returned no insights")
    return insights[:5]
