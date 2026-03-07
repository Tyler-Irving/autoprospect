"""Serializers for the leads app."""
from rest_framework import serializers

from apps.businesses.serializers import BusinessForLeadSerializer, BusinessListSerializer

from .models import Lead, LeadActivity, LeadList


class LeadListSerializer(serializers.ModelSerializer):
    """Serializer for LeadList (the list-of-leads container)."""

    lead_count = serializers.SerializerMethodField()

    class Meta:
        model = LeadList
        fields = ["id", "name", "description", "color", "lead_count", "created_at"]
        read_only_fields = ["id", "lead_count", "created_at"]

    def get_lead_count(self, obj) -> int:
        # Use the prefetch cache when available to avoid an extra COUNT query.
        prefetch_cache = getattr(obj, "_prefetched_objects_cache", {})
        if "leads" in prefetch_cache:
            return len(prefetch_cache["leads"])
        return obj.leads.count()


class LeadActivitySerializer(serializers.ModelSerializer):
    """Serializer for activity log entries."""

    class Meta:
        model = LeadActivity
        fields = ["id", "activity_type", "description", "metadata", "created_at"]
        read_only_fields = ["id", "created_at"]


class LeadSerializer(serializers.ModelSerializer):
    """Lead list serializer — minimal data for table views."""

    business = BusinessListSerializer(read_only=True)
    business_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Lead
        fields = [
            "id",
            "business",
            "business_id",
            "outreach_status",
            "priority",
            "tags",
            "notes",
            "contact_email",
            "last_contacted_at",
            "next_followup_at",
            "contact_attempts",
            "approval_required",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "approval_required", "approved_at", "created_at", "updated_at"]

    def create(self, validated_data):
        from apps.businesses.models import Business
        from rest_framework import serializers as drf_serializers
        try:
            business = Business.objects.get(pk=validated_data.pop("business_id"))
        except Business.DoesNotExist:
            raise drf_serializers.ValidationError({"business_id": "Business not found."})
        lead = Lead.objects.create(business=business, **validated_data)
        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.STATUS_CHANGE,
            description=f"Lead created with status '{lead.outreach_status}'",
        )
        return lead


class LeadDetailSerializer(LeadSerializer):
    """Full lead detail including generated outreach content and enrichment."""

    business = BusinessForLeadSerializer(read_only=True)
    activities = LeadActivitySerializer(many=True, read_only=True)

    class Meta(LeadSerializer.Meta):
        fields = LeadSerializer.Meta.fields + [
            "generated_email",
            "generated_email_subject",
            "generated_call_script",
            "outreach_generated_at",
            "lists",
            "activities",
        ]
