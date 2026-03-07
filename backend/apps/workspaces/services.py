"""Workspace service — business logic for workspace creation and resolution."""
from __future__ import annotations

import logging

from django.contrib.auth.models import User

from .models import Workspace, WorkspaceMembership

logger = logging.getLogger(__name__)


def get_or_create_workspace_for_user(user: User) -> Workspace:
    """Return the user's primary workspace, creating it if it doesn't exist.

    A user's primary workspace is the one where they are the owner.
    On first login this will always create a new workspace.
    """
    membership = (
        WorkspaceMembership.objects.filter(user=user, role=WorkspaceMembership.Role.OWNER)
        .select_related("workspace")
        .first()
    )
    if membership:
        return membership.workspace

    # Create a workspace from the user's GitHub login name
    display_name = user.first_name or user.username
    workspace = Workspace.objects.create(
        name=f"{display_name}'s Workspace",
        owner=user,
    )
    WorkspaceMembership.objects.create(
        workspace=workspace,
        user=user,
        role=WorkspaceMembership.Role.OWNER,
    )
    logger.info("Created workspace '%s' for user %s", workspace.name, user.username)
    return workspace


def claim_orphaned_records(user: User, workspace: Workspace) -> None:
    """Assign all workspace-less records to the given workspace.

    Called once for the first user who logs in so that data created before
    multi-tenant was introduced is not lost.
    """
    from apps.leads.models import Lead, LeadList
    from apps.scans.models import Scan

    scan_count = Scan.objects.filter(workspace__isnull=True).update(workspace=workspace)
    lead_count = Lead.objects.filter(workspace__isnull=True).update(workspace=workspace)
    list_count = LeadList.objects.filter(workspace__isnull=True).update(workspace=workspace)
    logger.info(
        "Claimed %d scans, %d leads, %d lists for workspace '%s'",
        scan_count,
        lead_count,
        list_count,
        workspace.name,
    )
