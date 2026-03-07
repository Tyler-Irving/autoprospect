"""Tests for scans Celery tasks: run_scan, start_scoring, finalize_scan."""
import pytest
from unittest.mock import MagicMock, patch

from apps.scans.models import Scan
from apps.scans.tasks import finalize_scan, run_scan, start_scoring


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scan(**kwargs):
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
        google_place_id=f"place_test_{suffix}",
        name=f"Test Biz {suffix}",
        latitude="34.05",
        longitude="-118.24",
        scan=scan,
    )


# ---------------------------------------------------------------------------
# run_scan
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRunScan:
    def test_nonexistent_scan_returns_error(self):
        result = run_scan(99999)
        assert result == {"error": "Scan not found"}

    def test_empty_discovery_completes_scan(self):
        scan = _make_scan()
        with patch("apps.scans.tasks._run_discovery", return_value=[]):
            result = run_scan(scan.pk)

        scan.refresh_from_db()
        assert scan.status == Scan.Status.COMPLETED
        assert result["businesses_found"] == 0

    def test_discovery_transitions_to_enriching(self):
        scan = _make_scan()
        biz = _make_business(scan, "X")

        with patch("apps.scans.tasks._run_discovery", return_value=[biz.pk]), \
             patch("apps.enrichment.tasks.enrich_business.s") as mock_enrich_s, \
             patch("apps.scans.tasks.start_scoring.s") as mock_scoring_s, \
             patch("apps.scans.tasks.chord") as mock_chord:

            mock_chord.return_value.delay.return_value = None
            result = run_scan(scan.pk)

        scan.refresh_from_db()
        assert scan.status == Scan.Status.ENRICHING_T1
        assert result["businesses_found"] == 1

    def test_discovery_exception_marks_scan_failed_on_last_retry(self):
        """Scan is only marked FAILED when all retries are exhausted."""
        scan = _make_scan()
        # max_retries=0 means the first attempt is the last — scan should be FAILED.
        with patch("apps.scans.tasks._run_discovery", side_effect=RuntimeError("boom")), \
             patch.object(run_scan, "retry", side_effect=RuntimeError("retry")), \
             patch.object(run_scan, "max_retries", 0):
            try:
                run_scan(scan.pk)
            except RuntimeError:
                pass

        scan.refresh_from_db()
        assert scan.status == Scan.Status.FAILED
        assert "boom" in scan.error_message

    def test_discovery_exception_does_not_mark_failed_during_retry(self):
        """Scan is NOT marked FAILED on intermediate retry attempts."""
        scan = _make_scan()
        original_status = scan.status
        # max_retries=2 and default retries=0 — this is NOT the last attempt.
        with patch("apps.scans.tasks._run_discovery", side_effect=RuntimeError("boom")), \
             patch.object(run_scan, "retry", side_effect=RuntimeError("retry")), \
             patch.object(run_scan, "max_retries", 2):
            try:
                run_scan(scan.pk)
            except RuntimeError:
                pass

        scan.refresh_from_db()
        assert scan.status != Scan.Status.FAILED

    def test_result_contains_scan_id(self):
        scan = _make_scan()
        with patch("apps.scans.tasks._run_discovery", return_value=[]):
            result = run_scan(scan.pk)
        assert result["scan_id"] == scan.pk


# ---------------------------------------------------------------------------
# start_scoring
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStartScoring:
    def test_nonexistent_scan_returns_error(self):
        result = start_scoring([], 99999, [1, 2])
        assert result == {"error": "Scan not found"}

    def test_transitions_scan_to_scoring_t1(self):
        scan = _make_scan()
        biz = _make_business(scan, "S1")

        with patch("apps.scoring.tasks.score_business_tier1.s") as mock_score_s, \
             patch("apps.scans.tasks.finalize_scan.s") as mock_finalize_s, \
             patch("apps.scans.tasks.chord") as mock_chord:
            mock_chord.return_value.delay.return_value = None
            start_scoring([], scan.pk, [biz.pk])

        scan.refresh_from_db()
        assert scan.status == Scan.Status.SCORING_T1

    def test_returns_scoring_started_count(self):
        scan = _make_scan()
        biz1 = _make_business(scan, "S2")
        biz2 = _make_business(scan, "S3")

        with patch("apps.scoring.tasks.score_business_tier1.s"), \
             patch("apps.scans.tasks.finalize_scan.s"), \
             patch("apps.scans.tasks.chord") as mock_chord:
            mock_chord.return_value.delay.return_value = None
            result = start_scoring([], scan.pk, [biz1.pk, biz2.pk])

        assert result["scoring_started"] == 2


# ---------------------------------------------------------------------------
# finalize_scan
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFinalizeScan:
    def test_nonexistent_scan_returns_error(self):
        result = finalize_scan([], 99999)
        assert result == {"error": "Scan not found"}

    def test_marks_scan_completed(self):
        scan = _make_scan()
        finalize_scan([], scan.pk)
        scan.refresh_from_db()
        assert scan.status == Scan.Status.COMPLETED
        assert scan.completed_at is not None

    def test_counts_scored_results(self):
        scan = _make_scan()
        results = [
            {"business_id": 1, "overall_score": 80, "api_cost_cents": 5},
            {"business_id": 2, "overall_score": 60, "api_cost_cents": 3},
            {"error": "Business not found"},  # should not count
        ]
        result = finalize_scan(results, scan.pk)
        assert result["scored"] == 2

    def test_none_results_handled(self):
        scan = _make_scan()
        result = finalize_scan(None, scan.pk)
        assert result["scored"] == 0

    def test_empty_results_handled(self):
        scan = _make_scan()
        result = finalize_scan([], scan.pk)
        assert result["scored"] == 0
        scan.refresh_from_db()
        assert scan.status == Scan.Status.COMPLETED
