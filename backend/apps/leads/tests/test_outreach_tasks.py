"""Tests for outreach generation task/service behavior."""
import pytest
from unittest.mock import patch

from apps.leads.tasks import _format_call_script, run_outreach_generation


def _make_lead(suffix="OG"):
    from apps.businesses.models import Business
    from apps.leads.models import Lead
    from apps.scans.models import Scan

    scan = Scan.objects.create(center_lat="34.8", center_lng="-90.0", radius_meters=5000)
    business = Business.objects.create(
        google_place_id=f"lead_outreach_{suffix}",
        name="Outreach Test Biz",
        latitude="34.8",
        longitude="-90.0",
        scan=scan,
    )
    lead = Lead.objects.create(business=business, contact_email="owner@example.com")
    return lead, scan


@pytest.mark.django_db
class TestRunOutreachGeneration:
    def test_persists_generated_content_and_cost_and_activity(self):
        from apps.leads.models import LeadActivity

        lead, scan = _make_lead("S1")
        email_payload = {"subject": "Quick question", "body": "Email body", "api_cost_cents": 4}
        call_payload = {
            "opening": "Hi",
            "hook": "Saw your reviews",
            "pain_question": "How are follow-ups handled?",
            "bridge": "We help automate that",
            "cta": "Open to 15 minutes?",
            "objection_handlers": [{"objection": "busy", "response": "understood"}],
            "api_cost_cents": 6,
        }

        with patch("apps.scoring.services.claude_client.ClaudeClient") as MockClient:
            MockClient.return_value.complete.side_effect = [email_payload, call_payload]
            result = run_outreach_generation(lead.pk)

        lead.refresh_from_db()
        scan.refresh_from_db()
        assert result["lead_id"] == lead.pk
        assert lead.generated_email_subject == "Quick question"
        assert lead.generated_email == "Email body"
        assert "OPENING:" in lead.generated_call_script
        assert lead.outreach_generated_at is not None
        assert scan.api_cost_cents == 10
        assert LeadActivity.objects.filter(
            lead=lead,
            activity_type=LeadActivity.ActivityType.EMAIL_GENERATED,
        ).exists()

    def test_invalid_claude_response_bubbles_up(self):
        lead, _ = _make_lead("S2")
        with patch("apps.scoring.services.claude_client.ClaudeClient") as MockClient:
            MockClient.return_value.complete.side_effect = ValueError("bad json")
            with pytest.raises(ValueError, match="bad json"):
                run_outreach_generation(lead.pk)


class TestFormatCallScript:
    def test_formats_sections_and_objections(self):
        out = _format_call_script({
            "opening": "Hi there",
            "hook": "Saw your profile",
            "pain_question": "How do you manage calls?",
            "bridge": "We can automate follow-ups.",
            "cta": "15 min call?",
            "objection_handlers": [{"objection": "not interested", "response": "fair"}],
        })
        assert "OPENING:" in out
        assert "OBJECTION HANDLERS:" in out
        assert "Q: not interested" in out
