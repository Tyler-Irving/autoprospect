"""Security tests for optional API key auth."""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestAPIKeyAuth:
    @override_settings(API_AUTH_TOKEN="secret-token")
    def test_missing_token_denied(self):
        resp = APIClient().get("/api/scans/")
        assert resp.status_code == 403

    @override_settings(API_AUTH_TOKEN="secret-token")
    def test_bearer_token_allows_access(self):
        resp = APIClient().get("/api/scans/", HTTP_AUTHORIZATION="Bearer secret-token")
        assert resp.status_code == 200

    @override_settings(API_AUTH_TOKEN="secret-token")
    def test_x_api_key_allows_access(self):
        resp = APIClient().get("/api/scans/", HTTP_X_API_KEY="secret-token")
        assert resp.status_code == 200
