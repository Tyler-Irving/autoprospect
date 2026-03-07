"""Tier 1 scorer — orchestrates Claude call, validation, and model persistence."""
from __future__ import annotations

import logging
from typing import Any

from apps.businesses.models import Business
from apps.enrichment.models import EnrichmentProfile
from apps.scoring.models import AutomationScore

from .claude_client import ClaudeClient
from .prompts import build_tier1_prompt, build_tier1_system

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {
    "overall_score",
    "confidence",
    "crm_score",
    "scheduling_score",
    "marketing_score",
    "invoicing_score",
    "key_signals",
    "summary",
    "recommended_pitch_angle",
    "estimated_deal_value",
}

VALID_DEAL_VALUES = {"low", "medium", "high", "enterprise"}


class Tier1Scorer:
    """Score a single business with Claude at Tier 1 (quick) depth."""

    def __init__(self) -> None:
        self._client = ClaudeClient()

    def score(self, business: Business, agent_config: Any = None) -> AutomationScore:
        """Run Tier 1 scoring for a business and save the result.

        Args:
            business: Business instance. Must have related enrichment loaded or
                      an EnrichmentProfile will be created with defaults.
            agent_config: Optional AgentConfig instance. When provided, the system
                          prompt is personalised with the workspace's service details.

        Returns:
            Saved AutomationScore instance.
        """
        enrichment = self._get_or_stub_enrichment(business)
        user_prompt = build_tier1_prompt(business, enrichment)

        result = self._client.complete(
            system=build_tier1_system(agent_config),
            user=user_prompt,
            max_tokens=1024,
        )

        self._validate(result)

        score = self._save(business, result)
        logger.info(
            "Tier 1 scored business %d (%s): %d — cost %d¢",
            business.pk,
            business.name,
            score.overall_score,
            score.api_cost_cents,
        )
        return score

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _get_or_stub_enrichment(business: Business) -> EnrichmentProfile:
        """Return enrichment profile, creating a stub if needed."""
        try:
            return business.enrichment
        except EnrichmentProfile.DoesNotExist:
            return EnrichmentProfile(business=business)

    @staticmethod
    def _validate(data: dict[str, Any]) -> None:
        """Raise ValueError if required fields are missing or out of range."""
        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ValueError(f"Claude response missing fields: {missing}")

        for field in ("overall_score", "crm_score", "scheduling_score", "marketing_score", "invoicing_score"):
            val = data[field]
            if not isinstance(val, (int, float)) or not (0 <= int(val) <= 100):
                raise ValueError(f"Field {field}={val!r} out of range 0-100")

        conf = data["confidence"]
        if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
            raise ValueError(f"confidence={conf!r} out of range 0.0-1.0")

        deal = data.get("estimated_deal_value", "")
        if deal not in VALID_DEAL_VALUES:
            # Coerce to low rather than failing the whole task
            data["estimated_deal_value"] = "low"

    @staticmethod
    def _save(business: Business, data: dict[str, Any]) -> AutomationScore:
        """Persist or update the Tier 1 AutomationScore."""
        score, _ = AutomationScore.objects.update_or_create(
            business=business,
            tier=AutomationScore.Tier.TIER1,
            defaults={
                "overall_score": int(data["overall_score"]),
                "confidence": float(data["confidence"]),
                "crm_score": int(data["crm_score"]),
                "scheduling_score": int(data["scheduling_score"]),
                "marketing_score": int(data["marketing_score"]),
                "invoicing_score": int(data["invoicing_score"]),
                "key_signals": data.get("key_signals", []),
                "summary": data.get("summary", ""),
                "recommended_pitch_angle": data.get("recommended_pitch_angle", ""),
                "estimated_deal_value": data.get("estimated_deal_value", "low"),
                "model_used": data["model_used"],
                "prompt_tokens": data["prompt_tokens"],
                "completion_tokens": data["completion_tokens"],
                "api_cost_cents": data["api_cost_cents"],
            },
        )
        return score
