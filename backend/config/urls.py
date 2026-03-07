"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.common.urls")),
    path("api/", include("apps.workspaces.urls")),
    path("api/", include("apps.agents.urls")),
    path("api/", include("apps.scans.urls")),
    path("api/", include("apps.businesses.urls")),
    path("api/", include("apps.leads.urls")),
]
