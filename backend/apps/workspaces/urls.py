from django.urls import path

from .views import workspace_detail

urlpatterns = [
    path("workspace/", workspace_detail),
]
