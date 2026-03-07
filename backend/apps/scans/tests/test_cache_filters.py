"""Tests for cache-filter helpers and Google Places error handling.

Covers:
    GROUP A — _filter_needs_enrichment
    GROUP B — _filter_needs_scoring
    GROUP C — GooglePlacesService._parse_unsupported_types
    GROUP D — GooglePlacesService.search_nearby retry-on-400 logic
"""
import json
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

import httpx
import pytest
from django.utils import timezone

from apps.businesses.services.google_places import GooglePlacesService
from apps.scans.tasks import _filter_needs_enrichment, _filter_needs_scoring


# ---------------------------------------------------------------------------
# Shared helpers / factories
# ---------------------------------------------------------------------------

def _make_scan(**kwargs):
    from apps.scans.models import Scan

    defaults = {
        "center_lat": "34.0522",
        "center_lng": "-118.2437",
        "radius_meters": 8000,
        "place_types": ["plumber"],
    }
    defaults.update(kwargs)
    return Scan.objects.create(**defaults)


def _make_business(scan, suffix="A"):
    from apps.businesses.models import Business

    return Business.objects.create(
        google_place_id=f"place_filter_{suffix}",
        name=f"Filter Biz {suffix}",
        latitude="34.05",
        longitude="-118.24",
        scan=scan,
    )


def _make_enrichment(business, status, enriched_at=None):
    """Create an EnrichmentProfile for *business* with given status and enriched_at."""
    from apps.enrichment.models import EnrichmentProfile

    return EnrichmentProfile.objects.create(
        business=business,
        status=status,
        enriched_at=enriched_at,
    )


def _make_score(business, tier="tier1", scored_at=None):
    """Create an AutomationScore for *business*. scored_at overrides auto_now_add via update()."""
    from apps.scoring.models import AutomationScore

    score = AutomationScore.objects.create(
        business=business,
        tier=tier,
        overall_score=75,
        confidence="0.80",
        crm_score=70,
        scheduling_score=70,
        marketing_score=70,
        invoicing_score=70,
        key_signals=[],
        summary="ok",
        model_used="claude-test",
    )
    if scored_at is not None:
        # auto_now_add prevents passing scored_at to create(); use queryset update.
        AutomationScore.objects.filter(pk=score.pk).update(scored_at=scored_at)
        score.refresh_from_db()
    return score


# ---------------------------------------------------------------------------
# GROUP A — _filter_needs_enrichment
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFilterNeedsEnrichment:
    """_filter_needs_enrichment returns IDs that need (re-)enrichment."""

    def test_all_ids_returned_when_no_enrichment_profile_exists(self):
        scan = _make_scan()
        biz1 = _make_business(scan, "E1")
        biz2 = _make_business(scan, "E2")

        result = _filter_needs_enrichment([biz1.pk, biz2.pk])

        assert sorted(result) == sorted([biz1.pk, biz2.pk])

    def test_empty_list_when_all_recently_enriched_completed(self):
        scan = _make_scan()
        biz1 = _make_business(scan, "E3")
        biz2 = _make_business(scan, "E4")

        recent = timezone.now() - timedelta(hours=12)
        _make_enrichment(biz1, "completed", enriched_at=recent)
        _make_enrichment(biz2, "completed", enriched_at=recent)

        result = _filter_needs_enrichment([biz1.pk, biz2.pk])

        assert result == []

    def test_only_stale_ids_returned_in_mixed_scenario(self):
        scan = _make_scan()
        fresh_biz = _make_business(scan, "E5")
        stale_biz = _make_business(scan, "E6")
        no_profile_biz = _make_business(scan, "E7")

        recent = timezone.now() - timedelta(hours=6)
        stale = timezone.now() - timedelta(days=5)

        _make_enrichment(fresh_biz, "completed", enriched_at=recent)
        _make_enrichment(stale_biz, "completed", enriched_at=stale)
        # no_profile_biz has no EnrichmentProfile at all

        result = _filter_needs_enrichment([fresh_biz.pk, stale_biz.pk, no_profile_biz.pk])

        assert fresh_biz.pk not in result
        assert stale_biz.pk in result
        assert no_profile_biz.pk in result

    def test_failed_status_always_included_regardless_of_enriched_at(self):
        scan = _make_scan()
        biz = _make_business(scan, "E8")

        # Even if enriched_at is recent, a failed profile must be re-enriched.
        recent = timezone.now() - timedelta(hours=1)
        _make_enrichment(biz, "failed", enriched_at=recent)

        result = _filter_needs_enrichment([biz.pk])

        assert biz.pk in result

    def test_pending_status_always_included(self):
        scan = _make_scan()
        biz = _make_business(scan, "E9")

        recent = timezone.now() - timedelta(hours=1)
        _make_enrichment(biz, "pending", enriched_at=recent)

        result = _filter_needs_enrichment([biz.pk])

        assert biz.pk in result

    def test_in_progress_status_always_included(self):
        scan = _make_scan()
        biz = _make_business(scan, "E10")

        recent = timezone.now() - timedelta(hours=1)
        _make_enrichment(biz, "in_progress", enriched_at=recent)

        result = _filter_needs_enrichment([biz.pk])

        assert biz.pk in result

    def test_empty_business_ids_returns_empty(self):
        result = _filter_needs_enrichment([])
        assert result == []

    def test_preserves_input_order(self):
        scan = _make_scan()
        bizs = [_make_business(scan, f"EO{i}") for i in range(4)]
        ids_in_order = [b.pk for b in bizs]

        result = _filter_needs_enrichment(ids_in_order)

        assert result == ids_in_order


