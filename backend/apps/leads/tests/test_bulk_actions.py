"""Tests for leads bulk-action endpoint and lead list CRUD."""
import pytest

from apps.leads.models import Lead, LeadActivity, LeadList


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scan_business(suffix="B", workspace=None):
    from apps.scans.models import Scan
    from apps.businesses.models import Business

    scan = Scan.objects.create(
        center_lat="34.05",
        center_lng="-118.24",
        radius_meters=5000,
        workspace=workspace,
    )
    business = Business.objects.create(
        google_place_id=f"place_bulk_{suffix}",
        name=f"Bulk Test Biz {suffix}",
        latitude="34.05",
        longitude="-118.24",
        scan=scan,
    )
    return scan, business


def _make_lead(suffix="B", workspace=None):
    _, biz = _make_scan_business(suffix, workspace=workspace)
    return Lead.objects.create(business=biz, workspace=workspace)


# ---------------------------------------------------------------------------
# Bulk action — update_status
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBulkUpdateStatus:
    def test_bulk_update_status_changes_all_leads(self, api_client, test_workspace):
        lead1 = _make_lead("S1", workspace=test_workspace)
        lead2 = _make_lead("S2", workspace=test_workspace)

        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": [lead1.pk, lead2.pk],
            "action": "update_status",
            "value": "contacted",
        }, format="json")

        assert resp.status_code == 200
        assert resp.data["updated"] == 2
        lead1.refresh_from_db()
        lead2.refresh_from_db()
        assert lead1.outreach_status == "contacted"
        assert lead2.outreach_status == "contacted"

    def test_bulk_update_status_with_empty_lead_ids_returns_400(self, api_client):
        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": [],
            "action": "update_status",
            "value": "contacted",
        }, format="json")
        assert resp.status_code == 400

    def test_bulk_action_missing_action_returns_400(self, api_client, test_workspace):
        lead = _make_lead("S3", workspace=test_workspace)
        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": [lead.pk],
        }, format="json")
        assert resp.status_code == 400

    def test_unknown_action_returns_400(self, api_client, test_workspace):
        lead = _make_lead("S4", workspace=test_workspace)
        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": [lead.pk],
            "action": "fly_to_moon",
            "value": "yes",
        }, format="json")
        assert resp.status_code == 400

    def test_bulk_action_rejects_non_integer_lead_ids(self, api_client):
        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": ["oops"],
            "action": "update_status",
            "value": "contacted",
        }, format="json")
        assert resp.status_code == 400

    def test_bulk_action_rejects_too_many_lead_ids(self, api_client):
        ids = list(range(1, 503))
        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": ids,
            "action": "update_status",
            "value": "contacted",
        }, format="json")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Bulk action — update_priority
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBulkUpdatePriority:
    def test_bulk_update_priority(self, api_client, test_workspace):
        lead1 = _make_lead("P1", workspace=test_workspace)
        lead2 = _make_lead("P2", workspace=test_workspace)

        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": [lead1.pk, lead2.pk],
            "action": "update_priority",
            "value": "high",
        }, format="json")

        assert resp.status_code == 200
        lead1.refresh_from_db()
        lead2.refresh_from_db()
        assert lead1.priority == "high"
        assert lead2.priority == "high"


