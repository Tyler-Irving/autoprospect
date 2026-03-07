"""Agent configuration and scheduling models for workspace AI prospecting."""
from django.db import models


class AgentConfig(models.Model):
    """Configuration for a workspace's AI prospecting agent.

    Collected during onboarding. Injected into all Claude prompts so the AI
    generates scoring and outreach personalized to the workspace's service.
    """

    class OutreachTone(models.TextChoices):
        FORMAL = "formal", "Formal & Professional"
        SEMI_FORMAL = "semi_formal", "Friendly & Professional"
        CASUAL = "casual", "Casual & Conversational"

    workspace = models.OneToOneField(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="agent_config",
    )

    # What the workspace owner sells
    service_name = models.CharField(max_length=255, blank=True)
    service_description = models.TextField(blank=True)

    # Ideal customer profile
    target_industries = models.JSONField(default=list)
    target_biz_description = models.TextField(blank=True)

    # Default scan geography (optional — lets scheduled scans know where to look)
    default_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    default_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    default_radius_meters = models.PositiveIntegerField(default=5000)

    # Outreach preferences
    outreach_tone = models.CharField(
        max_length=20, choices=OutreachTone.choices, default=OutreachTone.SEMI_FORMAL
    )
    key_selling_points = models.JSONField(default=list)
    custom_talking_points = models.TextField(blank=True)

    # Optional persona name for outreach ("Hi, I'm Alex from...")
    agent_name = models.CharField(max_length=100, blank=True)

    # Lifecycle flags
    is_configured = models.BooleanField(default=False)
    is_paused = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agent Config"

    def __str__(self) -> str:
        return f"{self.workspace.name} — {self.service_name or 'unconfigured'}"


class AgentSchedule(models.Model):
    """A recurring scan schedule for a workspace's AI prospecting agent.

    Each active schedule with a cron_expression is mirrored as a
    django-celery-beat PeriodicTask so Celery Beat fires it automatically.
    """

    # Simple presets expressed as standard 5-field cron strings
    CRON_PRESETS = {
        "daily_9am": "0 9 * * *",
        "weekdays_9am": "0 9 * * 1-5",
        "mon_wed_fri": "0 9 * * 1,3,5",
        "weekly_monday": "0 9 * * 1",
    }

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    name = models.CharField(max_length=100)
    cron_expression = models.CharField(
        max_length=100,
        help_text="Standard 5-field cron: 'min hour day month weekday'",
    )
    scan_place_types = models.JSONField(
        default=list,
        help_text="List of Google Places type strings to search for.",
    )
    scan_keyword = models.CharField(max_length=255, blank=True)
    scan_radius_meters = models.PositiveIntegerField(default=5000)
    is_active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    celery_task_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of the linked django-celery-beat PeriodicTask.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Agent Schedule"

    def __str__(self) -> str:
        return f"{self.workspace.name} — {self.name}"
