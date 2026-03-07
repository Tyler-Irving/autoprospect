"""Scan model — represents a single area prospecting job."""
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class Scan(models.Model):
    """A single area scan that discovers and enriches local businesses."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DISCOVERING = "discovering", "Discovering"
        ENRICHING_T1 = "enriching_t1", "Enriching (T1)"
        SCORING_T1 = "scoring_t1", "Scoring (T1)"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    center_lat = models.DecimalField(max_digits=10, decimal_places=7)
    center_lng = models.DecimalField(max_digits=10, decimal_places=7)
    radius_meters = models.PositiveIntegerField()
    place_types = models.JSONField(default=list)
    keyword = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    celery_task_id = models.CharField(max_length=255, blank=True)
    businesses_found = models.PositiveIntegerField(default=0)
    businesses_enriched = models.PositiveIntegerField(default=0)
    businesses_scored = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    label = models.CharField(max_length=255, blank=True)
    api_cost_cents = models.PositiveIntegerField(default=0)
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="scans"
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scans",
    )
    trigger_type = models.CharField(max_length=20, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.label or f"Scan #{self.pk} ({self.status})"

    @property
    def progress_pct(self) -> int:
        """Compute overall progress percentage based on current status."""
        status_progress = {
            self.Status.PENDING: 0,
            self.Status.DISCOVERING: 15,
            self.Status.ENRICHING_T1: 40,
            self.Status.SCORING_T1: 70,
            self.Status.COMPLETED: 100,
            self.Status.FAILED: 0,
        }
        base = status_progress.get(self.status, 0)
        if self.status == self.Status.ENRICHING_T1 and self.businesses_found > 0:
            pct = self.businesses_enriched / self.businesses_found
            return int(base + pct * 30)
        if self.status == self.Status.SCORING_T1 and self.businesses_found > 0:
            pct = self.businesses_scored / self.businesses_found
            return int(base + pct * 30)
        return base


class SiteConfig(models.Model):
    """Singleton model for user-editable application settings.

    Always access via SiteConfig.get() — never create more than one row.
    """

    monthly_budget_cents = models.PositiveIntegerField(
        default=0,
        help_text="Monthly Claude API budget in cents (0 = use env default).",
    )
    max_businesses_per_scan = models.PositiveIntegerField(
        default=0,
        help_text="Max businesses per scan (0 = use env default).",
    )

    class Meta:
        verbose_name = "Site Config"

    def __str__(self) -> str:
        return "Site Configuration"

    @classmethod
    def get(cls) -> "SiteConfig":
        """Return the singleton config row, creating it if it doesn't exist."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def effective_monthly_budget_cents(self) -> int:
        """Return the active budget, falling back to the env value."""
        return self.monthly_budget_cents or settings.MONTHLY_API_BUDGET_CENTS

    @property
    def effective_max_businesses(self) -> int:
        """Return the active max businesses, falling back to the env value."""
        return self.max_businesses_per_scan or settings.MAX_BUSINESSES_PER_SCAN
