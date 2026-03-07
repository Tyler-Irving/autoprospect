"""Tests for WebsiteCrawler — mocks httpx to avoid real HTTP calls."""
import pytest
from unittest.mock import MagicMock, patch
from apps.enrichment.services.crawler import WebsiteCrawler


SAMPLE_HTML = """
<html>
<head>
  <title>Joe's Plumbing - Hernando MS</title>
  <meta name="description" content="Best plumber in Hernando MS">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="/wp-content/themes/plumber/js/main.js"></script>
</head>
<body>
  <h1>Welcome to Joe's Plumbing</h1>
  <p>Book online today! We offer same-day service.</p>
  <form action="/contact"><h2>Contact Us</h2><input type="email"><button>Send</button></form>
  <a href="https://www.facebook.com/joesplumbing">Follow us</a>
  <a href="https://calendly.com/joesplumbing/appointment">Schedule</a>
</body>
</html>
"""


def _mock_response(html=SAMPLE_HTML, status=200, url="https://joesplumbing.com"):
    mock = MagicMock()
    mock.text = html
    mock.status_code = status
    mock.is_success = status < 400
    mock.headers = {"content-type": "text/html"}
    mock.url = url
    return mock


class TestWebsiteCrawler:
    def test_crawl_reachable_site(self):
        with patch("apps.enrichment.services.crawler.httpx.get") as mock_get:
            mock_get.return_value = _mock_response()
            result = WebsiteCrawler().crawl("https://joesplumbing.com", [])

        assert result["website_reachable"] is True
        assert result["website_title"] == "Joe's Plumbing - Hernando MS"
        assert result["has_ssl"] is True
        assert result["is_mobile_responsive"] is True
        assert result["website_platform"] == "wordpress"
        assert result["has_online_booking"] is True
        assert result["has_contact_form"] is True
        assert result["detected_scheduling_tool"] == "calendly"
        assert "facebook" in result["social_links"]

    def test_crawl_unreachable_site(self):
        with patch("apps.enrichment.services.crawler.httpx.get") as mock_get:
            import httpx
            mock_get.side_effect = httpx.TimeoutException("timeout")
            result = WebsiteCrawler().crawl("https://joesplumbing.com", [])

        assert result["website_reachable"] is False
        assert result["website_title"] == ""
        assert result["has_ssl"] is None

    def test_crawl_empty_url(self):
        result = WebsiteCrawler().crawl("", [])
        assert result["website_reachable"] is False

    def test_crawl_adds_https_scheme(self):
        with patch("apps.enrichment.services.crawler.httpx.get") as mock_get:
            mock_get.return_value = _mock_response()
            WebsiteCrawler().crawl("joesplumbing.com", [])
        called_url = mock_get.call_args[0][0]
        assert called_url.startswith("https://")

    def test_text_truncated_to_5000(self):
        long_html = "<html><body><p>" + ("word " * 2000) + "</p></body></html>"
        with patch("apps.enrichment.services.crawler.httpx.get") as mock_get:
            mock_get.return_value = _mock_response(html=long_html)
            result = WebsiteCrawler().crawl("https://example.com", [])
        assert len(result["website_text_content"]) <= 5000

    def test_non_2xx_returns_unreachable(self):
        with patch("apps.enrichment.services.crawler.httpx.get") as mock_get:
            mock_get.return_value = _mock_response(status=404)
            result = WebsiteCrawler().crawl("https://joesplumbing.com", [])
        assert result["website_reachable"] is False

    def test_blocks_localhost_target(self):
        result = WebsiteCrawler().crawl("http://localhost/admin", [])
        assert result["website_reachable"] is False
