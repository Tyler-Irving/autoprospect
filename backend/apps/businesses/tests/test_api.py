"""Tests for Businesses API endpoints."""
import pytest
from unittest.mock import patch
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestBusinessAPI:
    def test_list_businesses(self, api_client, business_factory):
        b1 = business_factory(name="Biz One")
        b2 = business_factory(name="Biz Two")
        response = api_client.get('/api/businesses/')
        assert response.status_code == 200
        raw = response.json()
        payload = raw.get("results", raw) if isinstance(raw, dict) else raw
        ids = {item["id"] for item in payload}
        assert ids == {b1.pk, b2.pk}

    def test_get_business_detail(self, api_client, business_factory):
        biz = business_factory(name='Joe Plumbing')
        response = api_client.get(f'/api/businesses/{biz.pk}/')
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Joe Plumbing'
        assert 'overall_score' in data
        assert 'has_lead' in data

    def test_map_data_returns_markers(self, api_client, scan_factory, business_factory):
        scan = scan_factory()
        business_factory(scan=scan)
        business_factory(scan=scan)
        response = api_client.get('/api/businesses/map-data/', {'scan': scan.pk})
        assert response.status_code == 200
        markers = response.json()
        assert len(markers) == 2
        for m in markers:
            assert 'id' in m
            assert 'latitude' in m
            assert 'longitude' in m
            assert 'name' in m

    def test_map_data_filter_by_scan(self, api_client, scan_factory, business_factory):
        scan1 = scan_factory()
        scan2 = scan_factory()
        b1 = business_factory(scan=scan1)
        business_factory(scan=scan2)

        response = api_client.get('/api/businesses/map-data/', {'scan': scan1.pk})
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["id"] == b1.pk

    def test_enrich_tier2_requires_lead(self, api_client, business_factory):
        biz = business_factory()
        resp = api_client.post(f"/api/businesses/{biz.pk}/enrich-tier2/")
        assert resp.status_code == 400

    def test_enrich_tier2_returns_500_on_scorer_error(self, api_client, business_factory):
        from apps.leads.models import Lead

        biz = business_factory()
        Lead.objects.create(business=biz)
        with patch("apps.scoring.services.tier2_scorer.Tier2Scorer") as MockScorer:
            MockScorer.return_value.score.side_effect = RuntimeError("bad response")
            resp = api_client.post(f"/api/businesses/{biz.pk}/enrich-tier2/")
        assert resp.status_code == 500
        assert "Tier 2 scoring failed" in resp.json()["detail"]

    def test_enrich_tier2_success_returns_score_and_updates_scan_cost(self, api_client, business_factory):
        from apps.scoring.models import AutomationScore
        from apps.leads.models import Lead, LeadActivity

        biz = business_factory()
        scan = biz.scan
        Lead.objects.create(business=biz)

        fake_score = AutomationScore.objects.create(
            business=biz,
            tier="tier2",
            overall_score=87,
            confidence="0.80",
            crm_score=80,
            scheduling_score=85,
            marketing_score=86,
            invoicing_score=90,
            key_signals=["signal"],
            summary="summary",
            recommended_pitch_angle="pitch",
            estimated_deal_value="high",
            full_dossier="dossier",
            competitor_analysis="analysis",
            model_used="test-model",
            prompt_tokens=1,
            completion_tokens=1,
            api_cost_cents=11,
        )

        with patch("apps.scoring.services.tier2_scorer.Tier2Scorer") as MockScorer:
            MockScorer.return_value.score.return_value = fake_score
            resp = api_client.post(f"/api/businesses/{biz.pk}/enrich-tier2/")

        assert resp.status_code == 200
        scan.refresh_from_db()
        assert scan.api_cost_cents == 11
        assert LeadActivity.objects.filter(
            lead=biz.lead,
            activity_type=LeadActivity.ActivityType.TIER2_REQUESTED,
        ).exists()
