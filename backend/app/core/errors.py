"""
Standardized Application Exceptions
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class PSAIException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = "GENERIC_ERROR",
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra = extra or {}


class NotFoundException(PSAIException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with identifier '{identifier}' was not found.",
            error_code="RESOURCE_NOT_FOUND",
            extra={"resource": resource, "identifier": str(identifier)},
        )


class ConflictException(PSAIException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT",
        )


class BadRequestException(PSAIException):
    def __init__(self, detail: str, error_code: str = "BAD_REQUEST"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code,
        )


class UnauthorizedException(PSAIException):
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED",
        )


class ForbiddenException(PSAIException):
    def __init__(self, detail: str = "Action not permitted"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN",
        )


class ProviderException(PSAIException):
    def __init__(self, provider: str, detail: str):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider '{provider}' error: {detail}",
            error_code="PROVIDER_ERROR",
            extra={"provider": provider},
        )
