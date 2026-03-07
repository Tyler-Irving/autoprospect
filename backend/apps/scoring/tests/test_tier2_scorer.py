"""Tests for Tier2Scorer service — mocks ClaudeClient."""
import pytest
from unittest.mock import patch

from apps.scoring.services.tier2_scorer import Tier2Scorer


VALID_RESPONSE = {
    "overall_score": 78,
    "confidence": 0.82,
    "crm_score": 80,
    "scheduling_score": 72,
    "marketing_score": 75,
    "invoicing_score": 84,
    "key_signals": ["manual follow-ups", "no booking flow"],
    "summary": "Strong candidate for deeper automation support.",
    "recommended_pitch_angle": "Lead with missed-call capture and booking.",
    "estimated_deal_value": "high",
    "full_dossier": "Detailed analysis body.",
    "competitor_analysis": "Peers in the area are more automated.",
    "model_used": "claude-sonnet-4-5-20250929",
    "prompt_tokens": 1200,
    "completion_tokens": 2000,
    "api_cost_cents": 42,
}


@pytest.mark.django_db
class TestTier2Scorer:
    def _make_business(self):
        from apps.scans.models import Scan
        from apps.businesses.models import Business

        scan = Scan.objects.create(center_lat="34.8", center_lng="-90.0", radius_meters=5000)
        return Business.objects.create(
            google_place_id="GPT2",
            name="Tier2 Test Plumbing",
            latitude="34.8",
            longitude="-90.0",
            scan=scan,
        )

    def _make_tier1(self, business):
        from apps.scoring.models import AutomationScore

        return AutomationScore.objects.create(
            business=business,
            tier="tier1",
            overall_score=65,
            confidence="0.70",
            crm_score=60,
            scheduling_score=70,
            marketing_score=65,
            invoicing_score=66,
            key_signals=["test"],
            summary="tier1",
            recommended_pitch_angle="angle",
            estimated_deal_value="medium",
            model_used="test-model",
            prompt_tokens=1,
            completion_tokens=1,
            api_cost_cents=1,
        )

    def test_score_creates_tier2_score(self):
        business = self._make_business()
        self._make_tier1(business)

        with patch("apps.scoring.services.tier2_scorer.ClaudeClient") as MockClient:
            MockClient.return_value.complete.return_value = dict(VALID_RESPONSE)
            score = Tier2Scorer().score(business)

        assert score.tier == "tier2"
        assert score.overall_score == 78
        assert score.full_dossier == "Detailed analysis body."

    def test_invalid_deal_value_coerced(self):
        business = self._make_business()
        self._make_tier1(business)

        bad = dict(VALID_RESPONSE)
        bad["estimated_deal_value"] = "unknown"

        with patch("apps.scoring.services.tier2_scorer.ClaudeClient") as MockClient:
            MockClient.return_value.complete.return_value = bad
            score = Tier2Scorer().score(business)

        assert score.estimated_deal_value == "low"

    def test_missing_required_field_raises(self):
        data = dict(VALID_RESPONSE)
        del data["full_dossier"]
        with pytest.raises(ValueError, match="missing fields"):
            Tier2Scorer._validate(data)
