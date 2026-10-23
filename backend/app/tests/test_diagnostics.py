"""
Tests for Deterministic Diagnostic Workflow Engine
"""
import pytest
from fastapi import status


def test_start_and_advance_diagnostic_workflow(client):
    conv = client.post("/api/v1/conversations", json={"product_area": "api_gateway"}).json()
    conv_id = conv["id"]

    # Start workflow
    start_resp = client.post(
        f"/api/v1/conversations/{conv_id}/diagnostics",
        json={"workflow_key": "auth_401_key_rotation"},
    )
    assert start_resp.status_code == status.HTTP_201_CREATED
    run = start_resp.json()

    assert run["conversation_id"] == conv_id
    assert run["workflow_key"] == "auth_401_key_rotation"
    assert run["status"] == "running"
    assert len(run["steps"]) > 0

    step_1 = run["steps"][0]
    assert step_1["step_key"] == "check_api_credentials"

    # Step 1 was executed and reported failed (cache mismatch)
    # Advance state machine by recording the result: "failed"
    step_resp = client.post(
        f"/api/v1/diagnostics/{run['id']}/steps/{step_1['id']}/result",
        json={
            "result": "failed",
            "evidence": {"cached_key_version": "v1", "vault_key_version": "v2"},
        },
    )
    assert step_resp.status_code == status.HTTP_200_OK
    run_after_step1 = step_resp.json()

    # Verify state machine branched to "recommend_cache_invalidation"
    assert run_after_step1["current_step"] == "recommend_cache_invalidation"
    assert len(run_after_step1["steps"]) == 2


def test_duplicate_step_prevention(client):
    conv = client.post("/api/v1/conversations", json={"product_area": "api_gateway"}).json()
    conv_id = conv["id"]

    start_resp = client.post(
        f"/api/v1/conversations/{conv_id}/diagnostics",
        json={"workflow_key": "auth_401_key_rotation"},
    )
    run = start_resp.json()
    step_1 = run["steps"][0]

    # Record result once
    client.post(
        f"/api/v1/diagnostics/{run['id']}/steps/{step_1['id']}/result",
        json={"result": "passed"},
    )

    # Attempt to record result for the EXACT same step AGAIN
    dup_resp = client.post(
        f"/api/v1/diagnostics/{run['id']}/steps/{step_1['id']}/result",
        json={"result": "passed"},
    )
    # Must reject with 400 Bad Request
    assert dup_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been recorded" in dup_resp.json()["detail"].lower()