# ---------------------------------------------------------------------------
# GROUP B — _filter_needs_scoring
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFilterNeedsScoring:
    """_filter_needs_scoring returns IDs that need Tier 1 scoring."""

    def test_all_ids_returned_when_no_score_exists(self):
        scan = _make_scan()
        biz1 = _make_business(scan, "S1")
        biz2 = _make_business(scan, "S2")

        result = _filter_needs_scoring([biz1.pk, biz2.pk])

        assert sorted(result) == sorted([biz1.pk, biz2.pk])

    def test_stale_tier1_score_included(self):
        scan = _make_scan()
        biz = _make_business(scan, "S3")

        stale = timezone.now() - timedelta(days=5)
        _make_score(biz, tier="tier1", scored_at=stale)

        result = _filter_needs_scoring([biz.pk])

        assert biz.pk in result

    def test_recent_tier1_score_excluded(self):
        scan = _make_scan()
        biz = _make_business(scan, "S4")

        recent = timezone.now() - timedelta(hours=6)
        _make_score(biz, tier="tier1", scored_at=recent)

        result = _filter_needs_scoring([biz.pk])

        assert biz.pk not in result

    def test_force_rescore_included_even_if_recently_scored(self):
        scan = _make_scan()
        biz = _make_business(scan, "S5")

        recent = timezone.now() - timedelta(hours=1)
        _make_score(biz, tier="tier1", scored_at=recent)

        result = _filter_needs_scoring([biz.pk], force_rescore={biz.pk})

        assert biz.pk in result

    def test_force_rescore_ids_not_queried_against_db_cache(self):
        """IDs in force_rescore must be skipped in the DB filter entirely."""
        scan = _make_scan()
        biz = _make_business(scan, "S6")

        recent = timezone.now() - timedelta(hours=1)
        _make_score(biz, tier="tier1", scored_at=recent)

        from apps.scoring.models import AutomationScore

        with patch.object(
            AutomationScore.objects,
            "filter",
            wraps=AutomationScore.objects.filter,
        ) as mock_filter:
            _filter_needs_scoring([biz.pk], force_rescore={biz.pk})

        # The filter was called, but biz.pk must NOT appear in business_id__in
        # because force_rescore IDs are excluded from to_check before the query.
        for call_args in mock_filter.call_args_list:
            kwargs = call_args.kwargs
            if "business_id__in" in kwargs:
                assert biz.pk not in kwargs["business_id__in"]

    def test_mixed_scenario_only_uncached_returned(self):
        scan = _make_scan()
        fresh_biz = _make_business(scan, "S7")
        stale_biz = _make_business(scan, "S8")
        no_score_biz = _make_business(scan, "S9")

        recent = timezone.now() - timedelta(hours=2)
        stale = timezone.now() - timedelta(days=4)

        _make_score(fresh_biz, tier="tier1", scored_at=recent)
        _make_score(stale_biz, tier="tier1", scored_at=stale)

        result = _filter_needs_scoring([fresh_biz.pk, stale_biz.pk, no_score_biz.pk])

        assert fresh_biz.pk not in result
        assert stale_biz.pk in result
        assert no_score_biz.pk in result

    def test_tier2_score_does_not_satisfy_tier1_cache(self):
        """A tier2 score must not count as a tier1 cache hit."""
        scan = _make_scan()
        biz = _make_business(scan, "S10")

        recent = timezone.now() - timedelta(hours=1)
        _make_score(biz, tier="tier2", scored_at=recent)

        result = _filter_needs_scoring([biz.pk])

        assert biz.pk in result

    def test_empty_business_ids_returns_empty(self):
        result = _filter_needs_scoring([])
        assert result == []

    def test_none_force_rescore_treated_as_empty_set(self):
        scan = _make_scan()
        biz = _make_business(scan, "S11")

        recent = timezone.now() - timedelta(hours=1)
        _make_score(biz, tier="tier1", scored_at=recent)

        # Should not raise; None treated as empty set → biz excluded (cache hit)
        result = _filter_needs_scoring([biz.pk], force_rescore=None)

        assert biz.pk not in result


