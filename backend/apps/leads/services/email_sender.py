"""Email sending service for lead outreach."""
from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from apps.leads.models import Lead, LeadActivity


def send_lead_email(lead: Lead) -> dict[str, str]:
    """Send the generated cold email for a lead via Resend.

    Uses the contact_email on the lead as the recipient (manually entered by
    the user). Updates last_contacted_at, increments contact_attempts, and
    auto-advances outreach_status to 'contacted' if currently 'outreach_ready'.
    Logs a LeadActivity entry on success.

    Args:
        lead: Lead instance. Must have generated_email populated.

    Returns:
        Dict with 'sent_to' key containing the recipient address.

    Raises:
        ValueError: If no outreach content exists or no recipient email is set.
    """
    if not lead.generated_email:
        raise ValueError("No outreach content generated yet. Generate email content first.")

    recipient = lead.contact_email.strip()
    if not recipient:
        raise ValueError(
            f"No email address for {lead.business.name}. "
            "Enter one in the contact email field below."
        )

    if not settings.DEFAULT_FROM_EMAIL:
        raise ValueError("EMAIL_FROM is not set. Add it to your .env file and restart the server.")

    if not settings.ANYMAIL.get("RESEND_API_KEY"):
        raise ValueError("RESEND_API_KEY is not set. Add it to your .env file and restart the server.")

    reply_to = getattr(settings, "EMAIL_REPLY_TO", "")

    msg = EmailMessage(
        subject=lead.generated_email_subject or f"Quick question — {lead.business.name}",
        body=lead.generated_email,
        to=[recipient],
        reply_to=[reply_to] if reply_to else [],
    )
    msg.send()

    now = timezone.now()
    update_fields = ["last_contacted_at", "contact_attempts", "updated_at"]
    lead.last_contacted_at = now
    lead.contact_attempts += 1

    if lead.outreach_status == Lead.OutreachStatus.OUTREACH_READY:
        lead.outreach_status = Lead.OutreachStatus.CONTACTED
        update_fields.append("outreach_status")

    lead.save(update_fields=update_fields)

    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.EMAIL_SENT,
        description=f"Cold email sent to {recipient}",
        metadata={"to": recipient, "subject": lead.generated_email_subject},
    )

    return {"sent_to": recipient}
