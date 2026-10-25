"""
Domain and application exceptions for the Epoxa core library.
All exceptions support mapping into RFC 7807 Problem Details for HTTP APIs.
"""

from typing import Any, Dict, Optional


class EpoxaException(Exception):
    """Base domain exception for all Epoxa errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        detail: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail or message
        self.extra = extra or {}


class EntityNotFoundError(EpoxaException):
    """Raised when a requested resource is not found."""

    def __init__(self, entity: str, entity_id: Any) -> None:
        super().__init__(
            message=f"{entity} with identifier '{entity_id}' was not found.",
            code="ENTITY_NOT_FOUND",
            status_code=404,
            detail=f"{entity} not found",
            extra={"entity": entity, "entity_id": str(entity_id)},
        )


class ConflictError(EpoxaException):
    """Raised when an operation conflicts with existing state (e.g. slot already booked)."""

    def __init__(self, message: str, reason: str = "conflict") -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            detail=message,
            extra={"reason": reason},
        )


class ValidationError(EpoxaException):
    """Raised when domain business rules or input formats are violated."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            detail=message,
            extra={"field": field} if field else {},
        )


class UnauthorizedError(EpoxaException):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
            detail=message,
        )


class ForbiddenError(EpoxaException):
    """Raised when an authenticated user lacks permission for the requested resource."""

    def __init__(self, message: str = "Access to this resource is forbidden.") -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            detail=message,
        )


class AbuseLimitExceededError(EpoxaException):
    """Raised when rate limits, concurrent call caps, or duration limits are breached."""

    def __init__(self, message: str, limit_type: str = "rate_limit") -> None:
        super().__init__(
            message=message,
            code="LIMIT_EXCEEDED",
            status_code=429,
            detail=message,
            extra={"limit_type": limit_type},
        )


class HandoffStateError(EpoxaException):
    """Raised when an invalid handoff transition is attempted."""

    def __init__(self, current_state: str, attempted_action: str) -> None:
        super().__init__(
            message=f"Cannot perform '{attempted_action}' while call is in '{current_state}' state.",
            code="INVALID_HANDOFF_STATE",
            status_code=409,
            detail=f"Invalid transition from {current_state}",
            extra={"current_state": current_state, "attempted_action": attempted_action},
        )


class SlotUnavailableError(ConflictError):
    """Raised when an appointment slot is already taken."""

    def __init__(self, message: str = "The requested appointment slot is already booked.") -> None:
        super().__init__(message=message, reason="slot_unavailable")


class BusinessHoursViolationError(ValidationError):
    """Raised when an appointment is scheduled outside operating business hours."""

    def __init__(self, message: str = "Appointments may only be booked during business hours (Mon-Sat 9 AM to 6 PM IST).") -> None:
        super().__init__(message=message, field="scheduled_at")


class PastAppointmentError(ValidationError):
    """Raised when an appointment is scheduled in the past."""

    def __init__(self, message: str = "Appointments cannot be booked in the past.") -> None:
        super().__init__(message=message, field="scheduled_at")
