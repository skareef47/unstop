"""
Tests for Conversation Lifecycle and Persistence
"""
import pytest
from fastapi import status


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] in ("online", "degraded")
    assert data["product"] == "PSAI"

    # API v1 health
    v1_resp = client.get("/api/v1/health")
    assert v1_resp.status_code == status.HTTP_200_OK


def test_create_conversation(client):
    payload = {
        "product_area": "api_gateway",
        "environment": "production",
    }
    response = client.post("/api/v1/conversations", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert data["status"] == "active"
    assert data["product_area"] == "api_gateway"
    assert data["environment"] == "production"


def test_list_and_get_conversation(client):
    # Create 2 conversations
    c1 = client.post("/api/v1/conversations", json={"product_area": "auth_service", "environment": "staging"}).json()
    c2 = client.post("/api/v1/conversations", json={"product_area": "crm_sync", "environment": "production"}).json()

    # List
    list_resp = client.get("/api/v1/conversations")
    assert list_resp.status_code == status.HTTP_200_OK
    list_data = list_resp.json()
    assert list_data["total"] >= 2
    ids = [item["id"] for item in list_data["items"]]
    assert c1["id"] in ids
    assert c2["id"] in ids

    # Filter by product_area
    filter_resp = client.get("/api/v1/conversations?product_area=auth_service")
    assert filter_resp.status_code == status.HTTP_200_OK
    filter_data = filter_resp.json()
    assert all(item["product_area"] == "auth_service" for item in filter_data["items"])

    # Get single
    get_resp = client.get(f"/api/v1/conversations/{c1['id']}")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["id"] == c1["id"]

    # 404 for unknown
    not_found = client.get("/api/v1/conversations/nonexistent-uuid-1234")
    assert not_found.status_code == status.HTTP_404_NOT_FOUND
