"""Tests for Places proxy endpoints (autocomplete/geocode)."""
from unittest.mock import MagicMock, patch

import httpx
import pytest
from django.test import override_settings
from rest_framework.test import APIClient


def _mock_ctx_client(mock_response):
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    return mock_client


@pytest.mark.django_db
class TestPlacesAutocomplete:
    def test_empty_query_returns_empty_predictions(self):
        resp = APIClient().get("/api/places/autocomplete/", {"input": ""})
        assert resp.status_code == 200
        assert resp.json() == {"predictions": []}

    @override_settings(GOOGLE_PLACES_API_KEY="")
    def test_missing_api_key_returns_503(self):
        resp = APIClient().get("/api/places/autocomplete/", {"input": "Chicago"})
        assert resp.status_code == 503

    def test_http_error_returns_502(self):
        with patch("apps.businesses.views.httpx.Client") as MockClient:
            client = MagicMock()
            client.__enter__.return_value = client
            client.__exit__.return_value = False
            client.post.side_effect = httpx.ConnectError("boom")
            MockClient.return_value = client
            resp = APIClient().get("/api/places/autocomplete/", {"input": "Chicago"})

        assert resp.status_code == 502
        assert resp.json()["error"] == "Autocomplete request failed."

    def test_success_transforms_suggestions_and_filters_missing_place_id(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "suggestions": [
                {
                    "placePrediction": {
                        "placeId": "abc123",
                        "text": {"text": "Chicago, IL, USA"},
                    }
                },
                {"placePrediction": {"text": {"text": "missing id"}}},
            ]
        }

        with patch("apps.businesses.views.httpx.Client", return_value=_mock_ctx_client(response)):
            resp = APIClient().get("/api/places/autocomplete/", {"input": "Chicago"})

        assert resp.status_code == 200
        assert resp.json()["predictions"] == [
            {"place_id": "abc123", "description": "Chicago, IL, USA"},
        ]

    def test_rejects_too_long_input(self):
        resp = APIClient().get("/api/places/autocomplete/", {"input": "x" * 201})
        assert resp.status_code == 400


@pytest.mark.django_db
class TestPlacesGeocode:
    def test_missing_place_id_returns_400(self):
        resp = APIClient().get("/api/places/geocode/")
        assert resp.status_code == 400

    def test_invalid_place_id_format_returns_400(self):
        resp = APIClient().get("/api/places/geocode/", {"place_id": "bad place id!"})
        assert resp.status_code == 400

    @override_settings(GOOGLE_PLACES_API_KEY="")
    def test_missing_api_key_returns_503(self):
        resp = APIClient().get("/api/places/geocode/", {"place_id": "abc123"})
        assert resp.status_code == 503

    def test_http_error_returns_502(self):
        with patch("apps.businesses.views.httpx.Client") as MockClient:
            client = MagicMock()
            client.__enter__.return_value = client
            client.__exit__.return_value = False
            client.get.side_effect = httpx.TimeoutException("timeout")
            MockClient.return_value = client
            resp = APIClient().get("/api/places/geocode/", {"place_id": "abc"})

        assert resp.status_code == 502
        assert resp.json()["error"] == "Geocode request failed."

    def test_no_results_returns_404(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"results": []}
        with patch("apps.businesses.views.httpx.Client", return_value=_mock_ctx_client(response)):
            resp = APIClient().get("/api/places/geocode/", {"place_id": "abc"})
        assert resp.status_code == 404

    def test_success_returns_rounded_lat_lng(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [{"geometry": {"location": {"lat": 41.8781136, "lng": -87.6297982}}}]
        }
        with patch("apps.businesses.views.httpx.Client", return_value=_mock_ctx_client(response)):
            resp = APIClient().get("/api/places/geocode/", {"place_id": "abc"})
        assert resp.status_code == 200
        assert resp.json() == {"lat": 41.8781136, "lng": -87.6297982}
