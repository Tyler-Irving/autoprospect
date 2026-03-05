"""Tests for Tier1Scorer service — mocks ClaudeClient."""
import pytest
from unittest.mock import MagicMock, patch

from apps.scoring.services.tier1_scorer import Tier1Scorer, VALID_DEAL_VALUES

VALID_RESPONSE = {
    "overall_score": 80,
    "confidence": 0.85,
    "crm_score": 90,
    "scheduling_score": 75,
    "marketing_score": 70,
    "invoicing_score": 85,
    "key_signals": ["no CRM detected", "manual scheduling", "high review volume"],
    "summary": "Strong candidate for automation. No digital tools detected.",
    "recommended_pitch_angle": "Lead with scheduling automation ROI.",
    "estimated_deal_value": "high",
    "model_used": "claude-sonnet-4-5-20250929",
    "prompt_tokens": 500,
    "completion_tokens": 200,
    "api_cost_cents": 5,
}


class TestTier1ScorerValidation:
    def test_valid_response_passes(self):
        Tier1Scorer._validate(dict(VALID_RESPONSE))

    def test_missing_field_raises(self):
        data = dict(VALID_RESPONSE)
        del data["overall_score"]
        with pytest.raises(ValueError, match="missing fields"):
            Tier1Scorer._validate(data)

    def test_score_out_of_range_raises(self):
        data = dict(VALID_RESPONSE)
        data["overall_score"] = 150
        with pytest.raises(ValueError, match="out of range"):
            Tier1Scorer._validate(data)

    def test_confidence_out_of_range_raises(self):
        data = dict(VALID_RESPONSE)
        data["confidence"] = 1.5
        with pytest.raises(ValueError, match="out of range"):
            Tier1Scorer._validate(data)

    def test_invalid_deal_value_coerced_to_low(self):
        data = dict(VALID_RESPONSE)
        data["estimated_deal_value"] = "gigantic"
        Tier1Scorer._validate(data)
        assert data["estimated_deal_value"] == "low"


@pytest.mark.django_db
class TestTier1ScorerScore:
    def _make_business(self):
        from apps.scans.models import Scan
        from apps.businesses.models import Business
        scan = Scan.objects.create(
            center_lat="34.8",
            center_lng="-90.0",
            radius_meters=5000,
        )
        return Business.objects.create(
            google_place_id="GPT1",
            name="Test Plumbing",
            latitude="34.8",
            longitude="-90.0",
            scan=scan,
        )

    def test_score_creates_automation_score(self):
        business = self._make_business()
        with patch("apps.scoring.services.tier1_scorer.ClaudeClient") as MockClient:
            MockClient.return_value.complete.return_value = dict(VALID_RESPONSE)
            scorer = Tier1Scorer()
            score = scorer.score(business)

        from apps.scoring.models import AutomationScore
        assert AutomationScore.objects.filter(business=business, tier="tier1").exists()
        assert score.overall_score == 80
        assert score.estimated_deal_value == "high"
        assert score.api_cost_cents == 5

    def test_score_upserts_existing(self):
        business = self._make_business()
        with patch("apps.scoring.services.tier1_scorer.ClaudeClient") as MockClient:
            MockClient.return_value.complete.return_value = dict(VALID_RESPONSE)
            scorer = Tier1Scorer()
            scorer.score(business)

            updated = dict(VALID_RESPONSE)
            updated["overall_score"] = 55
            MockClient.return_value.complete.return_value = updated
            score2 = scorer.score(business)

        from apps.scoring.models import AutomationScore
        assert AutomationScore.objects.filter(business=business, tier="tier1").count() == 1
        assert score2.overall_score == 55