# ---------------------------------------------------------------------------
# Bulk action — add_tag
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBulkAddTag:
    def test_add_tag_appended_to_leads(self, api_client, test_workspace):
        lead1 = _make_lead("T1", workspace=test_workspace)
        lead2 = _make_lead("T2", workspace=test_workspace)

        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": [lead1.pk, lead2.pk],
            "action": "add_tag",
            "value": "hot-prospect",
        }, format="json")

        assert resp.status_code == 200
        lead1.refresh_from_db()
        lead2.refresh_from_db()
        assert "hot-prospect" in lead1.tags
        assert "hot-prospect" in lead2.tags

    def test_add_tag_not_duplicated(self, api_client, test_workspace):
        lead = _make_lead("T3", workspace=test_workspace)
        lead.tags = ["hot-prospect"]
        lead.save(update_fields=["tags"])

        api_client.post("/api/leads/bulk-action/", {
            "lead_ids": [lead.pk],
            "action": "add_tag",
            "value": "hot-prospect",
        }, format="json")

        lead.refresh_from_db()
        assert lead.tags.count("hot-prospect") == 1

    def test_add_tag_rejects_empty_value(self, api_client, test_workspace):
        lead = _make_lead("T4", workspace=test_workspace)
        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": [lead.pk],
            "action": "add_tag",
            "value": "",
        }, format="json")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Bulk action — add_to_list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBulkAddToList:
    def test_add_to_list_links_leads(self, api_client, test_workspace):
        lead1 = _make_lead("L1", workspace=test_workspace)
        lead2 = _make_lead("L2", workspace=test_workspace)
        lead_list = LeadList.objects.create(name="Hot Plumbers")

        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": [lead1.pk, lead2.pk],
            "action": "add_to_list",
            "value": lead_list.pk,
        }, format="json")

        assert resp.status_code == 200
        assert lead_list.leads.filter(pk=lead1.pk).exists()
        assert lead_list.leads.filter(pk=lead2.pk).exists()

    def test_add_to_nonexistent_list_returns_404(self, api_client, test_workspace):
        lead = _make_lead("L3", workspace=test_workspace)

        resp = api_client.post("/api/leads/bulk-action/", {
            "lead_ids": [lead.pk],
            "action": "add_to_list",
            "value": 99999,
        }, format="json")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# LeadList CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLeadListCRUD:
    def test_create_lead_list(self, api_client):
        resp = api_client.post("/api/lead-lists/", {
            "name": "Top Prospects",
            "description": "Best leads from Q1",
            "color": "#FF5733",
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["name"] == "Top Prospects"
        assert resp.data["lead_count"] == 0

    def test_list_lead_lists(self, api_client):
        LeadList.objects.create(name="List A")
        LeadList.objects.create(name="List B")

        resp = api_client.get("/api/lead-lists/")
        assert resp.status_code == 200
        items = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
        names = [item["name"] for item in items]
        assert "List A" in names
        assert "List B" in names

    def test_get_lead_list_detail(self, api_client):
        lead_list = LeadList.objects.create(name="Dentists Q1")

        resp = api_client.get(f"/api/lead-lists/{lead_list.pk}/")
        assert resp.status_code == 200
        assert resp.data["name"] == "Dentists Q1"

    def test_patch_lead_list_name(self, api_client):
        lead_list = LeadList.objects.create(name="Old Name")

        resp = api_client.patch(f"/api/lead-lists/{lead_list.pk}/", {"name": "New Name"}, format="json")
        assert resp.status_code == 200
        lead_list.refresh_from_db()
        assert lead_list.name == "New Name"

    def test_delete_lead_list(self, api_client):
        lead_list = LeadList.objects.create(name="To Delete")

        resp = api_client.delete(f"/api/lead-lists/{lead_list.pk}/")
        assert resp.status_code == 204
        assert not LeadList.objects.filter(pk=lead_list.pk).exists()

    def test_lead_count_reflects_members(self, api_client, test_workspace):
        lead = _make_lead("LC1", workspace=test_workspace)
        lead_list = LeadList.objects.create(name="Count Test")
        lead_list.leads.add(lead)

        resp = api_client.get(f"/api/lead-lists/{lead_list.pk}/")
        assert resp.data["lead_count"] == 1


# ---------------------------------------------------------------------------
# LeadList add-leads endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLeadListAddLeads:
    def test_add_leads_to_list(self, api_client, test_workspace):
        lead1 = _make_lead("AL1", workspace=test_workspace)
        lead2 = _make_lead("AL2", workspace=test_workspace)
        lead_list = LeadList.objects.create(name="Add Test List")

        resp = api_client.post(
            f"/api/lead-lists/{lead_list.pk}/add-leads/",
            {"lead_ids": [lead1.pk, lead2.pk]},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["added"] == 2
        assert lead_list.leads.filter(pk=lead1.pk).exists()
        assert lead_list.leads.filter(pk=lead2.pk).exists()

    def test_add_leads_empty_ids_adds_zero(self, api_client):
        lead_list = LeadList.objects.create(name="Empty Test")

        resp = api_client.post(
            f"/api/lead-lists/{lead_list.pk}/add-leads/",
            {"lead_ids": []},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["added"] == 0

    def test_add_leads_idempotent(self, api_client, test_workspace):
        lead = _make_lead("AL3", workspace=test_workspace)
        lead_list = LeadList.objects.create(name="Idem Test")
        lead_list.leads.add(lead)

        resp = api_client.post(
            f"/api/lead-lists/{lead_list.pk}/add-leads/",
            {"lead_ids": [lead.pk]},
            format="json",
        )
        assert resp.status_code == 200
        assert lead_list.leads.count() == 1

    def test_add_leads_to_nonexistent_list_returns_404(self, api_client, test_workspace):
        lead = _make_lead("AL4", workspace=test_workspace)

        resp = api_client.post(
            "/api/lead-lists/99999/add-leads/",
            {"lead_ids": [lead.pk]},
            format="json",
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Lead list filtering
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLeadFiltering:
    def test_filter_by_status(self, api_client, test_workspace):
        lead_contacted = _make_lead("F1", workspace=test_workspace)
        lead_contacted.outreach_status = "contacted"
        lead_contacted.save(update_fields=["outreach_status"])

        lead_new = _make_lead("F2", workspace=test_workspace)

        resp = api_client.get("/api/leads/?status=contacted")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.data.get("results", resp.data)]
        assert lead_contacted.pk in ids
        assert lead_new.pk not in ids

    def test_filter_by_tag(self, api_client, test_workspace):
        lead_tagged = _make_lead("F3", workspace=test_workspace)
        lead_tagged.tags = ["vip"]
        lead_tagged.save(update_fields=["tags"])

        lead_other = _make_lead("F4", workspace=test_workspace)

        resp = api_client.get("/api/leads/?tags=vip")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.data.get("results", resp.data)]
        assert lead_tagged.pk in ids
        assert lead_other.pk not in ids

    def test_filter_by_list(self, api_client, test_workspace):
        lead_in_list = _make_lead("F5", workspace=test_workspace)
        lead_out = _make_lead("F6", workspace=test_workspace)
        lead_list = LeadList.objects.create(name="Filter List")
        lead_list.leads.add(lead_in_list)

        resp = api_client.get(f"/api/leads/?list={lead_list.pk}")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.data.get("results", resp.data)]
        assert lead_in_list.pk in ids
        assert lead_out.pk not in ids
