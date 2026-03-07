"""Prompt builders for Tier 1 and Tier 2 Claude scoring."""
from __future__ import annotations

from typing import Any

# ── Shared scoring sections ────────────────────────────────────────────────────

_SCORING_CATEGORIES = """\
You score businesses on their need for 4 automation categories:
- CRM: lead tracking, follow-ups, customer relationship management
- Scheduling: online booking, appointment management, calendar automation
- Marketing: email campaigns, social media automation, review management
- Invoicing: digital invoicing, payment processing, quote generation"""

_SCORING_RUBRIC = """\
SCORING RUBRIC:
HIGH (70-100): No tools detected, obviously manual processes, reviews mention pain points like slow response, missed follow-ups, scheduling issues. Ideal target.
MEDIUM (40-69): Some tools present but gaps remain, partial automation, room for improvement.
LOW (0-39): Already well automated, too small/inactive, or not a good fit."""

_TIER1_OUTPUT_FORMAT = """\
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

_TIER2_EXTRA_INSTRUCTIONS = """\
Your full_dossier must cover ALL of the following in multi-paragraph prose:
1. Current operational state — how this business likely runs today based on all signals
2. Automation gap analysis — specific gaps in CRM, scheduling, marketing, and invoicing
3. Tool recommendations — name real tools by name (e.g., ServiceTitan, Jobber, Housecall Pro, HubSpot, ActiveCampaign, Calendly, Acuity, Square, Stripe, QuickBooks) with rationale for each
4. Implementation roadmap — phased approach (what to fix first, second, third) with rough timelines
5. ROI argument — quantifiable business impact in time saved, leads captured, revenue recovered
6. Objection rebuttals — 2-3 anticipated objections and how to counter them

Your competitor_analysis must cover: how similar local businesses in this market segment and geography typically compare on automation adoption, what best-in-class operators in this space use, and where this specific business ranks relative to peers."""

_TIER2_OUTPUT_FORMAT = """\
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
  "estimated_deal_value": "<low|medium|high|enterprise>",
  "full_dossier": "<multi-paragraph deep-dive prose covering all 6 sections above>",
  "competitor_analysis": "<paragraph on how this business compares to similar local peers on automation adoption>"
}"""

_TONE_INSTRUCTIONS: dict[str, str] = {
    "formal": (
        "Write in a formal, professional tone. Use complete sentences. "
        "No contractions. Address prospects respectfully."
    ),
    "semi_formal": (
        "Write in a confident, friendly-but-professional tone. "
        "Be approachable without being informal."
    ),
    "casual": (
        "Write in a conversational, approachable tone. "
        "First-name basis. Keep it natural and human."
    ),
}

_EMAIL_RULES = """\
RULES:
- Under 150 words total
- Reference one specific thing you know about their business (from the data provided)
- Lead with their pain or gap, NOT your service
- One clear CTA at the end (a 15-minute call, not a purchase)
- No buzzwords: no "streamline", no "leverage", no "synergy", no "game-changer"
- Sound like a person, not a press release
- No spam triggers: no ALL CAPS, no excessive punctuation, no "FREE"

RESPOND WITH ONLY valid JSON (no preamble, no markdown):
{
  "subject": "<email subject line>",
  "body": "<full email body, use \\n for line breaks>"
}"""

_CALL_SCRIPT_STRUCTURE = """\
STRUCTURE:
- Opening (10 seconds): brief, honest intro
- Hook: reference something specific about their business
- Pain question: open-ended question that surfaces a real operational pain
- Bridge: connect their pain to automation without pitching a product
- CTA: ask for a 15-minute call to learn more
- 2-3 objection handlers for: "not interested", "too busy", "already have something"

