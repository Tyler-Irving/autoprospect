"""Website crawler service — fetches and analyzes business websites."""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .tech_stack import TechStackDetector, extract_review_signals

logger = logging.getLogger(__name__)

CRAWL_TIMEOUT = 10  # seconds
MAX_TEXT_LENGTH = 5000
USER_AGENT = (
    "Mozilla/5.0 (compatible; AutoProspect/1.0; +https://autoprospect.app)"
)


class WebsiteCrawler:
    """Crawl a business website and return enrichment data."""

    def crawl(self, url: str, reviews: list[dict[str, Any]]) -> dict[str, Any]:
        """Fetch and analyze a website URL.

        Args:
            url: The website URL to crawl.
            reviews: Raw review objects from Google Places (for signal extraction).

        Returns:
            Dict of enrichment fields ready to set on EnrichmentProfile.
        """
        if not url:
            return self._empty_result(reachable=False)

        # Ensure scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        start = time.monotonic()
        try:
            response = httpx.get(
                url,
                timeout=CRAWL_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            )
            load_time_ms = int((time.monotonic() - start) * 1000)
        except httpx.TimeoutException:
            logger.warning("Timeout crawling %s", url)
            return self._empty_result(reachable=False)
        except httpx.RequestError as exc:
            logger.warning("Request error crawling %s: %s", url, exc)
            return self._empty_result(reachable=False)

        if not response.is_success:
            logger.warning("Non-2xx crawling %s: %d", url, response.status_code)
            return self._empty_result(reachable=False)

        final_url = str(response.url)
        has_ssl = final_url.startswith("https://")
        # Strip NUL bytes — PostgreSQL rejects them in text fields
        html = response.text.replace("\x00", "")
        headers = dict(response.headers)

        soup = BeautifulSoup(html, "html.parser")
        detector = TechStackDetector(html, headers)

        # Basic page metadata
        title = self._get_title(soup)
        description = self._get_meta(soup, "description")
        is_mobile_responsive = self._check_mobile_responsive(soup)
        # Must come last — decomposes head/script/style tags
        text_content = self._get_text_content(soup)

        # Tech stack
        platform = detector.detect_platform()
        detected_technologies = detector.detect_technologies()
        detected_crm = detector.detect_crm()
        detected_scheduling_tool = detector.detect_scheduling_tool()
        detected_email_platform = detector.detect_email_platform()
        detected_payment_processor = detector.detect_payment_processor()
        detected_analytics = detector.detect_analytics()

        # Capabilities
        has_online_booking = detector.has_online_booking()
        has_live_chat = detector.has_live_chat()
        has_contact_form = detector.has_contact_form()
        has_email_signup = detector.has_email_signup()

        # Social links
        social_links = detector.extract_social_links()
        facebook_url = social_links.get("facebook", "")
        instagram_url = social_links.get("instagram", "")
        linkedin_url = social_links.get("linkedin", "")
        yelp_url = social_links.get("yelp", "")

        # Review signals from stored Google reviews
        negative_signals, positive_signals = extract_review_signals(reviews)

        return {
            "website_reachable": True,
            "website_title": title[:512],
            "website_description": description,
            "website_text_content": text_content,
            "website_load_time_ms": load_time_ms,
            "has_ssl": has_ssl,
            "is_mobile_responsive": is_mobile_responsive,
            "website_platform": platform,
            "detected_technologies": detected_technologies,
            "has_online_booking": has_online_booking,
            "has_live_chat": has_live_chat,
            "has_contact_form": has_contact_form,
            "has_email_signup": has_email_signup,
            "detected_crm": detected_crm,
            "detected_scheduling_tool": detected_scheduling_tool,
            "detected_email_platform": detected_email_platform,
            "detected_payment_processor": detected_payment_processor,
            "detected_analytics": detected_analytics,
            "social_links": social_links,
            "facebook_url": facebook_url[:1024] if facebook_url else "",
            "instagram_url": instagram_url[:1024] if instagram_url else "",
            "linkedin_url": linkedin_url[:1024] if linkedin_url else "",
            "yelp_url": yelp_url[:1024] if yelp_url else "",
            "negative_signals": negative_signals,
            "positive_signals": positive_signals,
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _empty_result(self, reachable: bool = False) -> dict[str, Any]:
        return {
            "website_reachable": reachable,
            "website_title": "",
            "website_description": "",
            "website_text_content": "",
            "website_load_time_ms": None,
            "has_ssl": None,
            "is_mobile_responsive": None,
            "website_platform": "",
            "detected_technologies": [],
            "has_online_booking": None,
            "has_live_chat": None,
            "has_contact_form": None,
            "has_email_signup": None,
            "detected_crm": "",
            "detected_scheduling_tool": "",
            "detected_email_platform": "",
            "detected_payment_processor": "",
            "detected_analytics": [],
            "social_links": {},
            "facebook_url": "",
            "instagram_url": "",
            "linkedin_url": "",
            "yelp_url": "",
            "negative_signals": [],
            "positive_signals": [],
        }

    def _get_title(self, soup: BeautifulSoup) -> str:
        tag = soup.find("title")
        return tag.get_text(strip=True) if tag else ""

    def _get_meta(self, soup: BeautifulSoup, name: str) -> str:
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": f"og:{name}"})
        if tag and tag.get("content"):
            return tag["content"]
        return ""

    def _get_text_content(self, soup: BeautifulSoup) -> str:
        for tag in soup(["script", "style", "nav", "footer", "head"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace and strip any residual NUL bytes
        import re
        text = re.sub(r"\s+", " ", text).replace("\x00", "")
        return text[:MAX_TEXT_LENGTH]

    def _check_mobile_responsive(self, soup: BeautifulSoup) -> bool:
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if viewport and viewport.get("content"):
            return "width=device-width" in viewport["content"].lower()
        return False
