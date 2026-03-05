"""Prompt builders for Tier 1 and Tier 2 Claude scoring."""
from __future__ import annotations

from typing import Any

TIER1_SYSTEM = """You are an automation sales intelligence system evaluating local businesses for automation readiness.

You score businesses on their need for 4 automation categories:
- CRM: lead tracking, follow-ups, customer relationship management
- Scheduling: online booking, appointment management, calendar automation
- Marketing: email campaigns, social media automation, review management
- Invoicing: digital invoicing, payment processing, quote generation

SCORING RUBRIC:
HIGH (70-100): No tools detected, obviously manual processes, reviews mention pain points like slow response, missed follow-ups, scheduling issues. Ideal target.
MEDIUM (40-69): Some tools present but gaps remain, partial automation, room for improvement.
LOW (0-39): Already well automated, too small/inactive, or not a good fit.

RESPOND WITH ONLY valid JSON matching this exact shape (no preamble, no markdown):
{
  "overall_score": <0-100 integer>,
  "confidence": <0.0-1.0 float>,
  "crm_score": <0-100 integer>,
  "scheduling_score": <0-100 integer>,
  "marketing_score": <0-100 integer>,
  "invoicing_score": <0-100 integer>,
  "key_signals": [<up to 6 short signal strings>],
  "summary": "<2-3 sentence summary of automation readiness>",
  "recommended_pitch_angle": "<1-2 sentences on best approach>",
  "estimated_deal_value": "<low|medium|high|enterprise>"
}"""


def build_tier1_prompt(business: Any, enrichment: Any) -> str:
    """Build the user message for Tier 1 scoring.

    Args:
        business: Business model instance.
        enrichment: EnrichmentProfile model instance (may have None fields).

    Returns:
        Formatted user prompt string.
    """
    e = enrichment

    # Sample reviews (max 5)
    reviews_data = business.reviews_data or []
    sample_reviews = []
    for r in reviews_data[:5]:
        text = r.get("text", {}).get("text", "") if isinstance(r.get("text"), dict) else r.get("text", "")
        rating = r.get("rating", "")
        if text:
            sample_reviews.append(f"  [{rating}★] {text[:300]}")
    reviews_block = "\n".join(sample_reviews) if sample_reviews else "  (no reviews available)"

    # Negative/positive signals
    neg = getattr(e, "negative_signals", []) or []
    pos = getattr(e, "positive_signals", []) or []

    lines = [
        "=== BUSINESS INFO ===",
        f"Name: {business.name}",
        f"Types: {', '.join(business.place_types or [])}",
        f"Address: {business.formatted_address}",
        f"Phone: {business.phone_number or 'none'}",
        f"Website: {business.website_url or 'none'}",
        f"Rating: {business.rating or 'n/a'} ({business.total_reviews} reviews)",
        "",
        "=== WEBSITE ANALYSIS ===",
        f"Reachable: {getattr(e, 'website_reachable', None)}",
        f"Platform: {getattr(e, 'website_platform', '') or 'unknown'}",
        f"Has SSL: {getattr(e, 'has_ssl', None)}",
        f"Mobile responsive: {getattr(e, 'is_mobile_responsive', None)}",
        f"Load time ms: {getattr(e, 'website_load_time_ms', None)}",
        f"Title: {getattr(e, 'website_title', '') or 'none'}",
        "",
        "=== TECH STACK ===",
        f"Has online booking: {getattr(e, 'has_online_booking', None)}",
        f"Has live chat: {getattr(e, 'has_live_chat', None)}",
        f"Has contact form: {getattr(e, 'has_contact_form', None)}",
        f"Has email signup: {getattr(e, 'has_email_signup', None)}",
        f"CRM detected: {getattr(e, 'detected_crm', '') or 'none'}",
        f"Scheduling tool: {getattr(e, 'detected_scheduling_tool', '') or 'none'}",
        f"Email platform: {getattr(e, 'detected_email_platform', '') or 'none'}",
        f"Payment processor: {getattr(e, 'detected_payment_processor', '') or 'none'}",
        f"Analytics: {', '.join(getattr(e, 'detected_analytics', []) or []) or 'none'}",
        f"Technologies: {', '.join(getattr(e, 'detected_technologies', []) or []) or 'none'}",
        "",
        "=== SOCIAL PRESENCE ===",
        f"Facebook: {'yes' if getattr(e, 'facebook_url', '') else 'no'}",
        f"Instagram: {'yes' if getattr(e, 'instagram_url', '') else 'no'}",
        f"LinkedIn: {'yes' if getattr(e, 'linkedin_url', '') else 'no'}",
        f"Yelp: {'yes' if getattr(e, 'yelp_url', '') else 'no'}",
        "",
        "=== REVIEW SIGNALS ===",
        f"Pain points from reviews: {', '.join(neg) if neg else 'none detected'}",
        f"Positive signals: {', '.join(pos) if pos else 'none detected'}",
        "",
        "=== SAMPLE REVIEWS ===",
        reviews_block,
        "",
        "=== WEBSITE CONTENT EXCERPT ===",
        (getattr(e, "website_text_content", "") or "")[:5000] or "(not available)",
    ]

    return "\n".join(lines)
