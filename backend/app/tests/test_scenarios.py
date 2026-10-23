"""
Comprehensive End-to-End Tests for the Four Core Troubleshooting Scenarios
"""
import pytest
from fastapi import status


def test_scenario_1_api_authentication_resolves(client):
    """
    Scenario 1: API authentication failure that resolves.
    - 401 error after key rotation
    - Diagnostic identifies stale gateway cache
    - Action plan generated & approved
    - Simulated config correction executed
    - Verification passes and conversation status becomes resolved
    """
    # 1. Customer initiates conversation
    conv_resp = client.post(
        "/api/v1/conversations",
        json={"product_area": "api_gateway", "environment": "production"},
    )
    assert conv_resp.status_code == status.HTTP_201_CREATED
    conv_id = conv_resp.json()["id"]

    # 2. Customer describes 401 key rotation issue
    msg_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Our API requests are failing with HTTP 401 Unauthorized after key rotation yesterday."},
    )
    assert msg_resp.status_code == status.HTTP_200_OK
    msg_data = msg_resp.json()
    assert len(msg_data["citations"]) > 0
    assert "401" in msg_data["assistant_message"]["content"]

    # 3. Start diagnostic workflow
    diag_start = client.post(
        f"/api/v1/conversations/{conv_id}/diagnostics",
        json={"workflow_key": "auth_401_key_rotation"},
    )
    assert diag_start.status_code == status.HTTP_201_CREATED
    run = diag_start.json()
    run_id = run["id"]
    step_1 = run["steps"][0]
    assert step_1["step_key"] == "check_api_credentials"

    # 4. Step 1 outcome recorded as failed (stale cache detected)
    step1_resp = client.post(
        f"/api/v1/diagnostics/{run_id}/steps/{step_1['id']}/result",
        json={
            "result": "failed",
            "evidence": {"gateway_cached_key": "v1_deprecated", "vault_key": "v2_2026"},
        },
    )
    assert step1_resp.status_code == status.HTTP_200_OK
    run_after_step1 = step1_resp.json()
    assert run_after_step1["current_step"] == "recommend_cache_invalidation"

    # 5. Generate action plan
    plan_resp = client.post(f"/api/v1/conversations/{conv_id}/action-plan")
    assert plan_resp.status_code == status.HTTP_201_CREATED
    plan = plan_resp.json()
    assert plan["status"] == "draft"

    # 6. Approve action plan
    approve_resp = client.post(f"/api/v1/action-plans/{plan['id']}/approve")
    assert approve_resp.status_code == status.HTTP_200_OK
    assert approve_resp.json()["status"] == "approved"

    # 7. Execute simulated configuration correction
    action_resp = client.post(
        f"/api/v1/cases/{conv_id}/actions",
        json={
            "action_key": "mock_config_correction",
            "parameters": {"target_service": "api_gateway"},
            "confirmed_approval": True,
        },
        headers={"X-Actor-Role": "agent"},
    )
    assert action_resp.status_code == status.HTTP_200_OK
    assert action_resp.json()["status"] == "success"

    # 8. Record step 2 result (cache invalidation recommended and done) -> advance to verification
    step_2 = run_after_step1["steps"][1]
    step2_resp = client.post(
        f"/api/v1/diagnostics/{run_id}/steps/{step_2['id']}/result",
        json={"result": "passed"},
    )
    assert step2_resp.status_code == status.HTTP_200_OK
    run_after_step2 = step2_resp.json()
    assert run_after_step2["current_step"] == "verify_config_sync"

    # 9. Verification step executed and reports passed
    step_3 = run_after_step2["steps"][2]
    step3_resp = client.post(
        f"/api/v1/diagnostics/{run_id}/steps/{step_3['id']}/result",
        json={"result": "passed", "evidence": {"sync_confirmed": True}},
    )
    assert step3_resp.status_code == status.HTTP_200_OK
    final_run = step3_resp.json()
    assert final_run["status"] == "passed"

    # 10. Verify conversation is resolved
    conv_check = client.get(f"/api/v1/conversations/{conv_id}").json()
    assert conv_check["status"] == "resolved"


