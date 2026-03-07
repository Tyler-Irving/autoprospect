"""Leads API views."""
from django.db import connection
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Lead, LeadActivity, LeadList
from .serializers import LeadActivitySerializer, LeadDetailSerializer, LeadListSerializer, LeadSerializer


class LeadViewSet(viewsets.ModelViewSet):
    """CRUD + outreach generation for leads."""

    queryset = Lead.objects.select_related(
        "business", "business__enrichment", "business__scan"
    ).prefetch_related("business__scores", "activities", "lists")
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return LeadDetailSerializer
        return LeadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        outreach_status = params.get("status")
        if outreach_status:
            qs = qs.filter(outreach_status=outreach_status)

        tags = params.get("tags")
        if tags:
            if connection.vendor == "sqlite":
                # SQLite lacks JSON contains lookup support; fallback for test/dev parity.
                ids = [lead.pk for lead in qs if tags in (lead.tags or [])]
                qs = qs.filter(pk__in=ids)
            else:
                qs = qs.filter(tags__contains=[tags])

        list_id = params.get("list")
        if list_id:
            qs = qs.filter(lists__id=list_id)

        min_score = params.get("min_score")
        if min_score:
            try:
                qs = qs.filter(
                    business__scores__tier="tier1",
                    business__scores__overall_score__gte=int(min_score),
                )
            except ValueError:
                pass

        sort = params.get("sort", "-created_at")
        allowed_sorts = {"created_at", "-created_at", "outreach_status", "-outreach_status", "priority", "-priority"}
        if sort in allowed_sorts:
            qs = qs.order_by(sort)

        return qs.distinct()

    def update(self, request, *args, **kwargs):
        """PATCH a lead and log activity for status changes."""
        lead = self.get_object()
        old_status = lead.outreach_status
        response = super().update(request, *args, **kwargs)
        lead.refresh_from_db()

        if lead.outreach_status != old_status:
            LeadActivity.objects.create(
                lead=lead,
                activity_type=LeadActivity.ActivityType.STATUS_CHANGE,
                description=f"Status changed from '{old_status}' to '{lead.outreach_status}'",
                metadata={"old_status": old_status, "new_status": lead.outreach_status},
            )
        return response

    @action(detail=True, methods=["post"], url_path="generate-outreach")
    def generate_outreach(self, request, pk=None):
        """Generate outreach (email + call script) for this lead synchronously."""
        lead = self.get_object()
        try:
            from apps.leads.tasks import run_outreach_generation
            run_outreach_generation(lead.id)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        lead.refresh_from_db()
        serializer = LeadDetailSerializer(lead)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="send-email")
    def send_email(self, request, pk=None):
        """Send the generated cold email for this lead via Resend."""
        lead = self.get_object()
        try:
            from apps.leads.services.email_sender import send_lead_email
            send_lead_email(lead)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        lead.refresh_from_db()
        serializer = LeadDetailSerializer(lead)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="activities")
    def activities(self, request, pk=None):
        lead = self.get_object()
        activities = lead.activities.all()
        serializer = LeadActivitySerializer(activities, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="bulk-action")
    def bulk_action(self, request):
        """Apply a bulk action to multiple leads."""
        lead_ids = request.data.get("lead_ids", [])
        action_name = request.data.get("action")
        value = request.data.get("value")

        if not lead_ids or not action_name:
            return Response({"detail": "lead_ids and action required."}, status=400)

        leads = Lead.objects.filter(id__in=lead_ids)

        if action_name == "update_status":
            valid_statuses = {c[0] for c in Lead.OutreachStatus.choices}
            if value not in valid_statuses:
                return Response({"detail": f"Invalid status '{value}'."}, status=400)
            updated = leads.update(outreach_status=value)
        elif action_name == "update_priority":
            valid_priorities = {c[0] for c in Lead.Priority.choices}
            if value not in valid_priorities:
                return Response({"detail": f"Invalid priority '{value}'."}, status=400)
            updated = leads.update(priority=value)
        elif action_name == "add_tag":
            updated = 0
            for lead in leads:
                if value not in lead.tags:
                    lead.tags.append(value)
                    lead.save(update_fields=["tags"])
                updated += 1
        elif action_name == "add_to_list":
            try:
                lead_list = LeadList.objects.get(pk=value)
                updated = 0
                for lead in leads:
                    lead.lists.add(lead_list)
                    updated += 1
            except LeadList.DoesNotExist:
                return Response({"detail": "List not found."}, status=404)
        else:
            return Response({"detail": f"Unknown action: {action_name}"}, status=400)

        return Response({"updated": updated})


class LeadListViewSet(viewsets.ModelViewSet):
    """CRUD for lead lists (named collections of leads)."""

    queryset = LeadList.objects.prefetch_related("leads")
    serializer_class = LeadListSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    @action(detail=True, methods=["post"], url_path="add-leads")
    def add_leads(self, request, pk=None):
        lead_list = self.get_object()
        lead_ids = request.data.get("lead_ids", [])
        leads = Lead.objects.filter(id__in=lead_ids)
        lead_list.leads.add(*leads)
        return Response({"added": leads.count()})
