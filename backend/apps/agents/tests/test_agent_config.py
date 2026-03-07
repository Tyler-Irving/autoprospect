"""Tests for AgentConfig model, API endpoints, and prompt builder."""
import pytest
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APIClient
from django.contrib.auth.models import User

from apps.workspaces.services import get_or_create_workspace_for_user
from apps.agents.models import AgentConfig
from apps.agents.services import get_or_create_agent_config, build_agent_system_prompt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(username="github_77777", first_name="agent_tester")


@pytest.fixture
def workspace(db, user):
    return get_or_create_workspace_for_user(user)


@pytest.fixture
def auth_client(db, user, workspace):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestGetOrCreateAgentConfig:
    def test_creates_config_on_first_call(self, db, workspace):
        config = get_or_create_agent_config(workspace)
        assert config.workspace == workspace
        assert config.is_configured is False

    def test_idempotent(self, db, workspace):
        config1 = get_or_create_agent_config(workspace)
        config2 = get_or_create_agent_config(workspace)
        assert config1.pk == config2.pk
        assert AgentConfig.objects.filter(workspace=workspace).count() == 1


class TestBuildAgentSystemPrompt:
    def test_returns_generic_when_unconfigured(self, db, workspace):
        config = get_or_create_agent_config(workspace)
        prompt = build_agent_system_prompt(config)
        assert "automation agency" in prompt.lower()

    def test_injects_service_name(self, db, workspace):
        config = get_or_create_agent_config(workspace)
        config.service_name = "CRM automation for dental offices"
        config.service_description = "We build custom CRM systems for dentists."
        config.save()
        prompt = build_agent_system_prompt(config)
        assert "CRM automation for dental offices" in prompt
        assert "custom CRM systems for dentists" in prompt

    def test_injects_target_industries(self, db, workspace):
        config = get_or_create_agent_config(workspace)
        config.service_name = "Scheduler Pro"
        config.target_industries = ["plumber", "hvac_contractor"]
        config.save()
        prompt = build_agent_system_prompt(config)
        assert "plumber" in prompt
        assert "hvac_contractor" in prompt

    def test_injects_selling_points(self, db, workspace):
        config = get_or_create_agent_config(workspace)
        config.service_name = "AutoBook"
        config.key_selling_points = ["Saves 5 hours/week", "No long-term contracts"]
        config.save()
        prompt = build_agent_system_prompt(config)
        assert "Saves 5 hours/week" in prompt
        assert "No long-term contracts" in prompt

    def test_tone_injected(self, db, workspace):
        config = get_or_create_agent_config(workspace)
        config.service_name = "CleanPro"
        config.outreach_tone = AgentConfig.OutreachTone.CASUAL
        config.save()
        prompt = build_agent_system_prompt(config)
        assert "conversational" in prompt.lower() or "casual" in prompt.lower()

    def test_agent_name_injected(self, db, workspace):
        config = get_or_create_agent_config(workspace)
        config.service_name = "LawnGenius"
        config.agent_name = "Jordan"
        config.save()
        prompt = build_agent_system_prompt(config)
        assert "Jordan" in prompt

    def test_none_config_returns_generic(self, db):
        prompt = build_agent_system_prompt(None)
        assert "automation agency" in prompt.lower()


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestAgentConfigEndpoint:
    def test_get_creates_default_config(self, db, auth_client, workspace):
        resp = auth_client.get("/api/agent/config/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_configured"] is False
        assert data["service_name"] == ""

    def test_patch_updates_fields(self, db, auth_client, workspace):
        resp = auth_client.patch("/api/agent/config/", {
            "service_name": "Plumbing Pro Software",
            "outreach_tone": "casual",
        }, format="json")
        assert resp.status_code == 200
        assert resp.json()["service_name"] == "Plumbing Pro Software"
        assert resp.json()["outreach_tone"] == "casual"

    def test_patch_caps_selling_points_at_5(self, db, auth_client, workspace):
        resp = auth_client.patch("/api/agent/config/", {
            "key_selling_points": ["a", "b", "c", "d", "e", "f"],
        }, format="json")
        assert resp.status_code == 400

    def test_patch_strips_blank_selling_points(self, db, auth_client, workspace):
        resp = auth_client.patch("/api/agent/config/", {
            "key_selling_points": ["Valid point", "  ", ""],
        }, format="json")
        assert resp.status_code == 200
        assert resp.json()["key_selling_points"] == ["Valid point"]

    def test_unauthenticated_returns_401(self, db):
        resp = APIClient().get("/api/agent/config/")
        assert resp.status_code == 401


class TestCompleteOnboarding:
    def test_sets_is_configured(self, db, auth_client, workspace):
        # Set service_name first
        auth_client.patch("/api/agent/config/", {"service_name": "Lawn Pro"}, format="json")
        resp = auth_client.post("/api/agent/onboarding/complete/")
        assert resp.status_code == 200
        assert resp.json()["is_configured"] is True

    def test_fails_without_service_name(self, db, auth_client, workspace):
        resp = auth_client.post("/api/agent/onboarding/complete/")
        assert resp.status_code == 400
        assert "service_name" in resp.json()["detail"]

    def test_is_configured_not_writable_via_patch(self, db, auth_client, workspace):
        """is_configured must only be set via the dedicated endpoint."""
        resp = auth_client.patch("/api/agent/config/", {"is_configured": True}, format="json")
        assert resp.status_code == 200
        # is_configured should still be False (read_only field, ignored)
        config = AgentConfig.objects.get(workspace=workspace)
        assert config.is_configured is False


class TestTogglePause:
    def test_pause_agent(self, db, auth_client, workspace):
        resp = auth_client.post("/api/agent/config/pause/", {"is_paused": True}, format="json")
        assert resp.status_code == 200
        assert resp.json()["is_paused"] is True

    def test_unpause_agent(self, db, auth_client, workspace):
        config = get_or_create_agent_config(workspace)
        config.is_paused = True
        config.save()
        resp = auth_client.post("/api/agent/config/pause/", {"is_paused": False}, format="json")
        assert resp.status_code == 200
        assert resp.json()["is_paused"] is False

    def test_missing_is_paused_returns_400(self, db, auth_client, workspace):
        resp = auth_client.post("/api/agent/config/pause/", {}, format="json")
        assert resp.status_code == 400
