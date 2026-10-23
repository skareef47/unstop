"""
Safety Policy: Sensitive Data Masking and Input Sanitization
"""
import re
from typing import Dict, Any


SECRET_REGEXES = [
    # API Keys / Bearer Tokens / Passwords
    (r"(bearer\s+)([A-Za-z0-9_\-\.]{15,})", r"\1[REDACTED_TOKEN]"),
    (r"(api[_\-\s]?key[\s:=]+)([A-Za-z0-9_\-]{15,})", r"\1[REDACTED_API_KEY]"),
    (r"(password[\s:=]+)([^\s,;]{4,})", r"\1[REDACTED_PASSWORD]"),
    (r"(secret[\s:=]+)([^\s,;]{8,})", r"\1[REDACTED_SECRET]"),
    (r"(\botp[\s:=]+)([0-9]{4,8})", r"\1[REDACTED_OTP]"),
]


def redact_sensitive_data(text: str) -> str:
    """Mask credentials, passwords, tokens, and OTPs from text logs."""
    if not text:
        return text
    sanitized = text
    for pattern, repl in SECRET_REGEXES:
        sanitized = re.sub(pattern, repl, sanitized, flags=re.IGNORECASE)
    return sanitized


def sanitize_audit_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively scrub secrets from audit event payloads."""
    clean = {}
    for k, v in payload.items():
        if any(secret_word in k.lower() for secret_word in ["password", "secret", "token", "key", "otp"]):
            clean[k] = "[REDACTED]"
        elif isinstance(v, str):
            clean[k] = redact_sensitive_data(v)
        elif isinstance(v, dict):
            clean[k] = sanitize_audit_payload(v)
        elif isinstance(v, list):
            clean[k] = [
                sanitize_audit_payload(item) if isinstance(item, dict)
                else redact_sensitive_data(item) if isinstance(item, str)
                else item
                for item in v
            ]
        else:
            clean[k] = v
    return clean
