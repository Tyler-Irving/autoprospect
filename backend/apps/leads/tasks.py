"""Lead outreach generation tasks."""
from __future__ import annotations

import json
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def run_outreach_generation(lead_id: int) -> dict:
    """Generate cold email and call script for a lead using Claude.

    Calls Claude twice (email prompt + call script prompt), persists results
    to the Lead model, tracks API cost against the originating scan, and logs
    an activity entry. Called directly by the view for synchronous execution.

    Args:
        lead_id: Primary key of the Lead to generate outreach for.

    Returns:
        Dict with email subject, email body, call script, and generated_at timestamp.

    Raises:
        Lead.DoesNotExist: If the lead is not found.
        ValueError: If Claude returns invalid JSON.
    """
    from apps.leads.models import Lead, LeadActivity
    from apps.scoring.services.claude_client import ClaudeClient
    from apps.scoring.services.prompts import (
        build_email_system,
        build_call_script_system,
        build_outreach_prompt,
    )

    lead = (
        Lead.objects.select_related(
            "business", "business__enrichment", "workspace__agent_config"
        )
        .prefetch_related("business__scores")
        .get(pk=lead_id)
    )

    business = lead.business

    agent_config = None
    try:
        agent_config = lead.workspace.agent_config
    except AttributeError:
        pass

    tier1 = None
    for score in business.scores.all():
        if score.tier == "tier1":
            tier1 = score
            break

    client = ClaudeClient()
    prompt = build_outreach_prompt(business, tier1)

    email_data = client.complete(build_email_system(agent_config), prompt, max_tokens=512)
    call_data = client.complete(build_call_script_system(agent_config), prompt, max_tokens=1024)

    lead.generated_email_subject = email_data.get("subject", "")
    lead.generated_email = email_data.get("body", "")
    lead.generated_call_script = _format_call_script(call_data)
    lead.outreach_generated_at = timezone.now()
    lead.save(update_fields=[
        "generated_email_subject",
        "generated_email",
        "generated_call_script",
        "outreach_generated_at",
        "updated_at",
    ])

    total_cost = email_data.get("api_cost_cents", 0) + call_data.get("api_cost_cents", 0)
    if total_cost and business.scan_id:
        from django.db.models import F
        from apps.scans.models import Scan
        Scan.objects.filter(pk=business.scan_id).update(
            api_cost_cents=F("api_cost_cents") + total_cost,
            updated_at=timezone.now(),
        )

    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.EMAIL_GENERATED,
        description="AI outreach generated: email + call script",
        metadata={
            "email_cost_cents": email_data.get("api_cost_cents", 0),
            "call_cost_cents": call_data.get("api_cost_cents", 0),
        },
    )

    return {
        "lead_id": lead_id,
        "email_subject": lead.generated_email_subject,
        "email_body": lead.generated_email,
        "call_script": lead.generated_call_script,
        "outreach_generated_at": lead.outreach_generated_at.isoformat(),
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_outreach_for_lead(self, lead_id: int) -> dict:
    """Async Celery wrapper around run_outreach_generation."""
    try:
        return run_outreach_generation(lead_id)
    except Exception as exc:
        logger.error("Outreach generation failed for lead %s: %s", lead_id, exc)
        raise self.retry(exc=exc)


def _format_call_script(data: dict) -> str:
    """Convert call script JSON dict to formatted plain text.

    Args:
        data: Parsed JSON dict from Claude's call script response.

    Returns:
        Human-readable call script string with section headers.
    """
    parts = []
    if data.get("opening"):
        parts.append(f"OPENING:\n{data['opening']}")
    if data.get("hook"):
        parts.append(f"HOOK:\n{data['hook']}")
    if data.get("pain_question"):
        parts.append(f"PAIN QUESTION:\n{data['pain_question']}")
    if data.get("bridge"):
        parts.append(f"BRIDGE:\n{data['bridge']}")
    if data.get("cta"):
        parts.append(f"CTA:\n{data['cta']}")
    if data.get("objection_handlers"):
        objection_lines = []
        for h in data["objection_handlers"]:
            objection_lines.append(f"  Q: {h.get('objection', '')}\n  A: {h.get('response', '')}")
        parts.append("OBJECTION HANDLERS:\n" + "\n\n".join(objection_lines))
    return "\n\n".join(parts)
