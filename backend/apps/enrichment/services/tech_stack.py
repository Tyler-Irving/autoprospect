"""Tech stack detector — pattern matching on HTML content and HTTP headers."""
from __future__ import annotations

import re
from typing import Any


# Each entry: (field_name, patterns...)
# Patterns are matched against lowercased HTML + headers string.
_CMS_PATTERNS: list[tuple[str, list[str]]] = [
    ("wordpress", ["/wp-content/", "/wp-includes/", "wp-json"]),
    ("squarespace", ["squarespace.com", "static.squarespace.com"]),
    ("wix", ["wix.com", "wixstatic.com", "_wix_"]),
    ("shopify", ["shopify.com", "cdn.shopify.com", "myshopify.com"]),
    ("weebly", ["weebly.com", "weeblycloud.com"]),
    ("godaddy", ["godaddy.com/websites", "godaddysites.com", "secureserver.net/websites"]),
    ("webflow", ["webflow.io", "assets-global.website-files.com"]),
    ("jimdo", ["jimdo.com", "jimdosite.com"]),
]

_SCHEDULING_PATTERNS: list[tuple[str, list[str]]] = [
    ("calendly", ["calendly.com"]),
    ("acuity", ["acuityscheduling.com"]),
    ("setmore", ["setmore.com"]),
    ("booksteam", ["booksteam.com"]),
    ("square_appointments", ["squareup.com/appointments"]),
    ("vagaro", ["vagaro.com"]),
    ("mindbody", ["mindbodyonline.com"]),
    ("booksy", ["booksy.com"]),
    ("jane", ["jane.app", "janeapp.com"]),
    ("servicetitan", ["servicetitan.com"]),
    ("jobber", ["jobber.com", "getjobber.com"]),
    ("housecall_pro", ["housecallpro.com"]),
]

_CRM_PATTERNS: list[tuple[str, list[str]]] = [
    ("hubspot", ["hubspot.com", "hs-scripts.com", "hsforms.com"]),
    ("salesforce", ["salesforce.com", "force.com", "pardot.com"]),
    ("zoho", ["zoho.com", "zohopublic.com"]),
    ("keap", ["keap.com", "infusionsoft.com"]),
    ("pipedrive", ["pipedrive.com"]),
    ("monday", ["monday.com"]),
]

_EMAIL_PATTERNS: list[tuple[str, list[str]]] = [
    ("mailchimp", ["mailchimp.com", "list-manage.com"]),
    ("constantcontact", ["constantcontact.com", "ctctcdn.com"]),
    ("klaviyo", ["klaviyo.com"]),
    ("activecampaign", ["activecampaign.com"]),
    ("convertkit", ["convertkit.com"]),
    ("sendinblue", ["sendinblue.com", "brevo.com"]),
]

_PAYMENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("stripe", ["stripe.com", "js.stripe.com"]),
    ("square", ["squareup.com", "square.link"]),
    ("paypal", ["paypal.com", "paypalobjects.com"]),
    ("venmo", ["venmo.com"]),
    ("clover", ["clover.com"]),
]

_CHAT_PATTERNS: list[tuple[str, list[str]]] = [
    ("intercom", ["intercom.io", "widget.intercom.io"]),
    ("drift", ["drift.com", "js.driftt.com"]),
    ("tawk", ["tawk.to"]),
    ("livechat", ["livechatinc.com", "cdn.livechatinc.com"]),
    ("zendesk_chat", ["zopim.com", "zendesk.com/embeddable"]),
    ("tidio", ["tidio.co", "widget.tidio.com"]),
]

_ANALYTICS_PATTERNS: list[tuple[str, list[str]]] = [
    ("google_analytics", ["google-analytics.com", "gtag/js", "googletagmanager.com"]),
    ("facebook_pixel", ["connect.facebook.net", "fbevents.js"]),
    ("hotjar", ["hotjar.com"]),
    ("mixpanel", ["mixpanel.com"]),
]

_BOOKING_KEYWORDS = ["book now", "book online", "schedule online", "schedule appointment",
                      "make appointment", "request appointment", "book appointment",
                      "online booking", "book a service"]
_CHAT_KEYWORDS = ["live chat", "chat with us", "chat now", "start chat"]
_CONTACT_FORM_KEYWORDS = ["contact us", "contact form", "send message", "get in touch", "send us a message"]
_EMAIL_SIGNUP_KEYWORDS = ["subscribe", "newsletter", "sign up for", "join our list", "email updates"]

_NEGATIVE_REVIEW_SIGNALS = [
    "hard to reach", "didn't call back", "never returned", "no response",
    "poor communication", "slow response", "unresponsive", "disorganized",
    "billing issues", "overcharged", "confusing invoice", "scheduling problems",
    "hard to schedule", "couldn't get appointment",
]
_POSITIVE_REVIEW_SIGNALS = [
    "easy to book", "quick response", "fast response", "on time",
    "professional", "great service", "highly recommend", "punctual",
    "communicative", "transparent pricing", "fair price",
]


