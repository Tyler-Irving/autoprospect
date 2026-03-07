"""Auth views — GitHub OAuth exchange and current-user endpoint."""
from __future__ import annotations

import logging

import httpx
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


def _user_payload(user: User) -> dict:
    """Serialize a user for API responses."""
    github_id = user.username.replace("github_", "")
    return {
        "id": user.pk,
        "github_login": user.first_name,
        "name": user.get_full_name() or user.first_name,
        "email": user.email,
        "avatar": f"https://avatars.githubusercontent.com/u/{github_id}",
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def github_login(request):
    """Exchange a GitHub OAuth code for JWT tokens.

    Body:
        code: GitHub OAuth authorization code.
        redirect_uri: The redirect URI used when requesting the code.
    """
    code = request.data.get("code", "").strip()
    redirect_uri = request.data.get("redirect_uri", "").strip()
    if not code:
        return Response({"detail": "code is required."}, status=400)

    client_id = settings.GITHUB_CLIENT_ID
    client_secret = settings.GITHUB_CLIENT_SECRET
    if not client_id or not client_secret:
        return Response({"detail": "GitHub OAuth is not configured on the server."}, status=503)

    # Exchange code for a GitHub access token
    try:
        with httpx.Client(timeout=10) as client:
            token_resp = client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
    except httpx.HTTPError as exc:
        logger.error("GitHub token exchange failed: %s", exc)
        return Response({"detail": "GitHub authentication failed."}, status=502)

    github_access_token = token_data.get("access_token")
    if not github_access_token:
        error = token_data.get("error_description", token_data.get("error", "unknown"))
        logger.error("GitHub did not return access_token: %s", error)
        return Response({"detail": f"GitHub denied the request: {error}"}, status=400)

    # Fetch GitHub user profile
    try:
        with httpx.Client(timeout=10) as client:
            user_resp = client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {github_access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            user_resp.raise_for_status()
            gh = user_resp.json()
    except httpx.HTTPError as exc:
        logger.error("GitHub user fetch failed: %s", exc)
        return Response({"detail": "Could not retrieve GitHub user info."}, status=502)

    github_id = gh.get("id")
    if not github_id:
        return Response({"detail": "Invalid GitHub user response."}, status=400)

    github_login_name = gh.get("login", "")
    github_email = gh.get("email") or ""
    github_name = gh.get("name") or github_login_name

    # Get or create a Django user keyed on GitHub ID
    username = f"github_{github_id}"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": github_login_name[:150],
            "last_name": github_name[:150],
            "email": github_email,
        },
    )
    if not created:
        user.first_name = github_login_name[:150]
        user.last_name = github_name[:150]
        user.email = github_email
        user.save(update_fields=["first_name", "last_name", "email"])

    # First ever user: claim all existing orphaned records so no data is lost
    if created and User.objects.count() == 1:
        _claim_orphaned_records(user)

    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": _user_payload(user),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """Return the authenticated user's profile."""
    return Response(_user_payload(request.user))


def _claim_orphaned_records(user: User) -> None:
    """Assign all owner-less records to the first user who logs in.

    This handles the transition from the single-user tool to multi-user without
    losing any previously created scans or leads.
    """
    from apps.leads.models import Lead, LeadList
    from apps.scans.models import Scan

    scan_count = Scan.objects.filter(owner__isnull=True).update(owner=user)
    lead_count = Lead.objects.filter(owner__isnull=True).update(owner=user)
    LeadList.objects.filter(owner__isnull=True).update(owner=user)
    logger.info(
        "Claimed %d scans and %d leads for first user %s",
        scan_count, lead_count, user.username,
    )
