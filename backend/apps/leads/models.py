"""Lead management models."""
from django.contrib.auth.models import User
from django.db import models


class LeadList(models.Model):
    """A named list for organizing leads (e.g. 'Hot Plumbers', 'Follow up Q2')."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#3B82F6")
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="lead_lists"
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lead_lists",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Lead(models.Model):
    """A business that has been promoted to an active prospect."""

    class OutreachStatus(models.TextChoices):
        NEW = "new", "New"
        RESEARCHING = "researching", "Researching"
        OUTREACH_READY = "outreach_ready", "Outreach Ready"
        CONTACTED = "contacted", "Contacted"
        FOLLOW_UP = "follow_up", "Follow Up"
        RESPONDED = "responded", "Responded"
        MEETING_BOOKED = "meeting_booked", "Meeting Booked"
        PROPOSAL_SENT = "proposal_sent", "Proposal Sent"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        NOT_INTERESTED = "not_interested", "Not Interested"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    business = models.OneToOneField(
        "businesses.Business", on_delete=models.CASCADE, related_name="lead"
    )
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="leads"
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leads",
    )
    outreach_status = models.CharField(
        max_length=20, choices=OutreachStatus.choices, default=OutreachStatus.NEW
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    tags = models.JSONField(default=list)
    lists = models.ManyToManyField(LeadList, blank=True, related_name="leads")
    notes = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    generated_email = models.TextField(blank=True)
    generated_email_subject = models.CharField(max_length=255, blank=True)
    generated_call_script = models.TextField(blank=True)
    outreach_generated_at = models.DateTimeField(null=True, blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    next_followup_at = models.DateTimeField(null=True, blank=True)
    contact_attempts = models.SmallIntegerField(default=0)
    # Approval queue fields — set when agent auto-generates outreach
    approval_required = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_leads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Lead: {self.business.name} ({self.outreach_status})"


class LeadActivity(models.Model):
    """Activity log entry for a lead."""

    class ActivityType(models.TextChoices):
        STATUS_CHANGE = "status_change", "Status Change"
        NOTE_ADDED = "note_added", "Note Added"
        EMAIL_GENERATED = "email_generated", "Email Generated"
        CALL_SCRIPT_GENERATED = "call_script_generated", "Call Script Generated"
        CONTACTED = "contacted", "Contacted"
        TAG_ADDED = "tag_added", "Tag Added"
        TIER2_REQUESTED = "tier2_requested", "Tier 2 Requested"
        EMAIL_SENT = "email_sent", "Email Sent"
        OUTREACH_APPROVED = "outreach_approved", "Outreach Approved"
        OUTREACH_REJECTED = "outreach_rejected", "Outreach Rejected"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices)
    description = models.TextField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.lead.business.name} — {self.activity_type}"
