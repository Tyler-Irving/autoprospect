"""Tests for Scans API endpoints."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.scans.models import Scan


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestScanAPI:
    def test_list_scans_empty(self, api_client):
        response = api_client.get('/api/scans/')
        assert response.status_code == 200

    def test_create_scan_enqueues_task(self, api_client):
        with patch('apps.scans.views.run_scan') as mock_task:
            mock_task.delay.return_value.id = 'fake-task-id'
            response = api_client.post('/api/scans/', {
                'center_lat': '34.0522',
                'center_lng': '-118.2437',
                'radius_meters': 8000,
                'place_types': ['plumber'],
                'label': 'Test Scan',
            }, format='json')

        assert response.status_code == 201
        data = response.json()
        assert data['label'] == 'Test Scan'
        assert data['status'] == 'pending'
        mock_task.delay.assert_called_once()

    def test_get_scan_detail(self, api_client, scan_factory):
        scan = scan_factory()
        response = api_client.get(f'/api/scans/{scan.pk}/')
        assert response.status_code == 200
        data = response.json()
        assert 'progress_pct' in data
        assert data['id'] == scan.pk

    def test_delete_scan(self, api_client, scan_factory):
        scan = scan_factory(status=Scan.Status.COMPLETED)
        response = api_client.delete(f'/api/scans/{scan.pk}/')
        assert response.status_code == 204
        assert not Scan.objects.filter(pk=scan.pk).exists()

    def test_scan_businesses_endpoint(self, api_client, scan_factory, business_factory):
        scan = scan_factory()
        business_factory(scan=scan)
        business_factory(scan=scan)

        response = api_client.get(f'/api/scans/{scan.pk}/businesses/')
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_rediscovered_business_reassigned_to_new_scan(self, scan_factory, business_factory):
        """A business found in scan1 and re-discovered in scan2 should appear in scan2's results."""
        from apps.scans.tasks import _upsert_business
        from apps.businesses.services.google_places import GooglePlacesService

        scan1 = scan_factory()
        scan2 = scan_factory()

        raw = {
            'id': 'places/ChIJtest123',
            'displayName': {'text': 'Joe Plumbing'},
            'formattedAddress': '123 Main St',
            'location': {'latitude': 34.05, 'longitude': -118.24},
            'types': ['plumber'],
            'businessStatus': 'OPERATIONAL',
            'rating': 4.5,
            'userRatingCount': 10,
        }
        data = GooglePlacesService.parse_place(raw)

        _upsert_business(scan1, data)
        _upsert_business(scan2, data)

        from apps.businesses.models import Business
        biz = Business.objects.get(google_place_id='places/ChIJtest123')
        assert biz.scan_id == scan2.pk
