"""Google Places API (New) service for discovering local businesses."""
import hashlib
import logging
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

PLACES_CACHE_TTL = 60 * 60 * 24 * 3  # 3 days — matches enrichment cache window

PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACES_DETAIL_URL = "https://places.googleapis.com/v1/places/{place_id}"

NEARBY_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.types",
    "places.businessStatus",
    "places.rating",
    "places.userRatingCount",
    "places.priceLevel",
    "places.nationalPhoneNumber",
    "places.websiteUri",
    "places.googleMapsUri",
])

DETAIL_FIELD_MASK = ",".join([
    "id",
    "displayName",
    "formattedAddress",
    "location",
    "types",
    "businessStatus",
    "rating",
    "userRatingCount",
    "priceLevel",
    "nationalPhoneNumber",
    "websiteUri",
    "googleMapsUri",
    "regularOpeningHours",
    "reviews",
])


class GooglePlacesService:
    """Wrapper around Google Places API (New) for business discovery."""

    def __init__(self) -> None:
        self.api_key = settings.GOOGLE_PLACES_API_KEY
        self.headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
        }

    @staticmethod
    def _cache_key(lat: float, lng: float, radius_meters: int, place_type: str, keyword: str) -> str:
        """Build a deterministic cache key for a single-type nearby search.

        lat/lng are rounded to 4 decimal places (~11 m) so near-identical searches
        caused by floating-point jitter share the same cache entry.
        """
        parts = f"{lat:.4f}:{lng:.4f}:{radius_meters}:{place_type}:{keyword.lower().strip()}"
        digest = hashlib.md5(parts.encode()).hexdigest()[:12]
        return f"places:nearby:{digest}"

    def search_nearby(
        self,
        lat: float,
        lng: float,
        radius_meters: int,
        place_types: list[str],
        keyword: str = "",
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for businesses near a location.

        When multiple place types are requested, each type is fetched and cached
        independently so a repeat scan for a subset of types returns immediately
        from cache without hitting the Google Places API.  Results are merged and
        deduplicated by place ID before returning.

        Caller is responsible for persistence.
        """
        if keyword:
            logger.warning(
                "Keyword '%s' ignored: searchNearby does not support text filtering. "
                "Use the searchText endpoint for keyword-based discovery.",
                keyword,
            )

        # Normalise: treat no-type as a single unnamed bucket so it gets its own cache entry.
        buckets: list[str] = place_types if place_types else [""]

        seen_ids: set[str] = set()
        merged: list[dict[str, Any]] = []

        for ptype in buckets:
            places = self._fetch_type(lat, lng, radius_meters, ptype, keyword, max_results)
            for place in places:
                pid = place.get("id", "")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    merged.append(place)

        logger.info("Google Places search_nearby returned %d unique results across %d type(s)", len(merged), len(buckets))
        return merged

    def _fetch_type(
        self,
        lat: float,
        lng: float,
        radius_meters: int,
        place_type: str,
        keyword: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Return results for a single place type, serving from cache when available."""
        cache_key = self._cache_key(lat, lng, radius_meters, place_type, keyword)
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("Google Places cache hit — %d results for type=%r", len(cached), place_type or "(any)")
            return cached

        results = self._call_api(lat, lng, radius_meters, place_type, max_results)
        cache.set(cache_key, results, PLACES_CACHE_TTL)
        logger.info(
            "Google Places API — %d results for type=%r, cached for %d days",
            len(results), place_type or "(any)", PLACES_CACHE_TTL // 86400,
        )
        return results

    def _call_api(
        self,
        lat: float,
        lng: float,
        radius_meters: int,
        place_type: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Make the actual Google Places searchNearby HTTP call for one place type."""
        payload: dict[str, Any] = {
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(min(radius_meters, 50000)),
                }
            },
            "maxResultCount": min(max_results, 20),
        }
        if place_type:
            payload["includedTypes"] = [place_type]

        with httpx.Client(timeout=30) as client:
            response = client.post(
                PLACES_NEARBY_URL,
                json=payload,
                headers={**self.headers, "X-Goog-FieldMask": NEARBY_FIELD_MASK},
            )

            if response.status_code == 400:
                error_msg = response.json().get("error", {}).get("message", "")
                bad_types = self._parse_unsupported_types(error_msg)
                if bad_types and place_type in bad_types:
                    logger.warning("Skipping unsupported place type %r", place_type)
                    return []

            if not response.is_success:
                logger.error("Google Places searchNearby failed %s: %s", response.status_code, response.text)
            response.raise_for_status()
            return response.json().get("places", [])

    @staticmethod
    def _parse_unsupported_types(error_message: str) -> set[str]:
        """Extract type names from Google's 'Unsupported types: foo, bar.' error message."""
        if "Unsupported types:" not in error_message:
            return set()
        types_part = error_message.split("Unsupported types:")[1].strip().rstrip(".")
        return {t.strip() for t in types_part.split(",") if t.strip()}

    def get_place_detail(self, place_id: str) -> dict[str, Any]:
        """Fetch full details for a single place.

        Args:
            place_id: The Google place resource name (e.g. 'places/ChIJ...')
        """
        url = PLACES_DETAIL_URL.format(place_id=place_id)
        with httpx.Client(timeout=15) as client:
            response = client.get(
                url,
                headers={**self.headers, "X-Goog-FieldMask": DETAIL_FIELD_MASK},
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def parse_place(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize raw Places API response to our internal schema.

        Args:
            raw: Raw place dict from the API response.

        Returns:
            Normalized dict ready for Business model creation.
        """
        # The New Places API returns price_level as a string enum, not an integer.
        _price_level_map = {
            "PRICE_LEVEL_FREE": 0,
            "PRICE_LEVEL_INEXPENSIVE": 1,
            "PRICE_LEVEL_MODERATE": 2,
            "PRICE_LEVEL_EXPENSIVE": 3,
            "PRICE_LEVEL_VERY_EXPENSIVE": 4,
        }
        raw_price = raw.get("priceLevel")
        price_level = _price_level_map.get(raw_price) if isinstance(raw_price, str) else raw_price

        location = raw.get("location", {})
        display_name = raw.get("displayName", {})
        return {
            "google_place_id": raw.get("id", ""),
            "google_maps_url": raw.get("googleMapsUri", ""),
            "name": display_name.get("text", "") if isinstance(display_name, dict) else str(display_name),
            "formatted_address": raw.get("formattedAddress", ""),
            "phone_number": raw.get("nationalPhoneNumber", ""),
            "website_url": raw.get("websiteUri", ""),
            "latitude": location.get("latitude", 0),
            "longitude": location.get("longitude", 0),
            "place_types": raw.get("types", []),
            "business_status": raw.get("businessStatus", ""),
            "price_level": price_level,
            "rating": raw.get("rating"),
            "total_reviews": raw.get("userRatingCount", 0),
            "opening_hours": raw.get("regularOpeningHours", {}),
            "reviews_data": raw.get("reviews", []),
        }
