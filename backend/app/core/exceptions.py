from typing import Optional, Any, Dict
from fastapi import HTTPException, status

class EpoxaException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class AuthenticationError(EpoxaException):
    def __init__(self, message: str = "Invalid or expired authentication credentials", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED, details=details)

class AuthorizationError(EpoxaException):
    def __init__(self, message: str = "Access denied: insufficient organization privileges", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, details=details)

class ResourceNotFoundError(EpoxaException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": str(identifier)}
        )

class ConflictError(EpoxaException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT, details=details)

class ValidationError(EpoxaException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)

class ProviderError(EpoxaException):
    def __init__(self, provider: str, message: str):
        super().__init__(
            message=f"External voice/AI service error ({provider})",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"provider": provider, "error_summary": message}
        )
