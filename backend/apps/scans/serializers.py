"""Serializers for the scans app."""
from rest_framework import serializers

from .models import Scan


class ScanSerializer(serializers.ModelSerializer):
    """Full scan serializer with computed progress."""

    progress_pct = serializers.ReadOnlyField()
    lead_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Scan
        fields = [
            "id",
            "label",
            "center_lat",
            "center_lng",
            "radius_meters",
            "place_types",
            "keyword",
            "status",
            "celery_task_id",
            "businesses_found",
            "businesses_enriched",
            "businesses_scored",
            "error_message",
            "api_cost_cents",
            "progress_pct",
            "lead_count",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "celery_task_id",
            "businesses_found",
            "businesses_enriched",
            "businesses_scored",
            "error_message",
            "api_cost_cents",
            "progress_pct",
            "lead_count",
            "created_at",
            "updated_at",
            "completed_at",
        ]
