"""Serializers for the businesses app."""
from rest_framework import serializers

from apps.enrichment.models import EnrichmentProfile
from apps.scoring.models import AutomationScore

from .models import Business


class EnrichmentInlineSerializer(serializers.ModelSerializer):
    """Minimal enrichment data for embedding in business responses."""

    class Meta:
        model = EnrichmentProfile
        fields = [
            "website_reachable",
            "website_title",
            "website_platform",
            "has_ssl",
            "is_mobile_responsive",
            "has_online_booking",
            "has_live_chat",
            "has_contact_form",
            "has_email_signup",
            "detected_crm",
            "detected_scheduling_tool",
            "detected_email_platform",
            "detected_payment_processor",
            "detected_analytics",
            "detected_technologies",
            "facebook_url",
            "instagram_url",
            "linkedin_url",
            "yelp_url",
            "negative_signals",
            "positive_signals",
        ]


class ScoreInlineSerializer(serializers.ModelSerializer):
    """Minimal score data embedded in business responses."""

    class Meta:
        model = AutomationScore
        fields = [
            "tier",
            "overall_score",
            "crm_score",
            "scheduling_score",
            "marketing_score",
            "invoicing_score",
            "key_signals",
            "summary",
            "estimated_deal_value",
            "scored_at",
        ]


class BusinessListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list and map views."""

    overall_score = serializers.ReadOnlyField()
    has_lead = serializers.ReadOnlyField()
    tier1_score = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "google_place_id",
            "name",
            "formatted_address",
            "latitude",
            "longitude",
            "place_types",
            "rating",
            "total_reviews",
            "website_url",
            "phone_number",
            "business_status",
            "overall_score",
            "has_lead",
            "tier1_score",
            "created_at",
        ]

    def get_tier1_score(self, obj) -> dict | None:
        """Return the most recent Tier 1 score if available."""
        tier1 = [s for s in obj.scores.all() if s.tier == "tier1"]
        if not tier1:
            return None
        return ScoreInlineSerializer(max(tier1, key=lambda s: s.scored_at)).data


class Tier1ScoreSummarySerializer(serializers.ModelSerializer):
    """Minimal tier-1 score data for map hover cards."""

    class Meta:
        model = AutomationScore
        fields = [
            "overall_score",
            "confidence",
            "crm_score",
            "scheduling_score",
            "marketing_score",
            "invoicing_score",
            "key_signals",
            "summary",
            "estimated_deal_value",
        ]


class MapMarkerSerializer(serializers.ModelSerializer):
    """Marker data for the map — includes enough for a rich hover card."""

    overall_score = serializers.ReadOnlyField()
    has_lead = serializers.ReadOnlyField()
    category = serializers.SerializerMethodField()
    tier1_score = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "latitude",
            "longitude",
            "overall_score",
            "category",
            "has_lead",
            "rating",
            "total_reviews",
            "phone_number",
            "website_url",
            "formatted_address",
            "business_status",
            "tier1_score",
        ]

    def get_category(self, obj) -> str:
        """Return the primary Google place type."""
        return obj.place_types[0] if obj.place_types else ""

    def get_tier1_score(self, obj) -> dict | None:
        """Return the most recent Tier 1 score if available."""
        tier1 = [s for s in obj.scores.all() if s.tier == "tier1"]
        if not tier1:
            return None
        return Tier1ScoreSummarySerializer(max(tier1, key=lambda s: s.scored_at)).data


class BusinessForLeadSerializer(serializers.ModelSerializer):
    """Business data for lead detail view — includes enrichment and tier1 score."""

    overall_score = serializers.ReadOnlyField()
    tier1_score = serializers.SerializerMethodField()
    enrichment = EnrichmentInlineSerializer(read_only=True)

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "formatted_address",
            "phone_number",
            "website_url",
            "place_types",
            "rating",
            "total_reviews",
            "google_maps_url",
            "business_status",
            "overall_score",
            "tier1_score",
            "enrichment",
        ]

    def get_tier1_score(self, obj) -> dict | None:
        tier1 = [s for s in obj.scores.all() if s.tier == "tier1"]
        if not tier1:
            return None
        return Tier1ScoreSummarySerializer(max(tier1, key=lambda s: s.scored_at)).data


class BusinessDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer including enrichment, scores, and lead status."""

    overall_score = serializers.ReadOnlyField()
    has_lead = serializers.ReadOnlyField()
    scores = ScoreInlineSerializer(many=True, read_only=True)

    class Meta:
        model = Business
        fields = "__all__"
