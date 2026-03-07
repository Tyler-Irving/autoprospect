"""Pytest fixtures shared across all test modules."""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.workspaces.models import WorkspaceMembership
from apps.workspaces.services import get_or_create_workspace_for_user


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def test_user(db):
    """A Django user with a workspace, suitable for API tests."""
    user = User.objects.create_user(username="github_99999", first_name="testuser")
    return user


@pytest.fixture
def test_workspace(db, test_user):
    """The workspace belonging to test_user."""
    return get_or_create_workspace_for_user(test_user)


@pytest.fixture
def api_client(db, test_user, test_workspace):
    """An authenticated APIClient with a valid JWT for test_user."""
    client = APIClient()
    refresh = RefreshToken.for_user(test_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ---------------------------------------------------------------------------
# Model factories
# ---------------------------------------------------------------------------

@pytest.fixture
def scan_factory(db, test_workspace):
    """Factory for creating Scan instances in tests."""
    from apps.scans.models import Scan

    def _factory(**kwargs):
        defaults = {
            "center_lat": "34.0522000",
            "center_lng": "-118.2437000",
            "radius_meters": 8000,
            "place_types": ["plumber"],
            "label": "Test Scan",
            "workspace": test_workspace,
        }
        defaults.update(kwargs)
        return Scan.objects.create(**defaults)

    return _factory


@pytest.fixture
def business_factory(db, scan_factory):
    """Factory for creating Business instances in tests."""
    from apps.businesses.models import Business

    _counter = [0]

    def _factory(scan=None, **kwargs):
        if scan is None:
            scan = scan_factory()
        _counter[0] += 1
        defaults = {
            "google_place_id": f"test_place_{_counter[0]}",
            "name": "Test Plumbing Co",
            "latitude": "34.0525000",
            "longitude": "-118.2440000",
            "scan": scan,
        }
        defaults.update(kwargs)
        return Business.objects.create(**defaults)

    return _factory
