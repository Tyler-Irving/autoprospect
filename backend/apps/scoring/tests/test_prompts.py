"""Tests for scoring prompt builder: build_tier1_prompt."""
import pytest
from unittest.mock import MagicMock

from apps.scoring.services.prompts import build_tier1_prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_business(**kwargs):
    biz = MagicMock()
    biz.name = kwargs.get("name", "Joe Plumbing")
    biz.place_types = kwargs.get("place_types", ["plumber"])
    biz.formatted_address = kwargs.get("formatted_address", "123 Main St, LA, CA")
    biz.phone_number = kwargs.get("phone_number", "(555) 123-4567")
    biz.website_url = kwargs.get("website_url", "https://joeplumbing.com")
    biz.rating = kwargs.get("rating", 4.5)
    biz.total_reviews = kwargs.get("total_reviews", 127)
    biz.reviews_data = kwargs.get("reviews_data", [])
    return biz


def _make_enrichment(**kwargs):
    e = MagicMock()
    e.website_reachable = kwargs.get("website_reachable", True)
    e.website_platform = kwargs.get("website_platform", "wordpress")
    e.has_ssl = kwargs.get("has_ssl", True)
    e.is_mobile_responsive = kwargs.get("is_mobile_responsive", True)
    e.website_load_time_ms = kwargs.get("website_load_time_ms", 350)
    e.website_title = kwargs.get("website_title", "Joe Plumbing")
    e.has_online_booking = kwargs.get("has_online_booking", False)
    e.has_live_chat = kwargs.get("has_live_chat", False)
    e.has_contact_form = kwargs.get("has_contact_form", True)
    e.has_email_signup = kwargs.get("has_email_signup", False)
    e.detected_crm = kwargs.get("detected_crm", "")
    e.detected_scheduling_tool = kwargs.get("detected_scheduling_tool", "")
    e.detected_email_platform = kwargs.get("detected_email_platform", "")
    e.detected_payment_processor = kwargs.get("detected_payment_processor", "")
    e.detected_analytics = kwargs.get("detected_analytics", [])
    e.detected_technologies = kwargs.get("detected_technologies", [])
    e.facebook_url = kwargs.get("facebook_url", "")
    e.instagram_url = kwargs.get("instagram_url", "")
    e.linkedin_url = kwargs.get("linkedin_url", "")
    e.yelp_url = kwargs.get("yelp_url", "")
    e.negative_signals = kwargs.get("negative_signals", [])
    e.positive_signals = kwargs.get("positive_signals", [])
    e.website_text_content = kwargs.get("website_text_content", "Some website content")
    return e


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBuildTier1Prompt:
    def test_returns_string(self):
        prompt = build_tier1_prompt(_make_business(), _make_enrichment())
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_includes_business_name(self):
        biz = _make_business(name="Acme Plumbing")
        prompt = build_tier1_prompt(biz, _make_enrichment())
        assert "Acme Plumbing" in prompt

    def test_includes_address(self):
        biz = _make_business(formatted_address="456 Oak Ave, Chicago, IL")
        prompt = build_tier1_prompt(biz, _make_enrichment())
        assert "456 Oak Ave" in prompt

    def test_includes_rating_and_reviews(self):
        biz = _make_business(rating=4.2, total_reviews=89)
        prompt = build_tier1_prompt(biz, _make_enrichment())
        assert "4.2" in prompt
        assert "89" in prompt

    def test_none_enrichment_fields_handled(self):
        """Enrichment with many None/missing attributes should not raise."""
        e = MagicMock(spec=[])  # no attributes at all — getattr will return defaults
        biz = _make_business()
        # Should not raise
        prompt = build_tier1_prompt(biz, e)
        assert isinstance(prompt, str)

    def test_missing_website_url_shows_none(self):
        biz = _make_business(website_url=None)
        e = _make_enrichment()
        prompt = build_tier1_prompt(biz, e)
        assert "Website: none" in prompt

    def test_missing_phone_shows_none(self):
        biz = _make_business(phone_number=None)
        prompt = build_tier1_prompt(biz, _make_enrichment())
        assert "Phone: none" in prompt

    def test_website_text_truncated_to_5000(self):
        long_text = "word " * 2000  # > 5000 chars
        e = _make_enrichment(website_text_content=long_text)
        prompt = build_tier1_prompt(_make_business(), e)
        # The prompt should not contain the full text — check excerpt section
        # Extract everything after "=== WEBSITE CONTENT EXCERPT ==="
        excerpt_marker = "=== WEBSITE CONTENT EXCERPT ==="
        assert excerpt_marker in prompt
        excerpt = prompt.split(excerpt_marker, 1)[1].strip()
        assert len(excerpt) <= 5000 + 50  # allow small overhead for newlines

    def test_no_reviews_shows_placeholder(self):
        biz = _make_business(reviews_data=[])
        prompt = build_tier1_prompt(biz, _make_enrichment())
        assert "no reviews available" in prompt

    def test_reviews_included_in_prompt(self):
        reviews = [
            {"text": {"text": "Great service, very professional!"}, "rating": 5},
            {"text": {"text": "Called three times, no callback."}, "rating": 2},
        ]
        biz = _make_business(reviews_data=reviews)
        prompt = build_tier1_prompt(biz, _make_enrichment())
        assert "Great service" in prompt
        assert "no callback" in prompt

    def test_max_five_reviews_included(self):
        reviews = [
            {"text": {"text": f"Review number {i}"}, "rating": 4}
            for i in range(10)
        ]
        biz = _make_business(reviews_data=reviews)
        prompt = build_tier1_prompt(biz, _make_enrichment())
        # Only reviews 0-4 should appear
        assert "Review number 4" in prompt
        assert "Review number 5" not in prompt

    def test_review_text_truncated_at_300_chars(self):
        long_review_text = "x" * 500
        reviews = [{"text": {"text": long_review_text}, "rating": 3}]
        biz = _make_business(reviews_data=reviews)
        prompt = build_tier1_prompt(biz, _make_enrichment())
        # The review snippet in the prompt should be at most 300 x chars
        assert "x" * 301 not in prompt
        assert "x" * 300 in prompt

    def test_negative_signals_listed(self):
        e = _make_enrichment(negative_signals=["slow response", "missed follow-ups"])
        prompt = build_tier1_prompt(_make_business(), e)
        assert "slow response" in prompt
        assert "missed follow-ups" in prompt

    def test_positive_signals_listed(self):
        e = _make_enrichment(positive_signals=["professional", "on time"])
        prompt = build_tier1_prompt(_make_business(), e)
        assert "professional" in prompt
        assert "on time" in prompt

    def test_empty_negative_signals_shows_none_detected(self):
        e = _make_enrichment(negative_signals=[])
        prompt = build_tier1_prompt(_make_business(), e)
        assert "none detected" in prompt

    def test_place_types_included(self):
        biz = _make_business(place_types=["dentist", "health"])
        prompt = build_tier1_prompt(biz, _make_enrichment())
        assert "dentist" in prompt

    def test_empty_place_types_handled(self):
        biz = _make_business(place_types=[])
        prompt = build_tier1_prompt(biz, _make_enrichment())
        assert isinstance(prompt, str)

    def test_none_reviews_data_handled(self):
        biz = _make_business(reviews_data=None)
        prompt = build_tier1_prompt(biz, _make_enrichment())
        assert "no reviews available" in prompt

    def test_website_content_not_available_when_empty(self):
        e = _make_enrichment(website_text_content="")
        prompt = build_tier1_prompt(_make_business(), e)
        assert "not available" in prompt

    def test_facebook_shows_yes_when_set(self):
        e = _make_enrichment(facebook_url="https://facebook.com/test")
        prompt = build_tier1_prompt(_make_business(), e)
        assert "Facebook: yes" in prompt

    def test_facebook_shows_no_when_empty(self):
        e = _make_enrichment(facebook_url="")
        prompt = build_tier1_prompt(_make_business(), e)
        assert "Facebook: no" in prompt

    def test_detected_crm_included(self):
        e = _make_enrichment(detected_crm="hubspot")
        prompt = build_tier1_prompt(_make_business(), e)
        assert "hubspot" in prompt

    def test_detected_analytics_listed(self):
        e = _make_enrichment(detected_analytics=["google_analytics", "hotjar"])
        prompt = build_tier1_prompt(_make_business(), e)
        assert "google_analytics" in prompt

    def test_none_analytics_handled(self):
        e = _make_enrichment(detected_analytics=None)
        prompt = build_tier1_prompt(_make_business(), e)
        # Should show 'none' rather than crashing
        assert "Analytics: none" in prompt
