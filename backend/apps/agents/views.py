"""Agent config and schedule API views."""
import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import AgentSchedule
from .serializers import AgentConfigSerializer, AgentScheduleSerializer
from .services import get_or_create_agent_config

logger = logging.getLogger(__name__)


@api_view(["GET", "PATCH"])
def agent_config(request):
    """Get or update the current workspace's agent configuration.

    GET  — returns the full agent config (creates default if none exists).
    PATCH — partial update; any subset of fields may be sent.
    """
    workspace = request.workspace
    if workspace is None:
        return Response({"detail": "No workspace found."}, status=404)

    config = get_or_create_agent_config(workspace)

    if request.method == "PATCH":
        serializer = AgentConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    return Response(AgentConfigSerializer(config).data)


@api_view(["POST"])
def complete_onboarding(request):
    """Mark the agent configuration as complete (onboarding finished).

    Sets is_configured=True. After this call the frontend redirects to /.
    """
    workspace = request.workspace
    if workspace is None:
        return Response({"detail": "No workspace found."}, status=404)

    config = get_or_create_agent_config(workspace)

    if not config.service_name:
        return Response(
            {"detail": "service_name is required before completing onboarding."},
            status=400,
        )

    config.is_configured = True
    config.save(update_fields=["is_configured", "updated_at"])
    logger.info("Onboarding completed for workspace '%s'", workspace.name)
    return Response(AgentConfigSerializer(config).data)


@api_view(["POST"])
def toggle_pause(request):
    """Toggle the agent's is_paused flag.

    Body: {"is_paused": true|false}
    """
    workspace = request.workspace
    if workspace is None:
        return Response({"detail": "No workspace found."}, status=404)

    config = get_or_create_agent_config(workspace)
    is_paused = request.data.get("is_paused")
    if is_paused is None:
        return Response({"detail": "is_paused is required."}, status=400)

    config.is_paused = bool(is_paused)
    config.save(update_fields=["is_paused", "updated_at"])
    return Response(AgentConfigSerializer(config).data)


class AgentScheduleViewSet(viewsets.ModelViewSet):
    """CRUD for workspace agent schedules.

    Schedules are workspace-scoped. Each saved schedule with a cron_expression
    is automatically mirrored to a django-celery-beat PeriodicTask via signal.
    """

    serializer_class = AgentScheduleSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        workspace = self.request.workspace
        if workspace is None:
            return AgentSchedule.objects.none()
        return AgentSchedule.objects.filter(workspace=workspace)

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)

    @action(detail=True, methods=["post"], url_path="run-now")
    def run_now(self, request, pk=None):
        """Manually trigger a scheduled scan outside of its cron schedule."""
        schedule = self.get_object()

        config = None
        try:
            config = schedule.workspace.agent_config
        except AttributeError:
            pass

        if config and config.is_paused:
            return Response(
                {"detail": "Agent is paused. Resume the agent before running a scan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not config or not config.default_lat or not config.default_lng:
            return Response(
                {"detail": "No default location set in agent config. Add a default lat/lng first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.agents.tasks import run_scheduled_scan
        run_scheduled_scan.delay(schedule.pk)

        return Response({"queued": True, "schedule_id": schedule.pk})
