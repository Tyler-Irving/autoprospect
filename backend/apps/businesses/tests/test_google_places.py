"""Tests for GooglePlacesService.parse_place."""
import pytest
from apps.businesses.services.google_places import GooglePlacesService


class TestParsePlaces:
    def _raw_place(self, **overrides):
        base = {
            'id': 'places/ChIJ12345',
            'displayName': {'text': 'Joe Plumbing'},
            'formattedAddress': '123 Main St, LA, CA 90001',
            'location': {'latitude': 34.0525, 'longitude': -118.244},
            'types': ['plumber'],
            'businessStatus': 'OPERATIONAL',
            'rating': 4.5,
            'userRatingCount': 127,
            'nationalPhoneNumber': '(555) 123-4567',
            'websiteUri': 'https://joeplumbing.com',
            'googleMapsUri': 'https://maps.google.com/...',
        }
        base.update(overrides)
        return base

    def test_parses_name_from_displayname_dict(self):
        raw = self._raw_place()
        parsed = GooglePlacesService.parse_place(raw)
        assert parsed['name'] == 'Joe Plumbing'

    def test_parses_coordinates(self):
        raw = self._raw_place()
        parsed = GooglePlacesService.parse_place(raw)
        assert parsed['latitude'] == 34.0525
        assert parsed['longitude'] == -118.244

    def test_parses_rating(self):
        raw = self._raw_place()
        parsed = GooglePlacesService.parse_place(raw)
        assert parsed['rating'] == 4.5
        assert parsed['total_reviews'] == 127

    def test_missing_website_becomes_empty_string(self):
        raw = self._raw_place()
        del raw['websiteUri']
        parsed = GooglePlacesService.parse_place(raw)
        assert parsed['website_url'] == ''

    def test_missing_price_level_is_none(self):
        raw = self._raw_place()
        parsed = GooglePlacesService.parse_place(raw)
        assert parsed['price_level'] is None

    def test_price_level_string_enum_converted_to_int(self):
        cases = {
            'PRICE_LEVEL_FREE': 0,
            'PRICE_LEVEL_INEXPENSIVE': 1,
            'PRICE_LEVEL_MODERATE': 2,
            'PRICE_LEVEL_EXPENSIVE': 3,
            'PRICE_LEVEL_VERY_EXPENSIVE': 4,
        }
        for string_val, expected_int in cases.items():
            raw = self._raw_place(priceLevel=string_val)
            parsed = GooglePlacesService.parse_place(raw)
            assert parsed['price_level'] == expected_int, f"Failed for {string_val}"
