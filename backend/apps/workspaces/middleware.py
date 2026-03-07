"""WorkspaceMiddleware — attaches request.workspace for authenticated requests."""
from __future__ import annotations

import logging

from django.utils.functional import SimpleLazyObject

logger = logging.getLogger(__name__)


def _resolve_workspace(request):
    """Return the active Workspace for the current request, or None.

    Resolution order:
    1. X-Workspace-ID header (future multi-workspace support)
    2. The user's owned workspace
    3. Any workspace the user is an active member of
    """
    from rest_framework_simplejwt.authentication import JWTAuthentication

    auth = JWTAuthentication()
    try:
        result = auth.authenticate(request)
    except Exception:
        return None

    if result is None:
        return None

    user, _ = result

    from apps.workspaces.models import WorkspaceMembership

    # Optional: explicit workspace header for future multi-workspace switching
    workspace_id = request.headers.get("X-Workspace-ID")
    if workspace_id:
        try:
            membership = WorkspaceMembership.objects.select_related("workspace").get(
                workspace_id=int(workspace_id),
                user=user,
                is_active=True,
            )
            return membership.workspace
        except (WorkspaceMembership.DoesNotExist, ValueError, TypeError):
            pass

    # Primary: workspace the user owns
    owned = (
        WorkspaceMembership.objects.filter(
            user=user, role=WorkspaceMembership.Role.OWNER, is_active=True
        )
        .select_related("workspace")
        .first()
    )
    if owned:
        return owned.workspace

    # Fallback: any workspace where the user is an active member
    any_membership = (
        WorkspaceMembership.objects.filter(user=user, is_active=True)
        .select_related("workspace")
        .first()
    )
    if any_membership:
        return any_membership.workspace

    # No workspace found — auto-create one for pre-workspace users
    from apps.workspaces.services import get_or_create_workspace_for_user
    return get_or_create_workspace_for_user(user)


class WorkspaceMiddleware:
    """Attach request.workspace lazily for every request.

    The DB query only fires when request.workspace is accessed — no overhead
    on public/auth endpoints that don't touch workspace data.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.workspace = SimpleLazyObject(lambda: _resolve_workspace(request))
        return self.get_response(request)
