"""Tests for settings and dashboard API endpoints."""
import pytest
from django.test import override_settings

from apps.scans.models import Scan, SiteConfig


@pytest.mark.django_db
class TestSiteSettingsAPI:
    @override_settings(
        GOOGLE_PLACES_API_KEY="abcdef1234567890",
        ANTHROPIC_API_KEY="anthro1234567890",
        ANYMAIL={"RESEND_API_KEY": "resend1234567890"},
        DEFAULT_FROM_EMAIL="from@example.com",
        EMAIL_REPLY_TO="reply@example.com",
    )
    def test_get_returns_masked_keys_and_config(self, api_client):
        SiteConfig.get()
        resp = api_client.get("/api/settings/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["google_places_key_set"] is True
        assert data["anthropic_key_set"] is True
        assert data["resend_key_set"] is True
        assert data["google_places_key_masked"].startswith("abcdef")
        assert "•" in data["google_places_key_masked"]

    def test_patch_rejects_invalid_monthly_budget(self, api_client):
        resp = api_client.patch("/api/settings/", {"monthly_budget_cents": "abc"}, format="json")
        assert resp.status_code == 400
        assert "must be an integer" in resp.json()["detail"]

    def test_patch_rejects_invalid_max_businesses(self, api_client):
        resp = api_client.patch("/api/settings/", {"max_businesses_per_scan": "abc"}, format="json")
        assert resp.status_code == 400
        assert "must be an integer" in resp.json()["detail"]

    def test_patch_updates_and_clamps_to_non_negative(self, api_client):
        resp = api_client.patch(
            "/api/settings/",
            {"monthly_budget_cents": -50, "max_businesses_per_scan": -2},
            format="json",
        )
        assert resp.status_code == 200
        cfg = SiteConfig.get()
        assert cfg.monthly_budget_cents == 0
        assert cfg.max_businesses_per_scan == 0


@pytest.mark.django_db
class TestDashboardStatsAPI:
    def test_counts_scans_this_month(self, api_client, scan_factory):
        scan_factory()
        scan_factory()
        resp = api_client.get("/api/dashboard/stats/")
        assert resp.status_code == 200
        assert resp.json()["scans_this_month"] >= 2
