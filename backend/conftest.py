"""Pytest fixtures shared across all test modules."""
import pytest
from django.test import TestCase


@pytest.fixture
def scan_factory(db):
    """Factory for creating Scan instances in tests."""
    from apps.scans.models import Scan

    def _factory(**kwargs):
        defaults = {
            "center_lat": "34.0522000",
            "center_lng": "-118.2437000",
            "radius_meters": 8000,
            "place_types": ["plumber"],
            "label": "Test Scan",
        }
        defaults.update(kwargs)
        return Scan.objects.create(**defaults)

    return _factory


@pytest.fixture
def business_factory(db, scan_factory):
    """Factory for creating Business instances in tests."""
    from apps.businesses.models import Business

    def _factory(scan=None, **kwargs):
        if scan is None:
            scan = scan_factory()
        defaults = {
            "google_place_id": f"test_place_{id(kwargs)}",
            "name": "Test Plumbing Co",
            "latitude": "34.0525000",
            "longitude": "-118.2440000",
            "scan": scan,
        }
        defaults.update(kwargs)
        return Business.objects.create(**defaults)

    return _factory
