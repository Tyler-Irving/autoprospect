"""Scoring Celery tasks."""
import logging
from typing import Any

from celery import shared_task
from django.db.models import F
from django.utils import timezone

from apps.businesses.models import Business
from apps.scans.models import Scan

from .services.tier1_scorer import Tier1Scorer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, rate_limit="3/s")
def score_business_tier1(self, business_id: int) -> dict[str, Any]:
    """Run Tier 1 Claude scoring for a single business.

    Args:
        business_id: Primary key of the Business to score.
    """
    try:
        business = Business.objects.select_related("enrichment", "scan").get(pk=business_id)
    except Business.DoesNotExist:
        logger.error("score_business_tier1: Business %d not found", business_id)
        return {"error": "Business not found"}

    try:
        scorer = Tier1Scorer()
        score = scorer.score(business)

        # Increment scan counter and accumulate cost atomically
        Scan.objects.filter(pk=business.scan_id).update(
            businesses_scored=F("businesses_scored") + 1,
            api_cost_cents=F("api_cost_cents") + score.api_cost_cents,
            updated_at=timezone.now(),
        )

        return {
            "business_id": business_id,
            "overall_score": score.overall_score,
            "api_cost_cents": score.api_cost_cents,
        }

    except Exception as exc:
        logger.exception("score_business_tier1 %d failed: %s", business_id, exc)
        raise self.retry(exc=exc)