class TechStackDetector:
    """Detects tools and capabilities from website HTML and HTTP headers."""

    def __init__(self, html: str, headers: dict[str, str]) -> None:
        self._haystack = (html + " " + " ".join(headers.values())).lower()
        self._html_lower = html.lower()

    def _matches_any(self, patterns: list[str]) -> bool:
        return any(p in self._haystack for p in patterns)

    def detect_platform(self) -> str:
        """Return the detected CMS/website platform name, or empty string."""
        for name, patterns in _CMS_PATTERNS:
            if self._matches_any(patterns):
                return name
        return ""

    def detect_scheduling_tool(self) -> str:
        """Return the detected scheduling tool name, or empty string."""
        for name, patterns in _SCHEDULING_PATTERNS:
            if self._matches_any(patterns):
                return name
        return ""

    def detect_crm(self) -> str:
        """Return the detected CRM name, or empty string."""
        for name, patterns in _CRM_PATTERNS:
            if self._matches_any(patterns):
                return name
        return ""

    def detect_email_platform(self) -> str:
        """Return the detected email marketing platform, or empty string."""
        for name, patterns in _EMAIL_PATTERNS:
            if self._matches_any(patterns):
                return name
        return ""

    def detect_payment_processor(self) -> str:
        """Return the detected payment processor, or empty string."""
        for name, patterns in _PAYMENT_PATTERNS:
            if self._matches_any(patterns):
                return name
        return ""

    def detect_analytics(self) -> list[str]:
        """Return list of detected analytics tools."""
        return [name for name, patterns in _ANALYTICS_PATTERNS if self._matches_any(patterns)]

    def detect_technologies(self) -> list[str]:
        """Return flat list of all detected technologies."""
        found = []
        for group in [_CMS_PATTERNS, _SCHEDULING_PATTERNS, _CRM_PATTERNS,
                      _EMAIL_PATTERNS, _PAYMENT_PATTERNS, _CHAT_PATTERNS, _ANALYTICS_PATTERNS]:
            for name, patterns in group:
                if self._matches_any(patterns):
                    found.append(name)
        return found

    def has_online_booking(self) -> bool:
        """Return True if page has booking keywords or a known scheduling tool."""
        if self.detect_scheduling_tool():
            return True
        return any(kw in self._html_lower for kw in _BOOKING_KEYWORDS)

    def has_live_chat(self) -> bool:
        """Return True if a live chat tool or keyword is detected."""
        for _, patterns in _CHAT_PATTERNS:
            if self._matches_any(patterns):
                return True
        return any(kw in self._html_lower for kw in _CHAT_KEYWORDS)

    def has_contact_form(self) -> bool:
        """Return True if a contact form is likely present."""
        has_form = "<form" in self._html_lower
        has_keyword = any(kw in self._html_lower for kw in _CONTACT_FORM_KEYWORDS)
        return has_form and has_keyword

    def has_email_signup(self) -> bool:
        """Return True if an email signup/newsletter form is likely present."""
        return any(kw in self._html_lower for kw in _EMAIL_SIGNUP_KEYWORDS)

    def extract_social_links(self) -> dict[str, str]:
        """Extract social media profile links from HTML."""
        patterns = {
            "facebook": r'https?://(?:www\.)?facebook\.com/[^\s\'"<>]+',
            "instagram": r'https?://(?:www\.)?instagram\.com/[^\s\'"<>]+',
            "linkedin": r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[^\s\'"<>]+',
            "twitter": r'https?://(?:www\.)?(?:twitter|x)\.com/[^\s\'"<>]+',
            "youtube": r'https?://(?:www\.)?youtube\.com/(?:channel|c|user|@)[^\s\'"<>]+',
            "tiktok": r'https?://(?:www\.)?tiktok\.com/@[^\s\'"<>]+',
            "yelp": r'https?://(?:www\.)?yelp\.com/biz/[^\s\'"<>]+',
        }
        result: dict[str, str] = {}
        for platform, pattern in patterns.items():
            match = re.search(pattern, self._haystack)
            if match:
                result[platform] = match.group(0).rstrip(".,;)'\"")
        return result


def extract_review_signals(reviews: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Extract negative and positive signals from Google review objects.

    Args:
        reviews: List of raw review dicts from Google Places API.

    Returns:
        Tuple of (negative_signals, positive_signals) — unique string lists.
    """
    combined_text = " ".join(
        r.get("text", {}).get("text", "") if isinstance(r.get("text"), dict) else str(r.get("text", ""))
        for r in reviews
    ).lower()

    negatives = list({sig for sig in _NEGATIVE_REVIEW_SIGNALS if sig in combined_text})
    positives = list({sig for sig in _POSITIVE_REVIEW_SIGNALS if sig in combined_text})
    return negatives, positives
