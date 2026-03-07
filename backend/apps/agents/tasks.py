"""Agent Celery tasks — scheduled scan execution."""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0, name="apps.agents.tasks.run_scheduled_scan")
def run_scheduled_scan(self, schedule_id: int) -> dict:
    """Execute a scan triggered by an AgentSchedule.

    Skips silently if:
    - Schedule is inactive or deleted.
    - Workspace's agent is paused.
    - No default lat/lng is configured on the AgentConfig.

    Args:
        schedule_id: Primary key of the AgentSchedule to run.

    Returns:
        Dict with scan_id and status, or a reason string if skipped.
    """
    from apps.agents.models import AgentSchedule
    from apps.scans.models import Scan
    from apps.scans.tasks import run_scan

    try:
        schedule = AgentSchedule.objects.select_related(
            "workspace__agent_config",
            "workspace__owner",
        ).get(pk=schedule_id, is_active=True)
    except AgentSchedule.DoesNotExist:
        logger.info("run_scheduled_scan: schedule %d not found or inactive — skipping", schedule_id)
        return {"skipped": "schedule not found or inactive"}

    config = None
    try:
        config = schedule.workspace.agent_config
    except AttributeError:
        pass

    if config and config.is_paused:
        logger.info("run_scheduled_scan: workspace '%s' is paused — skipping", schedule.workspace.name)
        return {"skipped": "agent paused"}

    if not config or not config.default_lat or not config.default_lng:
        logger.warning(
            "run_scheduled_scan: no default location for workspace '%s' — skipping",
            schedule.workspace.name,
        )
        return {"skipped": "no default location configured"}

    scan = Scan.objects.create(
        workspace=schedule.workspace,
        owner=schedule.workspace.owner,
        center_lat=config.default_lat,
        center_lng=config.default_lng,
        radius_meters=schedule.scan_radius_meters,
        place_types=schedule.scan_place_types,
        keyword=schedule.scan_keyword,
        trigger_type="scheduled",
        label=f"Scheduled: {schedule.name}",
    )

    run_scan.delay(scan.id)

    schedule.last_run_at = timezone.now()
    schedule.save(update_fields=["last_run_at", "updated_at"])

    logger.info(
        "run_scheduled_scan: created scan %d for workspace '%s'",
        scan.pk,
        schedule.workspace.name,
    )
    return {"scan_id": scan.pk, "status": "queued"}
