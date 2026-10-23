"""
Tests for Knowledge Ingestion, Vector Search, and Deletion
"""
import io
import pytest
from fastapi import status


def test_upload_document_and_search(client):
    content = b"""# Database Failover Protocol [OPS-DB-02]

## Overview
Procedures to migrate client traffic to secondary replicas during database cluster degradation.

## Connection Pool Saturation
When connection pool saturation exceeds 90%, initiate pool flush and failover.
"""
    files = {"file": ("database_failover.md", io.BytesIO(content), "text/markdown")}
    upload_resp = client.post(
        "/api/v1/knowledge/documents",
        files=files,
        data={"title": "Database Failover Protocol", "version": "1.0"},
    )
    assert upload_resp.status_code == status.HTTP_201_CREATED
    doc = upload_resp.json()
    assert doc["title"] == "Database Failover Protocol"
    assert doc["chunk_count"] > 0
    doc_id = doc["id"]

    # Semantic Search
    search_resp = client.get("/api/v1/knowledge/search?q=connection+pool+saturation")
    assert search_resp.status_code == status.HTTP_200_OK
    search_data = search_resp.json()
    assert len(search_data["results"]) > 0

    # Verify score and content
    top_match = search_data["results"][0]
    assert "saturation" in top_match["content"].lower() or "database" in top_match["content"].lower()
    assert top_match["score"] > 0.0

    # Delete Document
    del_resp = client.delete(f"/api/v1/knowledge/documents/{doc_id}")
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    # Search again; deleted doc chunks must not be returned
    search_after = client.get("/api/v1/knowledge/search?q=database+failover+protocol")
    matched_ids = [r["document_id"] for r in search_after.json()["results"]]
    assert doc_id not in matched_ids
