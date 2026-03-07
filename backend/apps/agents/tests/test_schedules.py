"""Tests for AgentSchedule model, API endpoints, and run_scheduled_scan task."""
import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

from apps.workspaces.services import get_or_create_workspace_for_user
from apps.agents.models import AgentConfig, AgentSchedule
from apps.agents.services import get_or_create_agent_config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(username="sched_tester")


@pytest.fixture
def workspace(db, user):
    return get_or_create_workspace_for_user(user)


@pytest.fixture
def config(db, workspace):
    cfg = get_or_create_agent_config(workspace)
    cfg.service_name = "Lawn Pro Software"
    cfg.default_lat = "34.0522"
    cfg.default_lng = "-118.2437"
    cfg.is_configured = True
    cfg.save()
    return cfg


@pytest.fixture
def auth_client(db, user, workspace):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def schedule(db, workspace):
    return AgentSchedule.objects.create(
        workspace=workspace,
        name="Weekday scan",
        cron_expression="0 9 * * 1-5",
        scan_place_types=["plumber", "hvac_contractor"],
        scan_radius_meters=5000,
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Schedule CRUD API
# ---------------------------------------------------------------------------

class TestScheduleAPI:
    def test_list_empty(self, db, auth_client, workspace):
        resp = auth_client.get("/api/agent/schedules/")
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_create_schedule(self, db, auth_client, workspace):
        resp = auth_client.post("/api/agent/schedules/", {
            "name": "Daily scan",
            "cron_expression": "0 9 * * *",
            "scan_place_types": ["plumber"],
            "scan_radius_meters": 5000,
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Daily scan"
        assert data["cron_expression"] == "0 9 * * *"
        assert AgentSchedule.objects.filter(workspace=workspace).count() == 1

    def test_create_requires_place_types(self, db, auth_client, workspace):
        resp = auth_client.post("/api/agent/schedules/", {
            "name": "Bad schedule",
            "cron_expression": "0 9 * * *",
            "scan_place_types": [],
        }, format="json")
        assert resp.status_code == 400

    def test_create_invalid_cron(self, db, auth_client, workspace):
        resp = auth_client.post("/api/agent/schedules/", {
            "name": "Bad cron",
            "cron_expression": "not-a-cron",
            "scan_place_types": ["plumber"],
        }, format="json")
        assert resp.status_code == 400

    def test_patch_schedule(self, db, auth_client, workspace, schedule):
        resp = auth_client.patch(f"/api/agent/schedules/{schedule.id}/", {
            "is_active": False,
        }, format="json")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_delete_schedule(self, db, auth_client, workspace, schedule):
        resp = auth_client.delete(f"/api/agent/schedules/{schedule.id}/")
        assert resp.status_code == 204
        assert not AgentSchedule.objects.filter(pk=schedule.id).exists()

    def test_unauthenticated_returns_401(self, db):
        resp = APIClient().get("/api/agent/schedules/")
        assert resp.status_code == 401

    def test_cross_tenant_isolation(self, db, workspace, schedule):
        """User B cannot see User A's schedules."""
        user_b = User.objects.create_user(username="user_b_sched")
        ws_b = get_or_create_workspace_for_user(user_b)
        client_b = APIClient()
        refresh = RefreshToken.for_user(user_b)
        client_b.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        resp = client_b.get("/api/agent/schedules/")
        assert resp.status_code == 200
        assert resp.json()["results"] == []

        resp = client_b.patch(f"/api/agent/schedules/{schedule.id}/", {"is_active": False}, format="json")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# run-now endpoint
# ---------------------------------------------------------------------------

class TestRunNow:
    def test_run_now_no_location(self, db, auth_client, workspace, schedule, config):
        """run-now fails if no default location is set."""
        config.default_lat = None
        config.default_lng = None
        config.save()
        resp = auth_client.post(f"/api/agent/schedules/{schedule.id}/run-now/")
        assert resp.status_code == 400
        assert "location" in resp.json()["detail"].lower()

    def test_run_now_paused(self, db, auth_client, workspace, schedule, config):
        """run-now fails when agent is paused."""
        config.is_paused = True
        config.save()
        resp = auth_client.post(f"/api/agent/schedules/{schedule.id}/run-now/")
        assert resp.status_code == 400
        assert "paused" in resp.json()["detail"].lower()

    @patch("apps.agents.tasks.run_scheduled_scan.delay")
    def test_run_now_queues_task(self, mock_delay, db, auth_client, workspace, schedule, config):
        """run-now enqueues the Celery task."""
        resp = auth_client.post(f"/api/agent/schedules/{schedule.id}/run-now/")
        assert resp.status_code == 200
        assert resp.json()["queued"] is True
        mock_delay.assert_called_once_with(schedule.pk)


# ---------------------------------------------------------------------------
# run_scheduled_scan task logic
# ---------------------------------------------------------------------------

class TestRunScheduledScanTask:
    @patch("apps.scans.tasks.run_scan.delay")
    def test_creates_scan(self, mock_run, db, workspace, schedule, config):
        from apps.agents.tasks import run_scheduled_scan
        from apps.scans.models import Scan

        result = run_scheduled_scan(schedule.pk)
        assert "scan_id" in result
        scan = Scan.objects.get(pk=result["scan_id"])
        assert scan.trigger_type == "scheduled"
        assert scan.workspace == workspace
        mock_run.assert_called_once_with(scan.pk)

    def test_skips_when_paused(self, db, workspace, schedule, config):
        from apps.agents.tasks import run_scheduled_scan

        config.is_paused = True
        config.save()
        result = run_scheduled_scan(schedule.pk)
        assert result["skipped"] == "agent paused"

    def test_skips_when_no_location(self, db, workspace, schedule, config):
        from apps.agents.tasks import run_scheduled_scan

        config.default_lat = None
        config.default_lng = None
        config.save()
        result = run_scheduled_scan(schedule.pk)
        assert result["skipped"] == "no default location configured"

    def test_skips_inactive_schedule(self, db, workspace, schedule, config):
        from apps.agents.tasks import run_scheduled_scan

        schedule.is_active = False
        schedule.save()
        result = run_scheduled_scan(schedule.pk)
        assert "skipped" in result

    def test_updates_last_run_at(self, db, workspace, schedule, config):
        from apps.agents.tasks import run_scheduled_scan

        with patch("apps.scans.tasks.run_scan.delay"):
            run_scheduled_scan(schedule.pk)

        schedule.refresh_from_db()
        assert schedule.last_run_at is not None
