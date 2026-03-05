"""Test settings — fast, no external calls."""
from .base import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

GOOGLE_PLACES_API_KEY = "test-key"
ANTHROPIC_API_KEY = "test-key"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
