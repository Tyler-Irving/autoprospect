"""Businesses API views."""
import logging
import re

import httpx
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Business
from .serializers import BusinessDetailSerializer, BusinessListSerializer, MapMarkerSerializer

logger = logging.getLogger(__name__)

PLACES_AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
MAX_AUTOCOMPLETE_INPUT = 200
_PLACE_ID_RE = re.compile(r"^[A-Za-z0-9_\-:.+/=]{3,255}$")


@api_view(["GET"])
@permission_classes([AllowAny])
def places_autocomplete(request):
    """Proxy Google Places autocomplete so the API key stays server-side.

    Query params:
        input: partial city/address string (required)
    """
    query = request.query_params.get("input", "").strip()
    if not query:
        return Response({"predictions": []})
    if len(query) > MAX_AUTOCOMPLETE_INPUT:
        return Response({"error": "input is too long."}, status=400)

    api_key = settings.GOOGLE_PLACES_API_KEY
    if not api_key:
        return Response({"error": "Google API key not configured."}, status=503)

    try:
        with httpx.Client(timeout=5) as client:
            resp = client.post(
                PLACES_AUTOCOMPLETE_URL,
                json={
                    "input": query,
                    "includedPrimaryTypes": ["locality", "sublocality", "administrative_area_level_3"],
                    "includedRegionCodes": ["us"],
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("Google autocomplete error: %s", exc)
        return Response({"error": "Autocomplete request failed."}, status=502)

    suggestions = [
        {
            "place_id": s.get("placePrediction", {}).get("placeId", ""),
            "description": s.get("placePrediction", {}).get("text", {}).get("text", ""),
        }
        for s in data.get("suggestions", [])
        if s.get("placePrediction", {}).get("placeId")
    ]
    return Response({"predictions": suggestions})


@api_view(["GET"])
@permission_classes([AllowAny])
def places_geocode(request):
    """Return lat/lng for a Google place_id.

    Query params:
        place_id: Google place ID (required)
    """
    place_id = request.query_params.get("place_id", "").strip()
    if not place_id:
        return Response({"error": "place_id is required."}, status=400)
    if not _PLACE_ID_RE.fullmatch(place_id):
        return Response({"error": "place_id format is invalid."}, status=400)

    api_key = settings.GOOGLE_PLACES_API_KEY
    if not api_key:
        return Response({"error": "Google API key not configured."}, status=503)

    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(
                GEOCODE_URL,
                params={"place_id": place_id, "key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("Google geocode error: %s", exc)
        return Response({"error": "Geocode request failed."}, status=502)

    results = data.get("results", [])
    if not results:
        return Response({"error": "No results found."}, status=404)

    loc = results[0]["geometry"]["location"]
    return Response({"lat": round(loc["lat"], 7), "lng": round(loc["lng"], 7)})


class BusinessViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only CRUD for businesses + map data endpoint."""

    queryset = Business.objects.select_related("enrichment", "lead", "scan").prefetch_related("scores")
    serializer_class = BusinessListSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BusinessDetailSerializer
        return BusinessListSerializer

    def get_queryset(self):
        workspace = self.request.workspace
        if workspace is None:
            return super().get_queryset().none()
        qs = super().get_queryset().filter(scan__workspace=workspace)
        params = self.request.query_params

        scan_id = params.get("scan")
        if scan_id:
            qs = qs.filter(scan_id=scan_id)

        place_types = params.get("place_types")
        if place_types:
            qs = qs.filter(place_types__contains=[place_types])

        min_score = params.get("min_score")
        if min_score:
            try:
                qs = qs.filter(
                    scores__tier="tier1",
                    scores__overall_score__gte=int(min_score),
                ).distinct()
            except ValueError:
                pass

        return qs

    @action(detail=False, methods=["get"], url_path="map-data")
    def map_data(self, request):
        """Return lightweight marker data for map rendering."""
        qs = self.get_queryset()
        serializer = MapMarkerSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="promote")
    def promote(self, request, pk=None):
        """Promote a business to an active lead."""
        from apps.leads.models import Lead, LeadActivity

        from apps.scoring.tasks import score_business_tier2

        business = self.get_object()
        if hasattr(business, "lead"):
            return Response({"lead_id": business.lead.id, "already_lead": True})

        lead = Lead.objects.create(
            business=business,
            owner=request.user,
            workspace=request.workspace,
        )

        # Auto-populate contact email from enrichment crawl if available
        enrichment = getattr(business, "enrichment", None)
        if enrichment and enrichment.contact_email:
            lead.contact_email = enrichment.contact_email
            lead.save(update_fields=["contact_email"])

        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.STATUS_CHANGE,
            description="Promoted to lead from map",
        )

        # Mark tier2 as pending and queue the background task
        business.tier2_pending = True
        business.save(update_fields=["tier2_pending"])
        score_business_tier2.delay(business.pk)

        return Response({"lead_id": lead.id, "already_lead": False}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="enrich-tier2")
    def enrich_tier2(self, request, pk=None):
        """Trigger Tier 2 deep analysis scoring for a business (manual action).

        The business must already be promoted to a lead before Tier 2 can run.
        Runs synchronously — may take several seconds due to Claude API call.

        Returns:
            Serialized Tier2ScoreSummarySerializer data on success.
            400 if the business has no associated lead.
            500 if the Claude scoring call fails.
        """
        from django.db.models import F

        from apps.leads.models import LeadActivity
        from apps.scans.models import Scan
        from apps.scoring.services.tier2_scorer import Tier2Scorer

        from .serializers import Tier2ScoreSummarySerializer

        business = self.get_object()

        if not hasattr(business, "lead"):
            return Response(
                {"detail": "Business must be promoted to a lead before running deep analysis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            score = Tier2Scorer().score(business)
        except Exception as exc:
            logger.error(
                "Tier 2 scoring failed for business %d (%s): %s",
                business.pk,
                business.name,
                exc,
            )
            return Response(
                {"detail": f"Tier 2 scoring failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Accumulate API cost on the parent scan using an atomic F() update
        Scan.objects.filter(pk=business.scan_id).update(
            api_cost_cents=F("api_cost_cents") + score.api_cost_cents
        )

        LeadActivity.objects.create(
            lead=business.lead,
            activity_type=LeadActivity.ActivityType.TIER2_REQUESTED,
            description=f"Deep analysis completed — score {score.overall_score}/100",
        )

        return Response(Tier2ScoreSummarySerializer(score).data)
