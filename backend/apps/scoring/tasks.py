"""Scoring Celery tasks."""
import logging
from typing import Any

from celery import shared_task
from django.db.models import F
from django.utils import timezone

from apps.businesses.models import Business
from apps.scans.models import Scan

from .services.tier1_scorer import Tier1Scorer
from .services.tier2_scorer import Tier2Scorer

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


@shared_task(bind=True, max_retries=2, default_retry_delay=60, rate_limit="3/s")
def score_business_tier2(self, business_id: int) -> dict[str, Any]:
    """Run Tier 2 deep-analysis Claude scoring for a single business.

    Queued automatically when a business is promoted to a lead.

    Args:
        business_id: Primary key of the Business to score.
    """
    try:
        business = Business.objects.select_related("enrichment", "scan").prefetch_related("scores").get(pk=business_id)
    except Business.DoesNotExist:
        logger.error("score_business_tier2: Business %d not found", business_id)
        return {"error": "Business not found"}

    try:
        scorer = Tier2Scorer()
        score = scorer.score(business)

        # Accumulate cost on the parent scan atomically
        Scan.objects.filter(pk=business.scan_id).update(
            api_cost_cents=F("api_cost_cents") + score.api_cost_cents,
            updated_at=timezone.now(),
        )

        # Clear pending flag now that scoring is complete
        Business.objects.filter(pk=business_id).update(tier2_pending=False)

        # Log activity on the associated lead if one exists
        if hasattr(business, "lead"):
            from apps.leads.models import LeadActivity

            LeadActivity.objects.create(
                lead=business.lead,
                activity_type=LeadActivity.ActivityType.TIER2_REQUESTED,
                description=f"Deep analysis completed — score {score.overall_score}/100",
            )

        return {
            "business_id": business_id,
            "overall_score": score.overall_score,
            "api_cost_cents": score.api_cost_cents,
        }

    except Exception as exc:
        logger.exception("score_business_tier2 %d failed: %s", business_id, exc)
        if self.request.retries >= self.max_retries:
            # Final attempt exhausted — clear the pending flag so the UI doesn't hang
            Business.objects.filter(pk=business_id).update(tier2_pending=False)
        raise self.retry(exc=exc)
