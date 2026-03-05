"""URL routing for the leads app."""
from rest_framework.routers import DefaultRouter

from .views import LeadListViewSet, LeadViewSet

router = DefaultRouter()
router.register(r"leads", LeadViewSet, basename="lead")
router.register(r"lead-lists", LeadListViewSet, basename="lead-list")

urlpatterns = router.urls
