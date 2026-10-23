"""
Security and Authentication Utilities
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
import bcrypt
from fastapi import Header, HTTPException, status
from app.core.config import settings


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_admin_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> bool:
    """Check administrative API key for protected actions."""
    if not x_api_key or x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing administrative API Key",
        )
    return True


# Prompt Injection Defense Filter
# Detect common prompt override attempts: "ignore previous instructions", "system override", "jailbreak", etc.
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s*:\s*you\s+are\s+now",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"dan\s+mode|jailbreak",
    r"reveal\s+(system\s+prompt|all\s+rules|api\s+key|secret)",
    r"output\s+the\s+system\s+prompt",
]


def detect_prompt_injection(text: str) -> bool:
    """Returns True if the text matches known adversarial prompt injection patterns."""
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def sanitize_input(text: str) -> str:
    """Strip dangerous control characters or null bytes."""
    if not text:
        return ""
    # Strip null bytes and non-printable control chars except standard whitespace
    sanitized = "".join(ch for ch in text if ch == "\n" or ch == "\r" or ch == "\t" or ord(ch) >= 32)
    return sanitized.strip()
