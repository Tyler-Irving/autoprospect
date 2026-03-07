"""Tests for the lead approval queue endpoints."""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

from apps.workspaces.services import get_or_create_workspace_for_user
from apps.businesses.models import Business
from apps.scans.models import Scan
from apps.leads.models import Lead, LeadActivity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(username="approval_tester")


@pytest.fixture
def workspace(db, user):
    return get_or_create_workspace_for_user(user)


@pytest.fixture
def auth_client(db, user, workspace):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def scan(db, workspace, user):
    return Scan.objects.create(
        workspace=workspace,
        owner=user,
        center_lat="34.0",
        center_lng="-118.0",
        radius_meters=5000,
        place_types=["plumber"],
    )


_biz_counter = [0]

@pytest.fixture
def lead(db, workspace, user, scan):
    _biz_counter[0] += 1
    biz = Business.objects.create(
        google_place_id=f"approval_place_{_biz_counter[0]}",
        scan=scan,
        name="Test Plumbing Co",
        formatted_address="123 Main St",
        place_types=["plumber"],
        latitude="34.0",
        longitude="-118.0",
    )
    return Lead.objects.create(
        business=biz,
        owner=user,
        workspace=workspace,
        approval_required=True,
        generated_email_subject="Quick question about your booking process",
        generated_email="Hi there, I noticed...",
        generated_call_script="OPENING: Hi, this is...",
    )


# ---------------------------------------------------------------------------
# GET /api/leads/pending-approval/
# ---------------------------------------------------------------------------

class TestPendingApproval:
    def test_returns_approval_required_leads(self, db, auth_client, workspace, lead):
        resp = auth_client.get("/api/leads/pending-approval/")
        assert resp.status_code == 200
        ids = [l["id"] for l in resp.json()]
        assert lead.id in ids

    def test_excludes_already_approved(self, db, auth_client, workspace, lead):
        from django.utils import timezone
        lead.approved_at = timezone.now()
        lead.save()
        resp = auth_client.get("/api/leads/pending-approval/")
        ids = [l["id"] for l in resp.json()]
        assert lead.id not in ids

    def test_excludes_leads_not_requiring_approval(self, db, auth_client, workspace, lead):
        lead.approval_required = False
        lead.save()
        resp = auth_client.get("/api/leads/pending-approval/")
        ids = [l["id"] for l in resp.json()]
        assert lead.id not in ids

    def test_cross_tenant_isolation(self, db, workspace, lead):
        user_b = User.objects.create_user(username="user_b_approval")
        get_or_create_workspace_for_user(user_b)
        client_b = APIClient()
        refresh = RefreshToken.for_user(user_b)
        client_b.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = client_b.get("/api/leads/pending-approval/")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/leads/{id}/approve/
# ---------------------------------------------------------------------------

class TestApprove:
    def test_approve_clears_approval_required(self, db, auth_client, workspace, lead):
        resp = auth_client.post(f"/api/leads/{lead.id}/approve/")
        assert resp.status_code == 200
        lead.refresh_from_db()
        assert lead.approval_required is False
        assert lead.approved_at is not None
        assert lead.approved_by is not None

    def test_approve_logs_activity(self, db, auth_client, workspace, lead):
        auth_client.post(f"/api/leads/{lead.id}/approve/")
        assert LeadActivity.objects.filter(
            lead=lead,
            activity_type=LeadActivity.ActivityType.OUTREACH_APPROVED,
        ).exists()

    def test_approve_send_now_without_email_config_returns_200(self, db, auth_client, workspace, lead):
        # send_now=True but no email configured — should still return 200 with error detail
        resp = auth_client.post(f"/api/leads/{lead.id}/approve/", {"send_now": True}, format="json")
        # Either 200 (approval succeeded, send may have failed gracefully) or 200
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/leads/{id}/reject/
# ---------------------------------------------------------------------------

class TestReject:
    def test_reject_clears_outreach(self, db, auth_client, workspace, lead):
        resp = auth_client.post(f"/api/leads/{lead.id}/reject/")
        assert resp.status_code == 200
        lead.refresh_from_db()
        assert lead.approval_required is False
        assert lead.generated_email == ""
        assert lead.generated_email_subject == ""
        assert lead.generated_call_script == ""
        assert lead.outreach_generated_at is None

    def test_reject_resets_status_to_new(self, db, auth_client, workspace, lead):
        lead.outreach_status = "outreach_ready"
        lead.save()
        auth_client.post(f"/api/leads/{lead.id}/reject/")
        lead.refresh_from_db()
        assert lead.outreach_status == "new"

    def test_reject_logs_activity(self, db, auth_client, workspace, lead):
        auth_client.post(f"/api/leads/{lead.id}/reject/")
        assert LeadActivity.objects.filter(
            lead=lead,
            activity_type=LeadActivity.ActivityType.OUTREACH_REJECTED,
        ).exists()

    def test_cross_tenant_cannot_reject(self, db, workspace, lead):
        user_b = User.objects.create_user(username="user_b_reject")
        get_or_create_workspace_for_user(user_b)
        client_b = APIClient()
        refresh = RefreshToken.for_user(user_b)
        client_b.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = client_b.post(f"/api/leads/{lead.id}/reject/")
        assert resp.status_code == 404