# ---------------------------------------------------------------------------
# GROUP C — GooglePlacesService._parse_unsupported_types
# ---------------------------------------------------------------------------

class TestParseUnsupportedTypes:
    """Static method — no DB needed."""

    def test_single_type_extracted(self):
        msg = "Unsupported types: bar"
        result = GooglePlacesService._parse_unsupported_types(msg)
        assert result == {"bar"}

    def test_multiple_comma_separated_types_extracted(self):
        msg = "Unsupported types: foo, bar, baz"
        result = GooglePlacesService._parse_unsupported_types(msg)
        assert result == {"foo", "bar", "baz"}

    def test_unrelated_400_error_returns_empty_set(self):
        msg = "Request contains an invalid argument."
        result = GooglePlacesService._parse_unsupported_types(msg)
        assert result == set()

    def test_empty_string_returns_empty_set(self):
        result = GooglePlacesService._parse_unsupported_types("")
        assert result == set()

    def test_trailing_period_stripped(self):
        msg = "Unsupported types: dental_clinic."
        result = GooglePlacesService._parse_unsupported_types(msg)
        assert result == {"dental_clinic"}

    def test_trailing_period_with_multiple_types(self):
        msg = "Unsupported types: foo, bar."
        result = GooglePlacesService._parse_unsupported_types(msg)
        assert result == {"foo", "bar"}

    def test_whitespace_trimmed_from_type_names(self):
        msg = "Unsupported types:   alpha ,  beta  "
        result = GooglePlacesService._parse_unsupported_types(msg)
        assert result == {"alpha", "beta"}


# ---------------------------------------------------------------------------
# GROUP D — GooglePlacesService.search_nearby retry-on-400
# ---------------------------------------------------------------------------

def _make_http_response(status_code: int, body: dict) -> MagicMock:
    """Build a MagicMock that quacks like an httpx.Response for search_nearby tests.

    httpx.Response requires a real Request object before raise_for_status() can
    be called, so we mock the whole response rather than constructing one directly.
    """
    import json as _json

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.is_success = (200 <= status_code < 300)
    mock_resp.text = _json.dumps(body)
    mock_resp.json.return_value = body

    if mock_resp.is_success:
        mock_resp.raise_for_status.return_value = None
    else:
        request = httpx.Request("POST", "https://places.googleapis.com/v1/places:searchNearby")
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"{status_code} error",
            request=request,
            response=MagicMock(spec=httpx.Response),
        )

    return mock_resp


