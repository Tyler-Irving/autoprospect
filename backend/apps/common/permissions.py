"""Custom DRF permissions for optional API key authentication."""
from __future__ import annotations

import secrets

from django.conf import settings
from rest_framework.permissions import BasePermission


class APIKeyOrOpenPermission(BasePermission):
    """Require a shared API token when API_AUTH_TOKEN is configured.

    If no token is configured, requests are allowed (preserves local/dev UX).
    Supports either:
    - `Authorization: Bearer <token>`
    - `X-API-Key: <token>`
    """

    message = "Authentication credentials were not provided or are invalid."

    def has_permission(self, request, view) -> bool:  # noqa: D401 - DRF signature
        expected = (getattr(settings, "API_AUTH_TOKEN", "") or "").strip()
        if not expected:
            return True

        auth_header = (request.headers.get("Authorization", "") or "").strip()
        api_key_header = (request.headers.get("X-API-Key", "") or "").strip()

        bearer = ""
        if auth_header.lower().startswith("bearer "):
            bearer = auth_header[7:].strip()

        provided = bearer or api_key_header
        if not provided:
            return False
        return secrets.compare_digest(provided, expected)
