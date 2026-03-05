"""Business model — a local business discovered via Google Places."""
from django.db import models


class Business(models.Model):
    """A local business discovered via Google Places API."""

    google_place_id = models.CharField(max_length=512, unique=True, db_index=True)
    google_maps_url = models.URLField(max_length=1024, blank=True)
    name = models.CharField(max_length=512)
    formatted_address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    website_url = models.URLField(max_length=1024, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    place_types = models.JSONField(default=list)
    business_status = models.CharField(max_length=50, blank=True)
    price_level = models.SmallIntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    total_reviews = models.PositiveIntegerField(default=0)
    opening_hours = models.JSONField(default=dict)
    reviews_data = models.JSONField(default=list)
    scan = models.ForeignKey("scans.Scan", on_delete=models.CASCADE, related_name="businesses")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def overall_score(self) -> int | None:
        """Return the most recent Tier 1 score, if any."""
        score = self.scores.filter(tier="tier1").order_by("-scored_at").first()
        return score.overall_score if score else None

    @property
    def has_lead(self) -> bool:
        """Return True if this business has been promoted to a lead."""
        return hasattr(self, "lead")
