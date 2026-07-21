# Phase 6 — AI Integration

A backend-only service layer this time — no new routes, models, or migrations.
`AIService` is the OpenRouter client every later phase (Sentiment, Weekly Summary,
AI Insights) calls into; Phase 6 just gets it built, tested, and hardened first.

## What shipped
- `app/services/ai_service.py` — a plain `httpx.Client` wrapper around OpenRouter's
  `/chat/completions` endpoint, with:
  - **Retry**: transient failures (timeouts, connection errors, and `408/409/425/
    429/500/502/503/504` responses) retry on the primary model up to
    `openrouter_max_retries` times with capped exponential backoff.
  - **Timeout**: every request uses `openrouter_timeout` (seconds).
  - **Fallback model**: if the primary model (`openrouter_model`) ultimately
    fails for any reason, one attempt is made against `openrouter_fallback_model`
    before the call is given up on.
  - **Safe JSON parsing**: LLM output is untrusted text — `_extract_json_object` /
    `_extract_json_array` strip Markdown code fences, locate the first `{...}` or
    `[...]` block, and parse it. Any malformed, missing, or out-of-range field
    raises `AIServiceError` (502) instead of an unhandled exception.
- Three public functions used by later phases:
  - `analyze_sentiment(text: str) -> dict` — `{"sentiment", "mood", "emotion",
    "confidence", "raw_response"}` (feeds the Phase 7 `Sentiment` model directly).
  - `extract_emotions(text: str, *, max_emotions=5) -> list[str]` — lowercase
    emotion labels, strongest first.
  - `generate_summary(entries: str | list[str]) -> str` — a short prose summary
    of one or more journal entries (feeds Phase 8 Weekly Summary).

## Design notes
- All three prompts instruct the model to respond with *only* JSON (or, for
  summaries, *only* prose) — but free OpenRouter models don't always comply
  (they sometimes wrap JSON in ` ```json ` fences or add a sentence of
  preamble). The parser strips fences and regex-extracts the JSON block rather
  than assuming `response.json()` will succeed on the raw string.
- `analyze_sentiment` validates `sentiment` is one of `positive|neutral|negative`,
  `mood`/`emotion` are non-empty, and clamps `confidence` to `[0, 1]` — a model
  that ignores instructions raises `AIServiceError` rather than poisoning the
  database with garbage.
- No API keys or raw model output are logged; only a one-line warning when the
  primary model fails and the fallback is attempted.
- Nothing here is reachable over HTTP yet — there's no `AIServiceError` route
  to hit directly. Phase 7 (`POST /journals/{id}/analyze`) is what actually
  wires a request into `analyze_sentiment`.

## Verify (no HTTP surface — call it directly)
```bash
# requires OPENROUTER_API_KEY set in .env
python -c "
from app.services import ai_service
text = 'Today was stressful but I finished a big project and my manager praised me.'
print(ai_service.analyze_sentiment(text))
print(ai_service.extract_emotions(text))
print(ai_service.generate_summary(text))
"
```
Tested against the configured free models end-to-end, including: a normal
successful call, an invalid primary model id correctly falling back to the
configured fallback model, both models invalid raising a single clean
`AIServiceError`, and malformed/out-of-range LLM output being rejected instead
of silently accepted.
