"""Tests for scoring Celery task: score_business_tier1."""
import pytest
from unittest.mock import MagicMock, patch

from apps.scoring.tasks import score_business_tier1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_business(suffix="T"):
    from apps.scans.models import Scan
    from apps.businesses.models import Business

    scan = Scan.objects.create(
        center_lat="34.0522",
        center_lng="-118.2437",
        radius_meters=8000,
    )
    return Business.objects.create(
        google_place_id=f"place_score_{suffix}",
        name="Score Test Biz",
        latitude="34.05",
        longitude="-118.24",
        scan=scan,
    )


def _mock_score(overall_score=75, api_cost_cents=5):
    """Return a mock AutomationScore-like object."""
    score = MagicMock()
    score.overall_score = overall_score
    score.api_cost_cents = api_cost_cents
    return score


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestScoreBusinessTier1:
    def test_nonexistent_business_returns_error(self):
        result = score_business_tier1(99999)
        assert result == {"error": "Business not found"}

    def test_returns_score_result(self):
        biz = _make_business("R1")
        with patch("apps.scoring.tasks.Tier1Scorer") as MockScorer:
            MockScorer.return_value.score.return_value = _mock_score(80, 7)
            result = score_business_tier1(biz.pk)

        assert result["business_id"] == biz.pk
        assert result["overall_score"] == 80
        assert result["api_cost_cents"] == 7

    def test_scan_businesses_scored_incremented(self):
        biz = _make_business("R2")
        scan = biz.scan
        assert scan.businesses_scored == 0

        with patch("apps.scoring.tasks.Tier1Scorer") as MockScorer:
            MockScorer.return_value.score.return_value = _mock_score(70, 4)
            score_business_tier1(biz.pk)

        scan.refresh_from_db()
        assert scan.businesses_scored == 1

    def test_scan_api_cost_accumulated(self):
        biz = _make_business("R3")
        scan = biz.scan
        # Set an initial cost
        scan.api_cost_cents = 10
        scan.save(update_fields=["api_cost_cents"])

        with patch("apps.scoring.tasks.Tier1Scorer") as MockScorer:
            MockScorer.return_value.score.return_value = _mock_score(65, 8)
            score_business_tier1(biz.pk)

        scan.refresh_from_db()
        assert scan.api_cost_cents == 18  # 10 + 8

    def test_scorer_exception_retries(self):
        biz = _make_business("R4")
        with patch("apps.scoring.tasks.Tier1Scorer") as MockScorer, \
             patch.object(score_business_tier1, "retry", side_effect=RuntimeError("retry")):
            MockScorer.return_value.score.side_effect = ValueError("Claude error")
            try:
                score_business_tier1(biz.pk)
            except RuntimeError:
                pass

        # Scan counters should NOT have been incremented on failure
        biz.scan.refresh_from_db()
        assert biz.scan.businesses_scored == 0

    def test_score_method_called_with_business(self):
        biz = _make_business("R5")
        with patch("apps.scoring.tasks.Tier1Scorer") as MockScorer:
            mock_instance = MockScorer.return_value
            mock_instance.score.return_value = _mock_score()
            score_business_tier1(biz.pk)

        # Verify scorer was called with the business object
        called_with = mock_instance.score.call_args[0][0]
        assert called_with.pk == biz.pk

    def test_multiple_businesses_accumulate_cost_independently(self):
        biz1 = _make_business("R6")
        biz2 = _make_business("R7")

        with patch("apps.scoring.tasks.Tier1Scorer") as MockScorer:
            MockScorer.return_value.score.side_effect = [
                _mock_score(80, 5),
                _mock_score(60, 3),
            ]
            score_business_tier1(biz1.pk)
            score_business_tier1(biz2.pk)

        biz1.scan.refresh_from_db()
        biz2.scan.refresh_from_db()
        assert biz1.scan.api_cost_cents == 5
        assert biz2.scan.api_cost_cents == 3
