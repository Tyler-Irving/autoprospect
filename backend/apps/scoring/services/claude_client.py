"""Claude API client with cost tracking."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5-20250929"
# Pricing per million tokens (USD → cents conversion)
INPUT_COST_PER_M = 300   # $3.00/M → 300 cents/M
OUTPUT_COST_PER_M = 1500  # $15.00/M → 1500 cents/M


class ClaudeClient:
    """Thin wrapper around the Anthropic SDK with JSON extraction and cost tracking."""

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> dict[str, Any]:
        """Send a completion request and return parsed JSON with cost metadata.

        Args:
            system: System prompt.
            user: User message.
            max_tokens: Maximum response tokens.

        Returns:
            Parsed JSON dict with extra keys: model_used, prompt_tokens,
            completion_tokens, api_cost_cents.

        Raises:
            ValueError: If the response cannot be parsed as JSON.
        """
        message = self._client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[
                {"role": "user", "content": user},
                # Prefill the assistant turn with "{" so Claude is forced to
                # complete a JSON object rather than risk adding preamble or
                # producing unescaped quotes inside string values.
                {"role": "assistant", "content": "{"},
            ],
        )

        # Prepend the "{" we sent as the prefill — the completion is the rest.
        raw = "{" + message.content[0].text
        prompt_tokens = message.usage.input_tokens
        completion_tokens = message.usage.output_tokens
        cost_cents = self._calc_cost(prompt_tokens, completion_tokens)

        parsed = self._extract_json(raw)
        parsed["model_used"] = MODEL
        parsed["prompt_tokens"] = prompt_tokens
        parsed["completion_tokens"] = completion_tokens
        parsed["api_cost_cents"] = cost_cents
        return parsed

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _calc_cost(prompt_tokens: int, completion_tokens: int) -> int:
        """Return total cost in cents (rounded up to nearest cent)."""
        cost = (prompt_tokens * INPUT_COST_PER_M + completion_tokens * OUTPUT_COST_PER_M) / 1_000_000
        return max(1, round(cost))

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """Strip markdown fences and parse JSON from Claude's response."""
        # Remove ```json ... ``` or ``` ... ``` fences
        text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Claude JSON response: %s\nRaw: %s", exc, text[:500])
            raise ValueError(f"Claude response was not valid JSON: {exc}") from exc