RESPOND WITH ONLY valid JSON (no preamble, no markdown):
{
  "opening": "<10 second opening>",
  "hook": "<specific reference to their business>",
  "pain_question": "<open-ended pain question>",
  "bridge": "<brief bridge connecting pain to solution>",
  "cta": "<call to action for a short call>",
  "objection_handlers": [
    {"objection": "<objection>", "response": "<response>"}
  ]
}"""


# ── Agent context helpers ──────────────────────────────────────────────────────

def _agent_scoring_intro(agent_config: Any) -> str:
    """Build the opening paragraph for scoring prompts from AgentConfig.

    Falls back to generic automation-agency framing when no config is provided
    or the workspace has not yet completed onboarding.
    """
    if not agent_config or not getattr(agent_config, "service_name", None):
        return (
            "You are an automation sales intelligence system evaluating local "
            "businesses for automation readiness."
        )

    parts = [f"You are a B2B sales intelligence AI for {agent_config.service_name}."]
    if agent_config.service_description:
        parts.append(f"Your client sells: {agent_config.service_description}")
    if agent_config.target_industries:
        parts.append(f"Target industries: {', '.join(agent_config.target_industries)}")
    if agent_config.target_biz_description:
        parts.append(f"Ideal customer profile: {agent_config.target_biz_description}")
    if agent_config.key_selling_points:
        points = "\n".join(f"- {p}" for p in agent_config.key_selling_points)
        parts.append(f"Key selling points:\n{points}")
    if agent_config.custom_talking_points:
        parts.append(f"Additional context: {agent_config.custom_talking_points}")

    return "\n".join(parts)


def _agent_outreach_intro(agent_config: Any, content_type: str) -> str:
    """Build the opening paragraph for outreach prompts from AgentConfig.

    Args:
        agent_config: AgentConfig instance or None.
        content_type: "email" or "call script" — used in the generic fallback.
    """
    if not agent_config or not getattr(agent_config, "service_name", None):
        return (
            f"You are a B2B cold {content_type} copywriter for a local business "
            "automation consultant.\n\n"
            f"Write a cold {content_type} to a local business owner about automation "
            "services (CRM, scheduling, marketing, invoicing)."
        )

    service = agent_config.service_name
    tone_key = getattr(agent_config, "outreach_tone", "semi_formal")
    tone = _TONE_INSTRUCTIONS.get(tone_key, _TONE_INSTRUCTIONS["semi_formal"])

    parts = [
        f"You are a B2B cold {content_type} copywriter for {service}.",
        f"Write a cold {content_type} to a local business owner about {service}.",
    ]
    if agent_config.service_description:
        parts.append(f"What you're selling: {agent_config.service_description}")
    if agent_config.key_selling_points:
        points = "; ".join(agent_config.key_selling_points)
        parts.append(f"Key selling points: {points}")
    if agent_config.custom_talking_points:
        parts.append(f"Additional context: {agent_config.custom_talking_points}")
    parts.append(f"Tone: {tone}")

    return "\n".join(parts)


# ── Dynamic system prompt builders ────────────────────────────────────────────

def build_tier1_system(agent_config: Any = None) -> str:
    """Build Tier 1 scoring system prompt, injecting agent config when available.

    Args:
        agent_config: AgentConfig instance, or None for generic framing.

    Returns:
        Full system prompt string for the Tier 1 Claude call.
    """
    intro = _agent_scoring_intro(agent_config)
    return f"{intro}\n\n{_SCORING_CATEGORIES}\n\n{_SCORING_RUBRIC}\n\n{_TIER1_OUTPUT_FORMAT}"


def build_tier2_system(agent_config: Any = None) -> str:
    """Build Tier 2 deep-analysis system prompt, injecting agent config when available.

    Args:
        agent_config: AgentConfig instance, or None for generic framing.

    Returns:
        Full system prompt string for the Tier 2 Claude call.
    """
    intro = _agent_scoring_intro(agent_config)
    return (
        f"{intro}\n\n"
        f"{_SCORING_CATEGORIES}\n\n"
        f"{_SCORING_RUBRIC}\n\n"
        f"{_TIER2_EXTRA_INSTRUCTIONS}\n\n"
        f"{_TIER2_OUTPUT_FORMAT}"
    )


def build_email_system(agent_config: Any = None) -> str:
    """Build email outreach system prompt, injecting agent config when available.

    Args:
        agent_config: AgentConfig instance, or None for generic framing.

    Returns:
        Full system prompt string for the email Claude call.
    """
    intro = _agent_outreach_intro(agent_config, "email")
    return f"{intro}\n\n{_EMAIL_RULES}"


def build_call_script_system(agent_config: Any = None) -> str:
    """Build call script system prompt, injecting agent config when available.

    Args:
        agent_config: AgentConfig instance, or None for generic framing.

    Returns:
        Full system prompt string for the call script Claude call.
    """
    intro = _agent_outreach_intro(agent_config, "call script")
    return f"{intro}\n\n{_CALL_SCRIPT_STRUCTURE}"


# ── Static constants (backwards-compat aliases) ───────────────────────────────
# These preserve the same prompt content as before — callers that don't yet
# pass an agent_config continue to work unchanged.

TIER1_SYSTEM = build_tier1_system(None)
TIER2_SYSTEM = build_tier2_system(None)
EMAIL_SYSTEM = build_email_system(None)
CALL_SCRIPT_SYSTEM = build_call_script_system(None)


# ── User message builders ─────────────────────────────────────────────────────

def build_tier2_prompt(business: Any, enrichment: Any, tier1_score: Any) -> str:
    """Build the user message for Tier 2 deep-analysis scoring.

    Includes all Tier 1 context plus a section surfacing the existing Tier 1
    assessment so Claude can produce a deeper dossier without re-deriving basics.

    Args:
        business: Business model instance.
        enrichment: EnrichmentProfile model instance (may have None fields).
        tier1_score: AutomationScore instance for tier1, or None if unavailable.

    Returns:
        Formatted user prompt string.
    """
    # Build the base context identical to Tier 1
    base = build_tier1_prompt(business, enrichment)

    lines = [base, ""]

    if tier1_score is not None:
        t = tier1_score
        lines += [
            "=== EXISTING TIER 1 ASSESSMENT ===",
            f"Overall score: {t.overall_score}/100",
            f"CRM score: {t.crm_score}",
            f"Scheduling score: {t.scheduling_score}",
            f"Marketing score: {t.marketing_score}",
            f"Invoicing score: {t.invoicing_score}",
            f"Estimated deal value: {t.estimated_deal_value}",
            f"Key signals: {', '.join(t.key_signals or [])}",
            f"Summary: {t.summary or 'none'}",
            f"Recommended pitch angle: {t.recommended_pitch_angle or 'none'}",
            "",
            "Use the above Tier 1 assessment as a starting point. Go deeper — produce the full dossier and competitor analysis as described in your instructions.",
        ]
    else:
        lines.append("(No prior Tier 1 assessment available — derive all scores from raw data.)")

    return "\n".join(lines)


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


def build_outreach_prompt(business: Any, tier1_score: Any) -> str:
    """Build the user message for outreach generation (email + call script).

    Args:
        business: Business model instance.
        tier1_score: AutomationScore model instance (tier1), may be None.

    Returns:
        Formatted prompt string.
    """
    t = tier1_score

    lines = [
        "=== BUSINESS ===",
        f"Name: {business.name}",
        f"Type: {', '.join(business.place_types or [])}",
        f"Address: {business.formatted_address}",
        f"Phone: {business.phone_number or 'none'}",
        f"Website: {business.website_url or 'none'}",
        f"Rating: {business.rating or 'n/a'} ({business.total_reviews} reviews)",
        "",
    ]

    if t:
        lines += [
            "=== AI ASSESSMENT ===",
            f"Automation score: {t.overall_score}/100",
            f"CRM fit: {t.crm_score}",
            f"Scheduling fit: {t.scheduling_score}",
            f"Marketing fit: {t.marketing_score}",
            f"Invoicing fit: {t.invoicing_score}",
            f"Estimated deal value: {t.estimated_deal_value}",
            f"Key signals: {', '.join(t.key_signals or [])}",
            f"Summary: {t.summary or 'none'}",
            f"Best pitch angle: {t.recommended_pitch_angle or 'none'}",
            "",
        ]

    e = getattr(business, "enrichment", None)
    if e:
        lines += [
            "=== CURRENT TECH STATE ===",
            f"Has online booking: {getattr(e, 'has_online_booking', None)}",
            f"Has live chat: {getattr(e, 'has_live_chat', None)}",
            f"CRM detected: {getattr(e, 'detected_crm', '') or 'none'}",
            f"Scheduling tool: {getattr(e, 'detected_scheduling_tool', '') or 'none'}",
            f"Email platform: {getattr(e, 'detected_email_platform', '') or 'none'}",
            f"Website platform: {getattr(e, 'website_platform', '') or 'unknown'}",
            "",
        ]

    return "\n".join(lines)