@pytest.mark.django_db
class TestSearchNearbyRetry:
    """search_nearby retries once when Google returns 400 with unsupported types."""

    def _service(self):
        with patch("apps.businesses.services.google_places.settings") as mock_settings:
            mock_settings.GOOGLE_PLACES_API_KEY = "test-key"
            svc = GooglePlacesService.__new__(GooglePlacesService)
            svc.api_key = "test-key"
            svc.headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": "test-key",
            }
        return svc

    def test_retries_once_on_400_with_unsupported_type(self):
        """First 400 with unsupported type triggers one retry; retry succeeds."""
        svc = self._service()

        bad_response = _make_http_response(
            400,
            {"error": {"message": "Unsupported types: bad_type"}},
        )
        good_response = _make_http_response(
            200,
            {"places": [{"id": "place_1", "displayName": {"text": "Good Biz"}}]},
        )

        mock_post = MagicMock(side_effect=[bad_response, good_response])

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post = mock_post
            mock_client_cls.return_value = mock_client

            places = svc.search_nearby(
                lat=34.05,
                lng=-118.24,
                radius_meters=5000,
                place_types=["plumber", "bad_type"],
            )

        assert mock_post.call_count == 2
        assert len(places) == 1
        assert places[0]["id"] == "place_1"

    def test_bad_type_removed_on_retry(self):
        """The unsupported type must be absent from the payload on the second attempt."""
        svc = self._service()

        bad_response = _make_http_response(
            400,
            {"error": {"message": "Unsupported types: bad_type"}},
        )
        good_response = _make_http_response(
            200,
            {"places": []},
        )

        mock_post = MagicMock(side_effect=[bad_response, good_response])

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post = mock_post
            mock_client_cls.return_value = mock_client

            svc.search_nearby(
                lat=34.05,
                lng=-118.24,
                radius_meters=5000,
                place_types=["plumber", "bad_type"],
            )

        # Inspect payload of the second call — bad_type must be gone.
        second_call_kwargs = mock_post.call_args_list[1].kwargs
        second_payload = second_call_kwargs.get("json", {})
        included = second_payload.get("includedTypes", [])
        assert "bad_type" not in included
        assert "plumber" in included

    def test_second_400_raises_http_status_error(self):
        """If the retry also returns 400 we must raise and not loop further."""
        svc = self._service()

        bad_response_1 = _make_http_response(
            400,
            {"error": {"message": "Unsupported types: bad_type"}},
        )
        bad_response_2 = _make_http_response(
            400,
            {"error": {"message": "Unsupported types: plumber"}},
        )

        mock_post = MagicMock(side_effect=[bad_response_1, bad_response_2])

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post = mock_post
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                svc.search_nearby(
                    lat=34.05,
                    lng=-118.24,
                    radius_meters=5000,
                    place_types=["plumber", "bad_type"],
                )

        assert mock_post.call_count == 2

    def test_no_retry_on_400_without_unsupported_type(self):
        """A 400 error whose message does not match must not trigger retry."""
        svc = self._service()

        bad_response = _make_http_response(
            400,
            {"error": {"message": "API key missing."}},
        )

        mock_post = MagicMock(return_value=bad_response)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post = mock_post
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                svc.search_nearby(
                    lat=34.05,
                    lng=-118.24,
                    radius_meters=5000,
                    place_types=["plumber"],
                )

        # Only one attempt — no retry for non-type-related 400.
        assert mock_post.call_count == 1

    def test_success_on_first_attempt_returns_places(self):
        """No 400 at all — single call, returns places list."""
        svc = self._service()

        good_response = _make_http_response(
            200,
            {"places": [
                {"id": "p1", "displayName": {"text": "Biz One"}},
                {"id": "p2", "displayName": {"text": "Biz Two"}},
            ]},
        )

        mock_post = MagicMock(return_value=good_response)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post = mock_post
            mock_client_cls.return_value = mock_client

            places = svc.search_nearby(
                lat=34.05,
                lng=-118.24,
                radius_meters=5000,
                place_types=["plumber"],
            )

        assert mock_post.call_count == 1
        assert len(places) == 2
        assert places[0]["id"] == "p1"
        assert places[1]["id"] == "p2"
