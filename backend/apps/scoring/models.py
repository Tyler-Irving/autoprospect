"""AutomationScore model — Claude AI score for a business."""
from django.db import models


class AutomationScore(models.Model):
    """AI-generated automation readiness score for a business."""

    class Tier(models.TextChoices):
        TIER1 = "tier1", "Tier 1 (Quick)"
        TIER2 = "tier2", "Tier 2 (Full)"

    class DealValue(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        ENTERPRISE = "enterprise", "Enterprise"

    business = models.ForeignKey(
        "businesses.Business", on_delete=models.CASCADE, related_name="scores"
    )
    tier = models.CharField(max_length=10, choices=Tier.choices)
    overall_score = models.SmallIntegerField()
    confidence = models.DecimalField(max_digits=3, decimal_places=2)
    crm_score = models.SmallIntegerField()
    scheduling_score = models.SmallIntegerField()
    marketing_score = models.SmallIntegerField()
    invoicing_score = models.SmallIntegerField()
    key_signals = models.JSONField(default=list)
    summary = models.TextField()
    recommended_pitch_angle = models.TextField(blank=True)
    estimated_deal_value = models.CharField(
        max_length=20, choices=DealValue.choices, blank=True
    )
    full_dossier = models.TextField(blank=True)
    competitor_analysis = models.TextField(blank=True)
    model_used = models.CharField(max_length=100)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    api_cost_cents = models.PositiveIntegerField(default=0)
    scored_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-overall_score"]
        indexes = [
            models.Index(fields=["-overall_score"]),
            models.Index(fields=["tier"]),
        ]

    def __str__(self) -> str:
        return f"{self.business.name} — {self.tier} score: {self.overall_score}"
