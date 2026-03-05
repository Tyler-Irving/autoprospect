"""Tests for enrichment Celery task: enrich_business."""
import pytest
from unittest.mock import MagicMock, patch

from apps.enrichment.models import EnrichmentProfile
from apps.enrichment.tasks import enrich_business


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_business(website_url="https://example.com", suffix="E"):
    from apps.scans.models import Scan
    from apps.businesses.models import Business

    scan = Scan.objects.create(
        center_lat="34.0522",
        center_lng="-118.2437",
        radius_meters=8000,
    )
    return Business.objects.create(
        google_place_id=f"place_enrich_{suffix}",
        name="Enrich Test Biz",
        latitude="34.05",
        longitude="-118.24",
        scan=scan,
        website_url=website_url,
    )


CRAWLER_RESULT = {
    "website_reachable": True,
    "website_title": "Test Biz",
    "website_description": "We fix things",
    "website_text_content": "Some text content here",
    "website_load_time_ms": 320,
    "has_ssl": True,
    "is_mobile_responsive": True,
    "website_platform": "wordpress",
    "detected_technologies": ["wordpress"],
    "has_online_booking": False,
    "has_live_chat": False,
    "has_contact_form": True,
    "has_email_signup": False,
    "detected_crm": "",
    "detected_scheduling_tool": "",
    "detected_email_platform": "",
    "detected_payment_processor": "",
    "detected_analytics": [],
    "social_links": {"facebook": "https://facebook.com/test"},
    "facebook_url": "https://facebook.com/test",
    "instagram_url": "",
    "linkedin_url": "",
    "yelp_url": "",
    "negative_signals": [],
    "positive_signals": ["professional"],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEnrichBusiness:
    def test_nonexistent_business_returns_error(self):
        result = enrich_business(99999)
        assert result == {"error": "Business not found"}

    def test_creates_enrichment_profile(self):
        biz = _make_business(suffix="C1")
        with patch("apps.enrichment.tasks.WebsiteCrawler") as MockCrawler:
            MockCrawler.return_value.crawl.return_value = dict(CRAWLER_RESULT)
            enrich_business(biz.pk)

        assert EnrichmentProfile.objects.filter(business=biz).exists()

    def test_profile_status_set_to_completed(self):
        biz = _make_business(suffix="C2")
        with patch("apps.enrichment.tasks.WebsiteCrawler") as MockCrawler:
            MockCrawler.return_value.crawl.return_value = dict(CRAWLER_RESULT)
            enrich_business(biz.pk)

        profile = EnrichmentProfile.objects.get(business=biz)
        assert profile.status == EnrichmentProfile.Status.COMPLETED

    def test_profile_fields_populated(self):
        biz = _make_business(suffix="C3")
        with patch("apps.enrichment.tasks.WebsiteCrawler") as MockCrawler:
            MockCrawler.return_value.crawl.return_value = dict(CRAWLER_RESULT)
            enrich_business(biz.pk)

        profile = EnrichmentProfile.objects.get(business=biz)
        assert profile.website_reachable is True
        assert profile.website_platform == "wordpress"
        assert profile.has_contact_form is True

    def test_scan_businesses_enriched_incremented(self):
        biz = _make_business(suffix="C4")
        scan = biz.scan
        assert scan.businesses_enriched == 0

        with patch("apps.enrichment.tasks.WebsiteCrawler") as MockCrawler:
            MockCrawler.return_value.crawl.return_value = dict(CRAWLER_RESULT)
            enrich_business(biz.pk)

        scan.refresh_from_db()
        assert scan.businesses_enriched == 1

    def test_result_contains_reachable_flag(self):
        biz = _make_business(suffix="C5")
        with patch("apps.enrichment.tasks.WebsiteCrawler") as MockCrawler:
            MockCrawler.return_value.crawl.return_value = dict(CRAWLER_RESULT)
            result = enrich_business(biz.pk)

        assert result["business_id"] == biz.pk
        assert result["reachable"] is True

    def test_idempotent_upserts_existing_profile(self):
        biz = _make_business(suffix="C6")
        EnrichmentProfile.objects.create(business=biz, website_title="Old Title")

        with patch("apps.enrichment.tasks.WebsiteCrawler") as MockCrawler:
            MockCrawler.return_value.crawl.return_value = dict(CRAWLER_RESULT)
            enrich_business(biz.pk)

        # Should still be just one profile
        assert EnrichmentProfile.objects.filter(business=biz).count() == 1
        profile = EnrichmentProfile.objects.get(business=biz)
        assert profile.website_title == "Test Biz"

    def test_crawler_exception_marks_profile_failed(self):
        biz = _make_business(suffix="C7")
        # Pre-create profile so we can check its status after failure
        profile = EnrichmentProfile.objects.create(business=biz)

        with patch("apps.enrichment.tasks.WebsiteCrawler") as MockCrawler, \
             patch.object(enrich_business, "retry", side_effect=RuntimeError("retry")):
            MockCrawler.return_value.crawl.side_effect = RuntimeError("network error")
            try:
                enrich_business(biz.pk)
            except RuntimeError:
                pass

        profile.refresh_from_db()
        assert profile.status == EnrichmentProfile.Status.FAILED
        assert "network error" in profile.error_log

    def test_enrichment_at_is_set(self):
        biz = _make_business(suffix="C8")
        with patch("apps.enrichment.tasks.WebsiteCrawler") as MockCrawler:
            MockCrawler.return_value.crawl.return_value = dict(CRAWLER_RESULT)
            enrich_business(biz.pk)

        profile = EnrichmentProfile.objects.get(business=biz)
        assert profile.enriched_at is not None
