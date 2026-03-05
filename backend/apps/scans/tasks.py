"""Scan orchestrator Celery task — Phase 2: discovery + enrichment."""
import logging
from typing import Any

from celery import chord, shared_task
from django.db import transaction
from django.utils import timezone

from apps.businesses.models import Business
from apps.businesses.services.google_places import GooglePlacesService

from .models import Scan

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def run_scan(self, scan_id: int) -> dict[str, Any]:
    """Orchestrate a full scan: discovery → enrichment.

    Args:
        scan_id: Primary key of the Scan to run.
    """
    try:
        scan = Scan.objects.get(pk=scan_id)
    except Scan.DoesNotExist:
        logger.error("Scan %d not found", scan_id)
        return {"error": "Scan not found"}

    try:
        business_ids = _run_discovery(scan)

        if not business_ids:
            scan.status = Scan.Status.COMPLETED
            scan.completed_at = timezone.now()
            scan.save(update_fields=["status", "completed_at", "updated_at"])
            return {"scan_id": scan_id, "businesses_found": 0}

        # Transition to enrichment → scoring pipeline via nested chords:
        # chord(enrich group, score_all.s(scan_id, business_ids))
        # chord(score group, finalize_scan.s(scan_id))
        from apps.enrichment.tasks import enrich_business

        scan.status = Scan.Status.ENRICHING_T1
        scan.save(update_fields=["status", "updated_at"])

        chord(
            (enrich_business.s(biz_id) for biz_id in business_ids),
            start_scoring.s(scan_id, business_ids),
        ).delay()

        return {"scan_id": scan_id, "businesses_found": len(business_ids)}

    except Exception as exc:
        logger.exception("Scan %d failed: %s", scan_id, exc)
        scan.status = Scan.Status.FAILED
        scan.error_message = str(exc)
        scan.save(update_fields=["status", "error_message", "updated_at"])
        raise self.retry(exc=exc)


@shared_task(bind=True)
def start_scoring(self, _enrich_results: list, scan_id: int, business_ids: list[int]) -> dict[str, Any]:
    """Chord callback after all enrichment tasks complete — kicks off Tier 1 scoring.

    Args:
        _enrich_results: Passed by chord (enrichment results, ignored).
        scan_id: Primary key of the Scan.
        business_ids: List of Business PKs to score.
    """
    try:
        scan = Scan.objects.get(pk=scan_id)
    except Scan.DoesNotExist:
        return {"error": "Scan not found"}

    from apps.scoring.tasks import score_business_tier1

    scan.status = Scan.Status.SCORING_T1
    scan.save(update_fields=["status", "updated_at"])

    chord(
        (score_business_tier1.s(biz_id) for biz_id in business_ids),
        finalize_scan.s(scan_id),
    ).delay()

    return {"scan_id": scan_id, "scoring_started": len(business_ids)}


@shared_task(bind=True)
def finalize_scan(self, results: list, scan_id: int) -> dict[str, Any]:
    """Called by chord callback after all scoring tasks complete.

    Args:
        results: List of results from score_business_tier1 tasks (passed by chord).
        scan_id: Primary key of the Scan to finalize.
    """
    try:
        scan = Scan.objects.get(pk=scan_id)
    except Scan.DoesNotExist:
        return {"error": "Scan not found"}

    scan.status = Scan.Status.COMPLETED
    scan.completed_at = timezone.now()
    scan.save(update_fields=["status", "completed_at", "updated_at"])

    scored = sum(1 for r in (results or []) if isinstance(r, dict) and "overall_score" in r)
    logger.info("Scan %d finalized: %d businesses scored", scan_id, scored)
    return {"scan_id": scan_id, "scored": scored}


def _run_discovery(scan: Scan) -> list[int]:
    """Run Google Places discovery and return list of Business PKs."""
    scan.status = Scan.Status.DISCOVERING
    scan.save(update_fields=["status", "updated_at"])

    from django.conf import settings
    service = GooglePlacesService()
    max_businesses = getattr(settings, "MAX_BUSINESSES_PER_SCAN", 300)

    all_places = service.search_nearby(
        lat=float(scan.center_lat),
        lng=float(scan.center_lng),
        radius_meters=scan.radius_meters,
        place_types=scan.place_types,
        keyword=scan.keyword,
        max_results=min(20, max_businesses),
    )

    business_ids = []
    for raw_place in all_places:
        parsed = service.parse_place(raw_place)
        if not parsed["google_place_id"]:
            continue
        business, _ = _upsert_business(scan, parsed)
        business_ids.append(business.pk)

    scan.businesses_found = len(business_ids)
    scan.save(update_fields=["businesses_found", "updated_at"])

    return business_ids


@transaction.atomic
def _upsert_business(scan: Scan, data: dict[str, Any]) -> tuple[Business, bool]:
    """Create or update a Business record, always assigning to current scan."""
    business, created = Business.objects.get_or_create(
        google_place_id=data["google_place_id"],
        defaults={**data, "scan": scan},
    )
    if not created:
        for field, value in data.items():
            if field != "google_place_id":
                setattr(business, field, value)
        business.scan = scan
        business.save()
    return business, created
