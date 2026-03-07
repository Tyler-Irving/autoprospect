"""Signals for AgentSchedule — keeps django-celery-beat PeriodicTask in sync."""
from __future__ import annotations

import json
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _periodic_task_name(schedule_id: int) -> str:
    return f"agent-schedule-{schedule_id}"


def _sync_periodic_task(instance) -> None:
    """Create or update the PeriodicTask that triggers run_scheduled_scan."""
    from django_celery_beat.models import CrontabSchedule, PeriodicTask

    name = _periodic_task_name(instance.pk)

    if not instance.is_active or not instance.cron_expression:
        PeriodicTask.objects.filter(name=name).delete()
        return

    parts = instance.cron_expression.split()
    if len(parts) != 5:
        logger.warning("AgentSchedule %d: invalid cron '%s'", instance.pk, instance.cron_expression)
        return

    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute=parts[0],
        hour=parts[1],
        day_of_month=parts[2],
        month_of_year=parts[3],
        day_of_week=parts[4],
    )

    PeriodicTask.objects.update_or_create(
        name=name,
        defaults={
            "crontab": crontab,
            "task": "apps.agents.tasks.run_scheduled_scan",
            "args": json.dumps([instance.pk]),
            "enabled": True,
        },
    )

    # Persist the task name for easy cleanup on delete
    if instance.celery_task_name != name:
        type(instance).objects.filter(pk=instance.pk).update(celery_task_name=name)


@receiver(post_save, sender="agents.AgentSchedule")
def on_schedule_save(sender, instance, **kwargs):
    """Sync the linked PeriodicTask whenever a schedule is saved."""
    try:
        _sync_periodic_task(instance)
    except Exception:
        logger.exception("Failed to sync PeriodicTask for AgentSchedule %d", instance.pk)


@receiver(post_delete, sender="agents.AgentSchedule")
def on_schedule_delete(sender, instance, **kwargs):
    """Remove the linked PeriodicTask when a schedule is deleted."""
    try:
        from django_celery_beat.models import PeriodicTask
        PeriodicTask.objects.filter(name=_periodic_task_name(instance.pk)).delete()
    except Exception:
        logger.exception("Failed to delete PeriodicTask for AgentSchedule %d", instance.pk)
