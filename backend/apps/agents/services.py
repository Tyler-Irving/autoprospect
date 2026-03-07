"""Agent services — config retrieval and prompt building."""
from __future__ import annotations

from apps.workspaces.models import Workspace

from .models import AgentConfig


def get_or_create_agent_config(workspace: Workspace) -> AgentConfig:
    """Return the AgentConfig for a workspace, creating it if it doesn't exist."""
    config, _ = AgentConfig.objects.get_or_create(workspace=workspace)
    return config


def build_agent_system_prompt(config: AgentConfig) -> str:
    """Build a Claude system prompt injecting the workspace's agent configuration.

    Falls back to generic automation-agency framing when config is incomplete.
    """
    if not config or not config.service_name:
        return (
            "You are a B2B sales intelligence AI for a software automation agency. "
            "Evaluate businesses for automation readiness."
        )

    tone_instructions = {
        AgentConfig.OutreachTone.FORMAL: (
            "Write in a formal, professional tone. Use complete sentences. "
            "No contractions. Address prospects respectfully."
        ),
        AgentConfig.OutreachTone.SEMI_FORMAL: (
            "Write in a confident, friendly-but-professional tone. "
            "Be approachable without being informal."
        ),
        AgentConfig.OutreachTone.CASUAL: (
            "Write in a conversational, approachable tone. "
            "First-name basis. Keep it natural and human."
        ),
    }

    selling_points_text = ""
    if config.key_selling_points:
        points = "\n".join(f"- {p}" for p in config.key_selling_points)
        selling_points_text = f"\nKey selling points:\n{points}"

    custom_context = (
        f"\nAdditional context: {config.custom_talking_points}"
        if config.custom_talking_points
        else ""
    )

    industries_text = (
        f"\nTarget industries: {', '.join(config.target_industries)}"
        if config.target_industries
        else ""
    )

    ideal_customer = (
        f"\nIdeal customer profile: {config.target_biz_description}"
        if config.target_biz_description
        else ""
    )

    agent_intro = f"You are representing {config.agent_name}. " if config.agent_name else ""

    return (
        f"{agent_intro}You are a B2B sales intelligence AI for {config.service_name}.\n\n"
        f"Your client sells: {config.service_description}"
        f"{industries_text}"
        f"{ideal_customer}"
        f"{selling_points_text}"
        f"{custom_context}\n\n"
        f"Outreach tone: {tone_instructions.get(config.outreach_tone, '')}"
    )