def test_scenario_2_crm_integration_escalates(client):
    """
    Scenario 2: CRM integration timeout that escalates.
    - 10,000ms timeouts on webhook
    - Diagnostic probe fails and retries
    - Sustained failure causes escalation state
    - Support ticket automatically dispatched to Tier 2
    """
    conv = client.post(
        "/api/v1/conversations",
        json={"product_area": "crm_sync", "environment": "production"},
    ).json()
    conv_id = conv["id"]

    # Customer message
    client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Outbound CRM webhook sync is timing out after 10000ms repeatedly."},
    )

    # Start diagnostic
    diag_start = client.post(
        f"/api/v1/conversations/{conv_id}/diagnostics",
        json={"workflow_key": "crm_sync_timeout"},
    ).json()
    run_id = diag_start["id"]
    step_1 = diag_start["steps"][0]

    # Initial probe fails due to timeout
    step1_resp = client.post(
        f"/api/v1/diagnostics/{run_id}/steps/{step_1['id']}/result",
        json={"result": "failed", "evidence": {"timeout": "10000ms"}},
    ).json()
    assert step1_resp["current_step"] == "retry_webhook_probe"

    # Retry probe also fails
    step_2 = step1_resp["steps"][1]
    step2_resp = client.post(
        f"/api/v1/diagnostics/{run_id}/steps/{step_2['id']}/result",
        json={"result": "failed", "evidence": {"packet_loss": 100}},
    ).json()

    # Reached terminal escalation status
    assert step2_resp["status"] == "escalated"

    # Create Tier-2 escalation ticket
    ticket_resp = client.post(
        f"/api/v1/conversations/{conv_id}/tickets",
        json={
            "summary": "External CRM partner webhook persistent timeout",
            "priority": "high",
            "assigned_team": "l2_devops",
        },
    )
    assert ticket_resp.status_code == status.HTTP_201_CREATED
    assert ticket_resp.json()["assigned_team"] == "l2_devops"

    # Conversation status must reflect escalation
    conv_status = client.get(f"/api/v1/conversations/{conv_id}").json()
    assert conv_status["status"] == "escalated"


def test_scenario_3_ambiguous_complaint_clarification(client):
    """
    Scenario 3: Ambiguous complaint requiring clarification.
    - Customer says: "System is slow and not working"
    - Severity remains low, missing information identified
    - Diagnostic step is inconclusive
    - System asks for clarification without false escalation
    """
    conv = client.post(
        "/api/v1/conversations",
        json={"product_area": "general", "environment": "production"},
    ).json()
    conv_id = conv["id"]

    msg_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "The system is slow and not working."},
    ).json()

    # Assistant asks for specific details
    reply = msg_resp["assistant_message"]["content"]
    assert "?" in reply or "which" in reply.lower() or "clarify" in reply.lower() or "endpoint" in reply.lower()

    # Analysis confirms missing information and low severity
    analysis_resp = client.post(f"/api/v1/conversations/{conv_id}/analyze").json()
    assert analysis_resp["severity_score"] < 40.0
    assert analysis_resp["escalation_required"] is False
    assert len(analysis_resp["missing_information"]) > 0

    # Diagnostic step inconclusive
    diag = client.post(
        f"/api/v1/conversations/{conv_id}/diagnostics",
        json={"workflow_key": "generic_diagnostic"},
    ).json()
    step_1 = diag["steps"][0]

    step_res = client.post(
        f"/api/v1/diagnostics/{diag['id']}/steps/{step_1['id']}/result",
        json={"result": "inconclusive", "evidence": {"missing": "endpoint URL"}},
    ).json()

    # Remains non-escalated awaiting customer input
    assert step_res["status"] in ("inconclusive", "running", "completed")
    conv_check = client.get(f"/api/v1/conversations/{conv_id}").json()
    assert conv_check["status"] != "escalated"


def test_scenario_4_widespread_outage_priority_escalation(client):
    """
    Scenario 4: Suspected widespread outage requiring priority escalation.
    - HTTP 500 error flood affecting all users in region
    - Severity score is critical (>= 85)
    - Mandatory escalation policy triggers immediate escalation
    - Database pool exhaustion confirmed
    - Ticket created for L3 engineering
    """
    conv = client.post(
        "/api/v1/conversations",
        json={"product_area": "platform_infrastructure", "environment": "production"},
    ).json()
    conv_id = conv["id"]

    # Critical report
    client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Major outage! All users in US-East are receiving HTTP 500 errors across all services!"},
    )

    # Recompute analysis
    analysis = client.post(f"/api/v1/conversations/{conv_id}/analyze").json()
    assert analysis["severity_score"] >= 85.0
    assert analysis["escalation_required"] is True

    # Conversation automatically shifted to escalated
    conv_check = client.get(f"/api/v1/conversations/{conv_id}").json()
    assert conv_check["status"] == "escalated"

    # Start platform triage
    diag = client.post(
        f"/api/v1/conversations/{conv_id}/diagnostics",
        json={"workflow_key": "platform_outage_triage"},
    ).json()
    step_1 = diag["steps"][0]

    # Database pool saturation verified
    step_res = client.post(
        f"/api/v1/diagnostics/{diag['id']}/steps/{step_1['id']}/result",
        json={"result": "failed", "evidence": {"active_connections": 500, "max": 500}},
    ).json()

    assert step_res["status"] == "escalated"

    # Create emergency ticket
    ticket = client.post(
        f"/api/v1/conversations/{conv_id}/tickets",
        json={
            "summary": "CRITICAL OUTAGE: Regional 500 spike in US-East due to DB pool exhaustion",
            "priority": "critical",
            "assigned_team": "l3_engineering",
        },
    ).json()
    assert ticket["priority"] == "critical"
    assert ticket["assigned_team"] == "l3_engineering"
