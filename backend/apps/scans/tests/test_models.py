"""Tests for Scan model."""
import pytest
from apps.scans.models import Scan


@pytest.mark.django_db
class TestScanProgressPct:
    def test_pending_is_zero(self, scan_factory):
        scan = scan_factory(status=Scan.Status.PENDING)
        assert scan.progress_pct == 0

    def test_discovering_is_15(self, scan_factory):
        scan = scan_factory(status=Scan.Status.DISCOVERING)
        assert scan.progress_pct == 15

    def test_completed_is_100(self, scan_factory):
        scan = scan_factory(status=Scan.Status.COMPLETED)
        assert scan.progress_pct == 100

    def test_enriching_scales_with_progress(self, scan_factory):
        scan = scan_factory(
            status=Scan.Status.ENRICHING_T1,
            businesses_found=100,
            businesses_enriched=50,
        )
        # base 40 + 50% of 30 = 55
        assert scan.progress_pct == 55

    def test_failed_is_zero(self, scan_factory):
        scan = scan_factory(status=Scan.Status.FAILED)
        assert scan.progress_pct == 0


@pytest.mark.django_db
class TestScanStr:
    def test_label_used_if_present(self, scan_factory):
        scan = scan_factory(label="LA Plumbers")
        assert str(scan) == "LA Plumbers"

    def test_fallback_without_label(self, scan_factory):
        scan = scan_factory(label="")
        assert "Scan #" in str(scan)
