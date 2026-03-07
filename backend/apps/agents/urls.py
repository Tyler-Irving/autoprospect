from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AgentScheduleViewSet, agent_config, complete_onboarding, toggle_pause

router = DefaultRouter()
router.register("agent/schedules", AgentScheduleViewSet, basename="agent-schedule")

urlpatterns = [
    path("agent/config/", agent_config),
    path("agent/onboarding/complete/", complete_onboarding),
    path("agent/config/pause/", toggle_pause),
    path("", include(router.urls)),
]
