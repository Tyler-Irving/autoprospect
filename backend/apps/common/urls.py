"""Auth URL routes."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import github_login, me

urlpatterns = [
    path("auth/github/", github_login, name="auth-github"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me/", me, name="auth-me"),
]
