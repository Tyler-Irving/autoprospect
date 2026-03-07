"""Workspace models — multi-tenant isolation unit."""
from __future__ import annotations

import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Workspace(models.Model):
    """A workspace ties together a business's scans, leads, and agent config.

    Every authenticated user has exactly one workspace they own (created on
    first login). Future versions will support inviting team members to share
    a workspace.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_workspaces"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        """Auto-generate a unique slug from the workspace name on creation."""
        if not self.slug:
            base = slugify(self.name) or "workspace"
            slug = base
            n = 1
            while Workspace.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class WorkspaceMembership(models.Model):
    """Links a User to a Workspace with a role.

    Every workspace owner also has a membership record (role=owner).
    Additional members (admin, member) are added via WorkspaceInvite.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="workspace_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("workspace", "user")]
        ordering = ["joined_at"]

    def __str__(self) -> str:
        return f"{self.user.username} — {self.workspace.name} ({self.role})"


def _invite_token() -> str:
    """Generate a secure URL-safe random token for workspace invites."""
    return secrets.token_urlsafe(48)


def _invite_expiry() -> object:
    """Return a datetime 7 days from now."""
    return timezone.now() + timedelta(days=7)


class WorkspaceInvite(models.Model):
    """A pending invitation to join a workspace (v2 feature — model defined now).

    Tokens are single-use and expire after 7 days.
    """

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="invites"
    )
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True, default=_invite_token)
    role = models.CharField(
        max_length=20,
        choices=WorkspaceMembership.Role.choices,
        default=WorkspaceMembership.Role.MEMBER,
    )
    invited_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_invites"
    )
    expires_at = models.DateTimeField(default=_invite_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-expires_at"]

    def __str__(self) -> str:
        return f"Invite for {self.email} → {self.workspace.name}"

    @property
    def is_expired(self) -> bool:
        """True if this invite has passed its expiry date."""
        return timezone.now() > self.expires_at

    @property
    def is_accepted(self) -> bool:
        """True if the invite has already been accepted."""
        return self.accepted_at is not None
