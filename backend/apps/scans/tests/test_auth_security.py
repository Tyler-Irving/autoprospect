"""Security tests for JWT authentication."""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
class TestJWTAuth:
    def test_unauthenticated_returns_401(self):
        resp = APIClient().get("/api/scans/")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer not-a-valid-jwt")
        resp = client.get("/api/scans/")
        assert resp.status_code == 401

    def test_valid_jwt_allows_access(self, api_client):
        resp = api_client.get("/api/scans/")
        assert resp.status_code == 200

    def test_expired_access_token_returns_401(self, db):
        """An expired token is rejected even if the user exists."""
        from datetime import timedelta
        from django.utils import timezone
        from rest_framework_simplejwt.tokens import AccessToken

        user = User.objects.create_user(username="github_expired")
        token = AccessToken.for_user(user)
        # Manually backdate the expiry
        token.set_exp(lifetime=-timedelta(seconds=1))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
        resp = client.get("/api/scans/")
        assert resp.status_code == 401
