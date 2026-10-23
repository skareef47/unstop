"""
Tests for Action Plans, Approvals, Tickets, and Simulated Actions
"""
import pytest
from fastapi import status


def test_action_plan_lifecycle_and_approval(client):
    conv = client.post("/api/v1/conversations", json={"product_area": "api_gateway"}).json()
    conv_id = conv["id"]

    # Generate action plan
    plan_resp = client.post(f"/api/v1/conversations/{conv_id}/action-plan")
    assert plan_resp.status_code == status.HTTP_201_CREATED
    plan = plan_resp.json()

    assert plan["conversation_id"] == conv_id
    assert plan["status"] == "draft"
    assert len(plan["recommendations"]) > 0

    # Retrieve latest plan
    get_resp = client.get(f"/api/v1/conversations/{conv_id}/action-plan")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["id"] == plan["id"]

    # Approve plan
    approve_resp = client.post(f"/api/v1/action-plans/{plan['id']}/approve")
    assert approve_resp.status_code == status.HTTP_200_OK
    assert approve_resp.json()["status"] == "approved"
    assert approve_resp.json()["approved_at"] is not None


def test_ticket_creation_and_listing(client):
    conv = client.post("/api/v1/conversations", json={"product_area": "crm_sync"}).json()
    conv_id = conv["id"]

    ticket_payload = {
        "summary": "External CRM partner webhook connection timeout",
        "priority": "high",
        "assigned_team": "l2_devops",
    }
    create_resp = client.post(f"/api/v1/conversations/{conv_id}/tickets", json=ticket_payload)
    assert create_resp.status_code == status.HTTP_201_CREATED
    ticket = create_resp.json()

    assert ticket["conversation_id"] == conv_id
    assert ticket["status"] == "open"
    assert ticket["priority"] == "high"
    assert ticket["assigned_team"] == "l2_devops"

    # List tickets
    list_resp = client.get("/api/v1/tickets?priority=high")
    assert list_resp.status_code == status.HTTP_200_OK
    tickets = list_resp.json()["items"]
    assert any(t["id"] == ticket["id"] for t in tickets)

    # Get single ticket
    single_resp = client.get(f"/api/v1/tickets/{ticket['id']}")
    assert single_resp.status_code == status.HTTP_200_OK
    assert single_resp.json()["id"] == ticket["id"]


def test_simulated_action_authorization_and_approval(client):
    conv = client.post("/api/v1/conversations", json={"product_area": "api_gateway"}).json()
    conv_id = conv["id"]

    action_payload = {
        "action_key": "mock_config_correction",
        "parameters": {"target_service": "api_gateway"},
        "confirmed_approval": False,  # Missing approval
    }

    # 1. Consequential action without confirmation should be rejected with 400
    fail_resp = client.post(f"/api/v1/cases/{conv_id}/actions", json=action_payload)
    assert fail_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "confirmed_approval" in fail_resp.json()["detail"]

    # 2. Consequential action with invalid role should be rejected with 403
    unauth_resp = client.post(
        f"/api/v1/cases/{conv_id}/actions",
        json={**action_payload, "confirmed_approval": True},
        headers={"X-Actor-Role": "unauthorized_role"},
    )
    assert unauth_resp.status_code == status.HTTP_403_FORBIDDEN

    # 3. Authorized execution with approval confirmation succeeds
    success_resp = client.post(
        f"/api/v1/cases/{conv_id}/actions",
        json={**action_payload, "confirmed_approval": True},
        headers={"X-Actor-Role": "agent", "X-Actor-Name": "lead_support_agent"},
    )
    assert success_resp.status_code == status.HTTP_200_OK
    result_data = success_resp.json()
    assert result_data["status"] == "success"
    assert "execution_id" in result_data
    assert "audit_event_id" in result_data
