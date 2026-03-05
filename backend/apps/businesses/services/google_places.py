"""Google Places API (New) service for discovering local businesses."""
import logging
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

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

        Returns raw place data dicts. Caller is responsible for persistence.
        """
        payload: dict[str, Any] = {
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_meters),
                }
            },
            "maxResultCount": min(max_results, 20),
        }

        if keyword:
            # searchNearby does not support textQuery — log and ignore rather than
            # sending an invalid field that causes a 400.
            logger.warning(
                "Keyword '%s' ignored: searchNearby does not support text filtering. "
                "Use the searchText endpoint for keyword-based discovery.",
                keyword,
            )

        results = []
        with httpx.Client(timeout=30) as client:
            for attempt in range(2):
                if place_types:
                    payload["includedTypes"] = place_types
                elif attempt == 0:
                    # place_types was originally non-empty but all were stripped
                    pass  # fall through without includedTypes

                response = client.post(
                    PLACES_NEARBY_URL,
                    json=payload,
                    headers={**self.headers, "X-Goog-FieldMask": NEARBY_FIELD_MASK},
                )

                if response.status_code == 400 and attempt == 0:
                    error_msg = response.json().get("error", {}).get("message", "")
                    bad_types = self._parse_unsupported_types(error_msg)
                    if bad_types:
                        logger.warning(
                            "Unsupported place types %s — retrying without them", bad_types
                        )
                        place_types = [t for t in place_types if t not in bad_types]
                        payload.pop("includedTypes", None)
                        continue  # retry once with cleaned list

                if not response.is_success:
                    logger.error(
                        "Google Places searchNearby failed %s: %s",
                        response.status_code,
                        response.text,
                    )
                response.raise_for_status()
                results.extend(response.json().get("places", []))
                break

        logger.info("Google Places returned %d results", len(results))
        return results

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
