"""URL routing for the businesses app."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BusinessViewSet, places_autocomplete, places_geocode

router = DefaultRouter()
router.register(r"businesses", BusinessViewSet, basename="business")

urlpatterns = router.urls + [
    path("places/autocomplete/", places_autocomplete, name="places-autocomplete"),
    path("places/geocode/", places_geocode, name="places-geocode"),
]
