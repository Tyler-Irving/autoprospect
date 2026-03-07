"""URL routing for the scans app."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ScanViewSet, dashboard_stats, site_settings

router = DefaultRouter()
router.register(r"scans", ScanViewSet, basename="scan")

urlpatterns = router.urls + [
    path("dashboard/stats/", dashboard_stats, name="dashboard-stats"),
    path("settings/", site_settings, name="site-settings"),
]
