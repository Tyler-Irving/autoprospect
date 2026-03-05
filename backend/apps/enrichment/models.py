"""EnrichmentProfile model — website crawl and tech stack data for a business."""
from django.db import models


class EnrichmentProfile(models.Model):
    """Enrichment data collected by crawling a business's website."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    business = models.OneToOneField(
        "businesses.Business", on_delete=models.CASCADE, related_name="enrichment"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Website basics
    website_reachable = models.BooleanField(null=True, blank=True)
    website_title = models.CharField(max_length=512, blank=True)
    website_description = models.TextField(blank=True)
    website_text_content = models.TextField(blank=True)
    website_load_time_ms = models.PositiveIntegerField(null=True, blank=True)
    has_ssl = models.BooleanField(null=True, blank=True)
    is_mobile_responsive = models.BooleanField(null=True, blank=True)
    website_platform = models.CharField(max_length=100, blank=True)
    detected_technologies = models.JSONField(default=list)

    # Capabilities
    has_online_booking = models.BooleanField(null=True, blank=True)
    has_live_chat = models.BooleanField(null=True, blank=True)
    has_contact_form = models.BooleanField(null=True, blank=True)
    has_email_signup = models.BooleanField(null=True, blank=True)

    # Detected tools
    detected_crm = models.CharField(max_length=200, blank=True)
    detected_scheduling_tool = models.CharField(max_length=200, blank=True)
    detected_email_platform = models.CharField(max_length=200, blank=True)
    detected_payment_processor = models.CharField(max_length=200, blank=True)
    detected_analytics = models.JSONField(default=list)

    # Social
    social_links = models.JSONField(default=dict)
    facebook_url = models.URLField(max_length=1024, blank=True)
    instagram_url = models.URLField(max_length=1024, blank=True)
    linkedin_url = models.URLField(max_length=1024, blank=True)
    yelp_url = models.URLField(max_length=1024, blank=True)

    # Review signals
    review_summary = models.TextField(blank=True)
    negative_signals = models.JSONField(default=list)
    positive_signals = models.JSONField(default=list)

    enriched_at = models.DateTimeField(null=True, blank=True)
    error_log = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"Enrichment for {self.business.name}"
