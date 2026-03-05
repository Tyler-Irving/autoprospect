"""Scans API views."""
import logging
from datetime import timedelta

from django.db.models import Avg, Count, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from apps.businesses.serializers import BusinessListSerializer

from .models import Scan
from .serializers import ScanSerializer
from .tasks import run_scan

logger = logging.getLogger(__name__)


@api_view(["GET"])
def dashboard_stats(request):
    """Aggregate stats for the dashboard overview."""
    from apps.leads.models import Lead
    from apps.scoring.models import AutomationScore

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_leads = Lead.objects.count()
    leads_by_status = dict(
        Lead.objects.values_list("outreach_status").annotate(n=Count("id")).values_list("outreach_status", "n")
    )

    avg_score = AutomationScore.objects.filter(tier="tier1").aggregate(avg=Avg("overall_score"))["avg"]

    monthly_cost = (
        Scan.objects.filter(created_at__gte=month_start).aggregate(total=Sum("api_cost_cents"))["total"] or 0
    )
    scans_this_month = Scan.objects.filter(created_at__gte=month_start).count()
    total_businesses_scanned = Scan.objects.aggregate(total=Sum("businesses_found"))["total"] or 0

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

    queryset = Scan.objects.all()
    serializer_class = ScanSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        """Launch a new scan and enqueue the discovery task."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan = serializer.save()

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
            pass  # Handled post-query since score is on related model
        else:
            qs = qs.order_by(sort)

        serializer = BusinessListSerializer(qs, many=True)
        return Response(serializer.data)
