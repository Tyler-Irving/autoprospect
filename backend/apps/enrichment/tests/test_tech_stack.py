"""Tests for TechStackDetector and review signal extraction."""
import pytest
from apps.enrichment.services.tech_stack import TechStackDetector, extract_review_signals


class TestTechStackDetector:
    def _detector(self, html="", headers=None):
        return TechStackDetector(html, headers or {})

    def test_detects_wordpress(self):
        d = self._detector(html='<link href="/wp-content/themes/x/style.css">')
        assert d.detect_platform() == "wordpress"

    def test_detects_squarespace(self):
        d = self._detector(html='<script src="https://static.squarespace.com/static/js/main.js">')
        assert d.detect_platform() == "squarespace"

    def test_detects_calendly(self):
        d = self._detector(html='<a href="https://calendly.com/mybusiness/30min">Book Now</a>')
        assert d.detect_scheduling_tool() == "calendly"

    def test_detects_hubspot_crm(self):
        d = self._detector(html='<script src="https://js.hs-scripts.com/12345.js">')
        assert d.detect_crm() == "hubspot"

    def test_detects_stripe(self):
        d = self._detector(html='<script src="https://js.stripe.com/v3/"></script>')
        assert d.detect_payment_processor() == "stripe"

    def test_detects_google_analytics(self):
        d = self._detector(html='<script async src="https://www.googletagmanager.com/gtag/js?id=G-xxx">')
        assert "google_analytics" in d.detect_analytics()

    def test_has_online_booking_via_keyword(self):
        d = self._detector(html="<p>Book online today!</p>")
        assert d.has_online_booking() is True

    def test_has_online_booking_via_tool(self):
        d = self._detector(html='<script src="https://calendly.com/assets/external/widget.js">')
        assert d.has_online_booking() is True

    def test_has_contact_form(self):
        d = self._detector(html='<form action="/contact"><h2>Contact Us</h2></form>')
        assert d.has_contact_form() is True

    def test_no_contact_form_without_form_tag(self):
        d = self._detector(html="<p>Contact us via phone</p>")
        assert d.has_contact_form() is False

    def test_extracts_facebook_link(self):
        d = self._detector(html='<a href="https://www.facebook.com/mybusiness">Facebook</a>')
        links = d.extract_social_links()
        assert "facebook" in links
        assert "mybusiness" in links["facebook"]

    def test_mobile_responsive_detected_via_crawler(self):
        from unittest.mock import MagicMock, patch
        html = '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body></body></html>'
        mock = MagicMock()
        mock.text = html
        mock.is_success = True
        mock.headers = {}
        mock.url = "https://example.com"
        with patch("apps.enrichment.services.crawler.httpx.get", return_value=mock):
            from apps.enrichment.services.crawler import WebsiteCrawler
            result = WebsiteCrawler().crawl("https://example.com", [])
        assert result["is_mobile_responsive"] is True

    def test_detect_technologies_returns_list(self):
        d = self._detector(html='<script src="/wp-content/themes/x.js"></script><script src="https://js.stripe.com/v3/"></script>')
        techs = d.detect_technologies()
        assert "wordpress" in techs
        assert "stripe" in techs


class TestReviewSignalExtraction:
    def _review(self, text):
        return [{"text": {"text": text}}]

    def test_detects_negative_signal(self):
        reviews = self._review("They never returned my call and had poor communication.")
        negatives, _ = extract_review_signals(reviews)
        assert any("return" in sig or "communication" in sig for sig in negatives)

    def test_detects_positive_signal(self):
        reviews = self._review("They were on time and very professional. Highly recommend!")
        _, positives = extract_review_signals(reviews)
        assert any("professional" in sig or "recommend" in sig for sig in positives)

    def test_empty_reviews(self):
        negatives, positives = extract_review_signals([])
        assert negatives == []
        assert positives == []
