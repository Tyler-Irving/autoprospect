"""Enrichment Celery tasks."""
import logging
from typing import Any

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.businesses.models import Business

from .models import EnrichmentProfile
from .services.crawler import WebsiteCrawler

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30, rate_limit="5/s")
def enrich_business(self, business_id: int) -> dict[str, Any]:
    """Crawl a business's website and populate its EnrichmentProfile.

    Args:
        business_id: Primary key of the Business to enrich.
    """
    try:
        business = Business.objects.get(pk=business_id)
    except Business.DoesNotExist:
        logger.error("enrich_business: Business %d not found", business_id)
        return {"error": "Business not found"}

    profile, _ = EnrichmentProfile.objects.get_or_create(business=business)
    profile.status = EnrichmentProfile.Status.IN_PROGRESS
    profile.save(update_fields=["status"])

    try:
        crawler = WebsiteCrawler()
        data = crawler.crawl(business.website_url, business.reviews_data)

        with transaction.atomic():
            for field, value in data.items():
                setattr(profile, field, value)
            profile.status = EnrichmentProfile.Status.COMPLETED
            profile.enriched_at = timezone.now()
            profile.error_log = ""
            profile.save()

        # Increment scan counter atomically
        from django.db.models import F
        from apps.scans.models import Scan
        Scan.objects.filter(pk=business.scan_id).update(
            businesses_enriched=F("businesses_enriched") + 1,
            updated_at=timezone.now(),
        )

        logger.info("Enriched business %d (%s)", business_id, business.name)
        return {"business_id": business_id, "reachable": data.get("website_reachable")}

    except Exception as exc:
        logger.exception("enrich_business %d failed: %s", business_id, exc)
        profile.status = EnrichmentProfile.Status.FAILED
        profile.error_log = str(exc)
        profile.save(update_fields=["status", "error_log"])
        raise self.retry(exc=exc)
