"""Tests for Businesses API endpoints."""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestBusinessAPI:
    def test_list_businesses(self, api_client, business_factory):
        business_factory()
        business_factory()
        response = api_client.get('/api/businesses/')
        assert response.status_code == 200
        assert len(response.json()) >= 2

    def test_get_business_detail(self, api_client, business_factory):
        biz = business_factory(name='Joe Plumbing')
        response = api_client.get(f'/api/businesses/{biz.pk}/')
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Joe Plumbing'
        assert 'overall_score' in data
        assert 'has_lead' in data

    def test_map_data_returns_markers(self, api_client, scan_factory, business_factory):
        scan = scan_factory()
        business_factory(scan=scan)
        business_factory(scan=scan)
        response = api_client.get('/api/businesses/map-data/', {'scan': scan.pk})
        assert response.status_code == 200
        markers = response.json()
        assert len(markers) == 2
        for m in markers:
            assert 'id' in m
            assert 'latitude' in m
            assert 'longitude' in m
            assert 'name' in m

    def test_map_data_filter_by_scan(self, api_client, scan_factory, business_factory):
        scan1 = scan_factory()
        scan2 = scan_factory()
        business_factory(scan=scan1)
        business_factory(scan=scan2)

        response = api_client.get('/api/businesses/map-data/', {'scan': scan1.pk})
        assert response.status_code == 200
        assert len(response.json()) == 1
