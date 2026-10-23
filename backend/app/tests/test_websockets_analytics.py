"""
Tests for WebSockets and Analytics Endpoints
"""
import pytest
from fastapi import status


def test_analytics_endpoints(client):
    # Create conversation and ticket
    conv = client.post("/api/v1/conversations", json={"product_area": "api_gateway"}).json()
    client.post(
        f"/api/v1/conversations/{conv['id']}/tickets",
        json={"summary": "Sample incident ticket", "priority": "high"},
    )

    # 1. Overview
    overview_resp = client.get("/api/v1/analytics/overview")
    assert overview_resp.status_code == status.HTTP_200_OK
    overview = overview_resp.json()
    assert "total_conversations" in overview
    assert "open_tickets" in overview
    assert overview["total_conversations"] >= 1
    assert overview["open_tickets"] >= 1

    # 2. Incidents
    incidents_resp = client.get("/api/v1/analytics/incidents")
    assert incidents_resp.status_code == status.HTTP_200_OK
    incidents = incidents_resp.json()
    assert "trends" in incidents
    assert len(incidents["trends"]) == 7  # 7-day trend

    # 3. Resolution
    resolution_resp = client.get("/api/v1/analytics/resolution")
    assert resolution_resp.status_code == status.HTTP_200_OK
    res = resolution_resp.json()
    assert "average_steps_to_resolution" in res
    assert "auto_resolved_pct" in res


def test_websocket_connection_and_heartbeat(client):
    with client.websocket_connect("/api/v1/ws/dashboard") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"
