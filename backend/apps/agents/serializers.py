"""Agent config and schedule serializers."""
from rest_framework import serializers

from .models import AgentConfig, AgentSchedule


class AgentConfigSerializer(serializers.ModelSerializer):
    """Full agent config — used for GET and PATCH."""

    class Meta:
        model = AgentConfig
        fields = [
            "id",
            "service_name",
            "service_description",
            "target_industries",
            "target_biz_description",
            "default_lat",
            "default_lng",
            "default_radius_meters",
            "outreach_tone",
            "key_selling_points",
            "custom_talking_points",
            "agent_name",
            "is_configured",
            "is_paused",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_configured", "created_at", "updated_at"]

    def validate_key_selling_points(self, value):
        """Cap at 5 selling points and strip blank entries."""
        cleaned = [p.strip() for p in value if isinstance(p, str) and p.strip()]
        if len(cleaned) > 5:
            raise serializers.ValidationError("Maximum 5 selling points allowed.")
        return cleaned

    def validate_target_industries(self, value):
        """Ensure industries is a list of non-empty strings."""
        if not isinstance(value, list):
            raise serializers.ValidationError("target_industries must be a list.")
        return [i.strip() for i in value if isinstance(i, str) and i.strip()]


class AgentScheduleSerializer(serializers.ModelSerializer):
    """Serializer for AgentSchedule — used for list, create, and update."""

    class Meta:
        model = AgentSchedule
        fields = [
            "id",
            "name",
            "cron_expression",
            "scan_place_types",
            "scan_keyword",
            "scan_radius_meters",
            "is_active",
            "last_run_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_run_at", "created_at", "updated_at"]

    def validate_cron_expression(self, value: str) -> str:
        """Ensure cron has exactly 5 space-separated fields."""
        parts = value.strip().split()
        if len(parts) != 5:
            raise serializers.ValidationError(
                "cron_expression must have exactly 5 fields: minute hour day month weekday"
            )
        return " ".join(parts)

    def validate_scan_place_types(self, value):
        """Ensure at least one place type is specified."""
        if not isinstance(value, list):
            raise serializers.ValidationError("scan_place_types must be a list.")
        cleaned = [t.strip() for t in value if isinstance(t, str) and t.strip()]
        if not cleaned:
            raise serializers.ValidationError("At least one place type is required.")
        return cleaned
