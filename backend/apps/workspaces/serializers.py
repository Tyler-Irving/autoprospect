"""Workspace serializers."""
from rest_framework import serializers

from .models import Workspace, WorkspaceMembership


class WorkspaceSerializer(serializers.ModelSerializer):
    """Workspace summary for API responses."""

    member_count = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "member_count", "role", "created_at"]
        read_only_fields = ["id", "slug", "member_count", "role", "created_at"]

    def get_member_count(self, obj) -> int:
        return obj.memberships.filter(is_active=True).count()

    def get_role(self, obj) -> str | None:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user, is_active=True).first()
        return membership.role if membership else None


class WorkspaceMembershipSerializer(serializers.ModelSerializer):
    """Membership detail for team management."""

    username = serializers.CharField(source="user.username", read_only=True)
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = ["id", "username", "name", "email", "role", "joined_at", "is_active"]
        read_only_fields = ["id", "username", "name", "email", "joined_at"]

    def get_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.first_name or obj.user.username
