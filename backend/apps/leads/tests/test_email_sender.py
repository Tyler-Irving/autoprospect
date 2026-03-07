"""Tests for lead email sending service."""
import pytest
from unittest.mock import patch

from apps.leads.services.email_sender import send_lead_email


def _make_lead(suffix="ES", generated_email="Hello", contact_email="owner@example.com"):
    from apps.businesses.models import Business
    from apps.leads.models import Lead
    from apps.scans.models import Scan

    scan = Scan.objects.create(center_lat="34.8", center_lng="-90.0", radius_meters=5000)
    business = Business.objects.create(
        google_place_id=f"lead_email_{suffix}",
        name="Email Sender Biz",
        latitude="34.8",
        longitude="-90.0",
        scan=scan,
    )
    return Lead.objects.create(
        business=business,
        generated_email=generated_email,
        generated_email_subject="Subject",
        contact_email=contact_email,
        outreach_status="outreach_ready",
    )


@pytest.mark.django_db
class TestSendLeadEmail:
    def test_requires_generated_email(self):
        lead = _make_lead("M1", generated_email="")
        with pytest.raises(ValueError, match="No outreach content generated yet"):
            send_lead_email(lead)

    def test_requires_contact_email(self):
        lead = _make_lead("M2", contact_email="")
        with pytest.raises(ValueError, match="No email address"):
            send_lead_email(lead)

    @patch("apps.leads.services.email_sender.settings")
    def test_requires_from_email(self, mock_settings):
        lead = _make_lead("M3")
        mock_settings.DEFAULT_FROM_EMAIL = ""
        mock_settings.ANYMAIL = {"RESEND_API_KEY": "x"}
        with pytest.raises(ValueError, match="EMAIL_FROM is not set"):
            send_lead_email(lead)

    @patch("apps.leads.services.email_sender.settings")
    def test_requires_resend_api_key(self, mock_settings):
        lead = _make_lead("M4")
        mock_settings.DEFAULT_FROM_EMAIL = "from@example.com"
        mock_settings.ANYMAIL = {"RESEND_API_KEY": ""}
        with pytest.raises(ValueError, match="RESEND_API_KEY is not set"):
            send_lead_email(lead)

    @patch("apps.leads.services.email_sender.settings")
    @patch("apps.leads.services.email_sender.EmailMessage")
    def test_sends_and_updates_lead_and_activity(self, MockEmailMessage, mock_settings):
        from apps.leads.models import LeadActivity

        lead = _make_lead("M5")
        mock_settings.DEFAULT_FROM_EMAIL = "from@example.com"
        mock_settings.ANYMAIL = {"RESEND_API_KEY": "rk_test"}
        mock_settings.EMAIL_REPLY_TO = "reply@example.com"

        send_lead_email(lead)

        lead.refresh_from_db()
        assert lead.contact_attempts == 1
        assert lead.outreach_status == "contacted"
        assert lead.last_contacted_at is not None
        assert MockEmailMessage.return_value.send.called
        assert LeadActivity.objects.filter(
            lead=lead,
            activity_type=LeadActivity.ActivityType.EMAIL_SENT,
        ).exists()
