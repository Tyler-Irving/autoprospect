"""Tests for leads API — promote, CRUD, dashboard stats."""
import pytest
from unittest.mock import patch


def _create_scan_and_business(workspace=None):
    from apps.scans.models import Scan
    from apps.businesses.models import Business

    scan = Scan.objects.create(
        center_lat="34.8", center_lng="-90.0", radius_meters=5000,
        workspace=workspace,
    )
    business = Business.objects.create(
        google_place_id=f"LT_{scan.pk}",
        name="Test Plumbing",
        latitude="34.8",
        longitude="-90.0",
        scan=scan,
    )
    return scan, business


@pytest.mark.django_db
class TestPromoteEndpoint:
    def test_promote_creates_lead(self, api_client, test_workspace):
        _, business = _create_scan_and_business(workspace=test_workspace)
        url = f"/api/businesses/{business.pk}/promote/"
        with patch("apps.scoring.tasks.score_business_tier2.delay"):
            resp = api_client.post(url)
        assert resp.status_code == 201
        assert "lead_id" in resp.data
        assert resp.data["already_lead"] is False

    def test_promote_idempotent(self, api_client, test_workspace):
        _, business = _create_scan_and_business(workspace=test_workspace)
        url = f"/api/businesses/{business.pk}/promote/"
        with patch("apps.scoring.tasks.score_business_tier2.delay"):
            api_client.post(url)
            resp = api_client.post(url)
        assert resp.status_code == 200
        assert resp.data["already_lead"] is True

    def test_promote_sets_tier2_pending_and_queues_task(self, api_client, test_workspace):
        _, business = _create_scan_and_business(workspace=test_workspace)
        with patch("apps.scoring.tasks.score_business_tier2.delay") as mock_delay:
            resp = api_client.post(f"/api/businesses/{business.pk}/promote/")
        assert resp.status_code == 201
        business.refresh_from_db()
        assert business.tier2_pending is True
        mock_delay.assert_called_once_with(business.pk)

    def test_promote_copies_contact_email_from_enrichment(self, api_client, test_workspace):
        _, business = _create_scan_and_business(workspace=test_workspace)
        from apps.enrichment.models import EnrichmentProfile
        from apps.leads.models import Lead

        EnrichmentProfile.objects.create(business=business, contact_email="owner@biz.com")
        with patch("apps.scoring.tasks.score_business_tier2.delay"):
            resp = api_client.post(f"/api/businesses/{business.pk}/promote/")
        assert resp.status_code == 201
        lead = Lead.objects.get(pk=resp.data["lead_id"])
        assert lead.contact_email == "owner@biz.com"


@pytest.mark.django_db
class TestLeadsAPI:
    def test_create_lead(self, api_client, test_workspace):
        _, business = _create_scan_and_business(workspace=test_workspace)
        with patch("apps.scoring.tasks.score_business_tier2.delay"):
            resp = api_client.post("/api/leads/", {"business_id": business.pk})
        assert resp.status_code == 201
        assert resp.data["business"]["id"] == business.pk

    def test_list_leads(self, api_client, test_workspace):
        _, business = _create_scan_and_business(workspace=test_workspace)
        with patch("apps.scoring.tasks.score_business_tier2.delay"):
            created = api_client.post("/api/leads/", {"business_id": business.pk})
        resp = api_client.get("/api/leads/")
        assert resp.status_code == 200
        results = resp.data.get("results", resp.data)
        assert len(results) == 1
        assert results[0]["id"] == created.data["id"]

    def test_patch_status_creates_activity(self, api_client, test_workspace):
        _, business = _create_scan_and_business(workspace=test_workspace)
        with patch("apps.scoring.tasks.score_business_tier2.delay"):
            lead_resp = api_client.post("/api/leads/", {"business_id": business.pk})
        lead_id = lead_resp.data["id"]

        patch_resp = api_client.patch(f"/api/leads/{lead_id}/", {"outreach_status": "contacted"})
        assert patch_resp.status_code == 200

        activities = api_client.get(f"/api/leads/{lead_id}/activities/")
        assert any(a["activity_type"] == "status_change" for a in activities.data)

    def test_lead_detail_includes_enrichment(self, api_client, test_workspace):
        _, business = _create_scan_and_business(workspace=test_workspace)
        from apps.enrichment.models import EnrichmentProfile
        EnrichmentProfile.objects.create(business=business, website_reachable=True)

        with patch("apps.scoring.tasks.score_business_tier2.delay"):
            lead_resp = api_client.post("/api/leads/", {"business_id": business.pk})
        lead_id = lead_resp.data["id"]

        detail = api_client.get(f"/api/leads/{lead_id}/")
        assert detail.status_code == 200
        assert "enrichment" in detail.data["business"]
        assert detail.data["business"]["enrichment"]["website_reachable"] is True

    def test_generate_outreach_returns_500_on_failure(self, api_client, test_workspace):
        _, business = _create_scan_and_business(workspace=test_workspace)
        with patch("apps.scoring.tasks.score_business_tier2.delay"):
            lead_resp = api_client.post("/api/leads/", {"business_id": business.pk})
        lead_id = lead_resp.data["id"]

        with patch("apps.leads.tasks.run_outreach_generation", side_effect=RuntimeError("boom")):
            resp = api_client.post(f"/api/leads/{lead_id}/generate-outreach/")
        assert resp.status_code == 500

    def test_send_email_maps_value_error_to_400(self, api_client, test_workspace):
        _, business = _create_scan_and_business(workspace=test_workspace)
        with patch("apps.scoring.tasks.score_business_tier2.delay"):
            lead_resp = api_client.post("/api/leads/", {"business_id": business.pk})
        lead_id = lead_resp.data["id"]

        with patch("apps.leads.services.email_sender.send_lead_email", side_effect=ValueError("bad input")):
            resp = api_client.post(f"/api/leads/{lead_id}/send-email/")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestDashboardStats:
    def test_stats_returns_expected_keys(self, api_client):
        resp = api_client.get("/api/dashboard/stats/")
        assert resp.status_code == 200
        for key in ["total_leads", "total_businesses_scanned", "leads_by_status", "monthly_api_cost_cents", "scans_this_month"]:
            assert key in resp.data
