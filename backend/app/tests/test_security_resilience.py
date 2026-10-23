"""
Tests for Security, Rate Limiting, Audit Masking, and Resilience
"""
import io
import pytest
from fastapi import status
from app.policies.safety_policy import redact_sensitive_data, sanitize_audit_payload
from app.core.config import settings


def test_sensitive_data_masking():
    raw_text = "Here is my bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and apiKey: secret-api-key-99887766554433 and password: supersecretpassword123 with otp: 123456"
    masked = redact_sensitive_data(raw_text)

    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in masked
    assert "secret-api-key-99887766554433" not in masked
    assert "supersecretpassword123" not in masked
    assert "123456" not in masked
    assert "[REDACTED_TOKEN]" in masked
    assert "[REDACTED_PASSWORD]" in masked
    assert "[REDACTED_OTP]" in masked


def test_sanitize_audit_payload():
    payload = {
        "user": "alice",
        "api_key": "raw_sensitive_key_12345",
        "secret_token": "secret_abc_xyz",
        "nested": {
            "password": "my_db_password",
            "safe_field": "nominal",
        },
        "log_array": [
            "Normal log entry",
            "Authorization: bearer sk-11223344556677889900",
        ],
    }
    clean = sanitize_audit_payload(payload)
    assert clean["api_key"] == "[REDACTED]"
    assert clean["secret_token"] == "[REDACTED]"
    assert clean["nested"]["password"] == "[REDACTED]"
    assert clean["nested"]["safe_field"] == "nominal"
    assert "sk-11223344556677889900" not in clean["log_array"][1]
    assert "[REDACTED_TOKEN]" in clean["log_array"][1]


def test_rate_limiting_middleware(client):
    from app.main import _request_counts
    _request_counts.clear()

    # Temporarily set lower rate limit for quick testing
    original_limit = settings.RATE_LIMIT_PER_MINUTE
    settings.RATE_LIMIT_PER_MINUTE = 5
    try:
        # Send 5 requests
        for _ in range(5):
            r = client.get("/api/v1/conversations")
            assert r.status_code == status.HTTP_200_OK

        # 6th request must trigger HTTP 429
        blocked_r = client.get("/api/v1/conversations")
        assert blocked_r.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert blocked_r.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
    finally:
        settings.RATE_LIMIT_PER_MINUTE = original_limit


def test_file_upload_size_limit(client):
    # Create file that exceeds 10MB limit
    oversized_content = b"X" * (settings.MAX_UPLOAD_SIZE_BYTES + 1024)
    files = {"file": ("huge_runbook.md", io.BytesIO(oversized_content), "text/markdown")}

    resp = client.post(
        "/api/v1/knowledge/documents",
        files=files,
        data={"title": "Too Large Document"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "exceeds" in resp.json()["detail"].lower()
