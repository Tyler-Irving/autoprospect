"""Tests for workspace creation, scoping, and cross-tenant isolation."""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.workspaces.services import get_or_create_workspace_for_user, claim_orphaned_records


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_a(db):
    return User.objects.create_user(username="github_111", first_name="alice")


@pytest.fixture
def user_b(db):
    return User.objects.create_user(username="github_222", first_name="bob")


@pytest.fixture
def workspace_a(db, user_a):
    return get_or_create_workspace_for_user(user_a)


@pytest.fixture
def workspace_b(db, user_b):
    return get_or_create_workspace_for_user(user_b)


def _auth_client(user: User) -> APIClient:
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ---------------------------------------------------------------------------
# Workspace creation
# ---------------------------------------------------------------------------

class TestWorkspaceCreation:
    def test_creates_workspace_and_owner_membership(self, db, user_a, workspace_a):
        assert workspace_a.owner == user_a
        membership = WorkspaceMembership.objects.get(workspace=workspace_a, user=user_a)
        assert membership.role == WorkspaceMembership.Role.OWNER

    def test_idempotent_get_or_create(self, db, user_a, workspace_a):
        """Calling get_or_create_workspace twice returns the same workspace."""
        second = get_or_create_workspace_for_user(user_a)
        assert second.pk == workspace_a.pk
        assert WorkspaceMembership.objects.filter(user=user_a).count() == 1

    def test_slug_auto_generated(self, db, user_a, workspace_a):
        assert workspace_a.slug != ""
        assert " " not in workspace_a.slug

    def test_two_users_get_separate_workspaces(self, db, workspace_a, workspace_b):
        assert workspace_a.pk != workspace_b.pk


# ---------------------------------------------------------------------------
# Orphaned record claiming
# ---------------------------------------------------------------------------

class TestClaimOrphanedRecords:
    def test_claims_workspace_less_scans(self, db, user_a, workspace_a):
        from apps.scans.models import Scan

        scan = Scan.objects.create(
            center_lat="34.0", center_lng="-118.0",
            radius_meters=5000, workspace=None,
        )
        claim_orphaned_records(user_a, workspace_a)
        scan.refresh_from_db()
        assert scan.workspace == workspace_a

    def test_does_not_overwrite_existing_workspace(self, db, user_a, workspace_a, user_b, workspace_b):
        from apps.scans.models import Scan

        scan_b = Scan.objects.create(
            center_lat="34.0", center_lng="-118.0",
            radius_meters=5000, workspace=workspace_b,
        )
        claim_orphaned_records(user_a, workspace_a)
        scan_b.refresh_from_db()
        assert scan_b.workspace == workspace_b  # unchanged


# ---------------------------------------------------------------------------
# Workspace API endpoint
# ---------------------------------------------------------------------------

class TestWorkspaceEndpoint:
    def test_get_workspace(self, db, user_a, workspace_a):
        client = _auth_client(user_a)
        resp = client.get("/api/workspace/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == workspace_a.pk
        assert data["name"] == workspace_a.name
        assert data["role"] == "owner"

    def test_patch_workspace_name(self, db, user_a, workspace_a):
        client = _auth_client(user_a)
        resp = client.patch("/api/workspace/", {"name": "Acme Plumbing Co"}, format="json")
        assert resp.status_code == 200
        workspace_a.refresh_from_db()
        assert workspace_a.name == "Acme Plumbing Co"

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()
        resp = client.get("/api/workspace/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Cross-tenant scan isolation
# ---------------------------------------------------------------------------

class TestScanIsolation:
    def test_user_a_cannot_see_user_b_scans(self, db, user_a, workspace_a, user_b, workspace_b):
        from apps.scans.models import Scan

        scan_b = Scan.objects.create(
            center_lat="34.0", center_lng="-118.0",
            radius_meters=5000, workspace=workspace_b,
        )
        client_a = _auth_client(user_a)
        resp = client_a.get("/api/scans/")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["results"]]
        assert scan_b.pk not in ids

    def test_user_a_cannot_get_user_b_scan_by_id(self, db, user_a, workspace_a, user_b, workspace_b):
        from apps.scans.models import Scan

        scan_b = Scan.objects.create(
            center_lat="34.0", center_lng="-118.0",
            radius_meters=5000, workspace=workspace_b,
        )
        client_a = _auth_client(user_a)
        resp = client_a.get(f"/api/scans/{scan_b.pk}/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Cross-tenant lead isolation
# ---------------------------------------------------------------------------

class TestLeadIsolation:
    def _make_lead(self, workspace):
        from apps.scans.models import Scan
        from apps.businesses.models import Business
        from apps.leads.models import Lead

        scan = Scan.objects.create(
            center_lat="34.0", center_lng="-118.0",
            radius_meters=5000, workspace=workspace,
        )
        biz = Business.objects.create(
            google_place_id=f"place_{workspace.pk}_{scan.pk}",
            name="Test Biz",
            formatted_address="123 Main St",
            latitude="34.0",
            longitude="-118.0",
            scan=scan,
        )
        return Lead.objects.create(business=biz, workspace=workspace)

    def test_user_a_cannot_see_user_b_leads(self, db, user_a, workspace_a, user_b, workspace_b):
        lead_b = self._make_lead(workspace_b)
        client_a = _auth_client(user_a)
        resp = client_a.get("/api/leads/")
        assert resp.status_code == 200
        ids = [l["id"] for l in resp.json()["results"]]
        assert lead_b.pk not in ids

    def test_user_a_cannot_get_user_b_lead_by_id(self, db, user_a, workspace_a, user_b, workspace_b):
        lead_b = self._make_lead(workspace_b)
        client_a = _auth_client(user_a)
        resp = client_a.get(f"/api/leads/{lead_b.pk}/")
        assert resp.status_code == 404

    def test_user_a_cannot_patch_user_b_lead(self, db, user_a, workspace_a, user_b, workspace_b):
        lead_b = self._make_lead(workspace_b)
        client_a = _auth_client(user_a)
        resp = client_a.patch(f"/api/leads/{lead_b.pk}/", {"notes": "hacked"}, format="json")
        assert resp.status_code == 404
