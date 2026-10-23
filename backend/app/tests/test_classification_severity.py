"""
Tests for Classification and Deterministic Severity Scoring Policy
"""
import pytest
from fastapi import status
from app.policies.escalation_policy import EscalationPolicy


def test_deterministic_severity_formula():
    """
    Test 35% impact, 25% urgency, 25% scope, 15% SLA calculation.
    """
    breakdown = EscalationPolicy.calculate_severity(
        impact="moderate",  # 50 * 0.35 = 17.5
        urgency="medium",   # 45 * 0.25 = 11.25
        scope="single_user",# 15 * 0.25 = 3.75
        sla_risk="safe",    # 10 * 0.15 = 1.5
    )
    # Expected: 17.5 + 11.25 + 3.75 + 1.5 = 34.0
    assert breakdown.final_score == 34.0
    assert breakdown.severity_label == "medium"
    assert breakdown.escalation_decision is False


def test_critical_mandatory_escalation_rules():
    # 1. Security incident must trigger mandatory escalation
    sec_breakdown = EscalationPolicy.calculate_severity(
        impact="minor",
        urgency="low",
        scope="single_user",
        is_security_incident=True,
    )
    assert sec_breakdown.escalation_decision is True
    assert sec_breakdown.final_score >= 90.0
    assert sec_breakdown.severity_label == "critical"
    assert "security incident" in sec_breakdown.escalation_reason.lower()

    # 2. Confirmed widespread outage must trigger mandatory escalation
    outage_breakdown = EscalationPolicy.calculate_severity(
        impact="complete_outage",
        urgency="critical",
        scope="widespread",
        is_widespread_outage=True,
    )
    assert outage_breakdown.escalation_decision is True
    assert outage_breakdown.final_score >= 88.0
    assert outage_breakdown.severity_label == "critical"
    assert "widespread" in outage_breakdown.escalation_reason.lower()


def test_analyze_endpoint(client):
    conv = client.post("/api/v1/conversations", json={"product_area": "api_gateway"}).json()
    conv_id = conv["id"]

    # Post message
    client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "All requests to API gateway are failing with HTTP 401 after key rotation."},
    )

    # Recompute analysis endpoint
    resp = client.post(f"/api/v1/conversations/{conv_id}/analyze")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert data["conversation_id"] == conv_id
    assert "severity_score" in data
    assert "hypotheses" in data
    assert len(data["hypotheses"]) <= 3
    for hyp in data["hypotheses"]:
        assert "rank" in hyp
        assert "probability" in hyp
        assert "best_next_diagnostic_test" in hyp
