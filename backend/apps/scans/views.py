"""Scans API views."""
import logging
from datetime import timedelta

from django.db.models import Avg, Count, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from apps.businesses.serializers import BusinessListSerializer

from .models import Scan, SiteConfig
from .serializers import ScanSerializer
from .tasks import run_scan

logger = logging.getLogger(__name__)
ALLOWED_BUSINESS_SORTS = {"created_at", "-created_at", "name", "-name", "rating", "-rating"}


def _mask(key: str) -> str:
    """Return a masked version of an API key for safe display."""
    if not key:
        return ""
    visible = key[:6]
    return f"{visible}{'•' * min(len(key) - 6, 20)}"


@api_view(["GET", "PATCH"])
def site_settings(request):
    """Read or update application settings.

    GET  — returns config values (API keys masked, editable fields).
    PATCH — updates monthly_budget_cents and/or max_businesses_per_scan.
    """
    from django.conf import settings as django_settings

    config = SiteConfig.get()

    if request.method == "PATCH":
        data = request.data
        if "monthly_budget_cents" in data:
            try:
                config.monthly_budget_cents = max(0, int(data["monthly_budget_cents"]))
            except (TypeError, ValueError):
                return Response({"detail": "monthly_budget_cents must be an integer."}, status=400)
        if "max_businesses_per_scan" in data:
            try:
                config.max_businesses_per_scan = max(0, int(data["max_businesses_per_scan"]))
            except (TypeError, ValueError):
                return Response({"detail": "max_businesses_per_scan must be an integer."}, status=400)
        config.save()

    google_key = django_settings.GOOGLE_PLACES_API_KEY
    anthropic_key = django_settings.ANTHROPIC_API_KEY
    resend_key = django_settings.ANYMAIL.get("RESEND_API_KEY", "")

    return Response({
        # Editable config
        "monthly_budget_cents": config.effective_monthly_budget_cents,
        "max_businesses_per_scan": config.effective_max_businesses,
        # API keys — masked, read-only
        "google_places_key_set": bool(google_key),
        "google_places_key_masked": _mask(google_key),
        "anthropic_key_set": bool(anthropic_key),
        "anthropic_key_masked": _mask(anthropic_key),
        "resend_key_set": bool(resend_key),
        "resend_key_masked": _mask(resend_key),
        # Email config — read-only
        "email_from": django_settings.DEFAULT_FROM_EMAIL,
        "email_reply_to": django_settings.EMAIL_REPLY_TO,
    })


@api_view(["GET"])
def dashboard_stats(request):
    """Aggregate stats for the dashboard overview."""
    from apps.leads.models import Lead
    from apps.scoring.models import AutomationScore

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    workspace = request.workspace
    if workspace is None:
        return Response({
            "total_businesses_scanned": 0, "total_leads": 0, "leads_by_status": {},
            "avg_automation_score": None, "monthly_api_cost_cents": 0, "scans_this_month": 0,
        })

    workspace_leads = Lead.objects.filter(workspace=workspace)
    workspace_scans = Scan.objects.filter(workspace=workspace)

    total_leads = workspace_leads.count()
    leads_by_status = dict(
        workspace_leads.values_list("outreach_status").annotate(n=Count("id")).values_list("outreach_status", "n")
    )

    avg_score = AutomationScore.objects.filter(
        tier="tier1", business__scan__workspace=workspace
    ).aggregate(avg=Avg("overall_score"))["avg"]

    monthly_cost = (
        workspace_scans.filter(created_at__gte=month_start).aggregate(total=Sum("api_cost_cents"))["total"] or 0
    )
    scans_this_month = workspace_scans.filter(created_at__gte=month_start).count()
    total_businesses_scanned = workspace_scans.aggregate(total=Sum("businesses_found"))["total"] or 0

    return Response({
        "total_businesses_scanned": total_businesses_scanned,
        "total_leads": total_leads,
        "leads_by_status": leads_by_status,
        "avg_automation_score": round(float(avg_score), 1) if avg_score else None,
        "monthly_api_cost_cents": monthly_cost,
        "scans_this_month": scans_this_month,
    })


class ScanViewSet(viewsets.ModelViewSet):
    """CRUD + business listing for scans."""

    serializer_class = ScanSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        from django.db.models import Count
        workspace = self.request.workspace
        qs = Scan.objects.filter(workspace=workspace) if workspace else Scan.objects.none()
        return qs.annotate(
            lead_count=Count("businesses__lead", distinct=True)
        ).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        """Launch a new scan and enqueue the discovery task."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan = serializer.save(owner=request.user, workspace=request.workspace)

        # Enqueue the scan task
        task = run_scan.delay(scan.pk)
        scan.celery_task_id = task.id
        scan.save(update_fields=["celery_task_id"])

        logger.info("Scan %d created, task %s enqueued", scan.pk, task.id)
        return Response(ScanSerializer(scan).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Cancel running task (if any) and delete the scan."""
        scan = self.get_object()
        if scan.celery_task_id and scan.status not in (
            Scan.Status.COMPLETED,
            Scan.Status.FAILED,
        ):
            from config.celery import app as celery_app
            celery_app.control.revoke(scan.celery_task_id, terminate=True)
        scan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="businesses")
    def businesses(self, request, pk=None):
        """List businesses discovered in this scan."""
        scan = self.get_object()
        qs = scan.businesses.select_related("enrichment").prefetch_related("scores")

        min_score = request.query_params.get("min_score")
        if min_score is not None:
            try:
                # Filter businesses that have a tier1 score >= min_score
                from apps.businesses.models import Business
                scored_ids = (
                    Business.objects.filter(
                        scan=scan,
                        scores__tier="tier1",
                        scores__overall_score__gte=int(min_score),
                    )
                    .values_list("id", flat=True)
                )
                qs = qs.filter(id__in=scored_ids)
            except ValueError:
                pass

        sort = request.query_params.get("sort", "-created_at")
        if sort in ("-overall_score", "overall_score"):
            reverse = sort.startswith("-")
            businesses = sorted(qs, key=lambda b: b.overall_score or -1, reverse=reverse)
            serializer = BusinessListSerializer(businesses, many=True)
        else:
            if sort not in ALLOWED_BUSINESS_SORTS:
                sort = "-created_at"
            qs = qs.order_by(sort)
            serializer = BusinessListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="rerun")
    def rerun(self, request, pk=None):
        """Create a new scan with the same parameters as an existing one."""
        original = self.get_object()
        new_scan = Scan.objects.create(
            center_lat=original.center_lat,
            center_lng=original.center_lng,
            radius_meters=original.radius_meters,
            place_types=original.place_types,
            keyword=original.keyword,
            label=f"{original.label} (re-run)" if original.label else "",
            owner=request.user,
            workspace=request.workspace,
        )
        task = run_scan.delay(new_scan.pk)
        new_scan.celery_task_id = task.id
        new_scan.save(update_fields=["celery_task_id"])
        logger.info("Re-run scan %d → new scan %d, task %s", original.pk, new_scan.pk, task.id)
        return Response(ScanSerializer(new_scan).data, status=status.HTTP_201_CREATED)
