"""
epoxa_core: Shared domain models, database abstractions, repositories, and business services.
"""

from epoxa_core.database import check_database_health, get_db_session, get_engine, get_session_factory
from epoxa_core.exceptions import (
    AbuseLimitExceededError,
    ConflictError,
    EntityNotFoundError,
    EpoxaException,
    ForbiddenError,
    HandoffStateError,
    UnauthorizedError,
    ValidationError,
)
from epoxa_core.logging import get_logger, setup_logging
from epoxa_core.models import (
    Appointment,
    AuditLog,
    Base,
    CallSession,
    CallTranscript,
    Customer,
    HandoffEvent,
    KBChunk,
    KBDocument,
    LatencyLog,
    Membership,
    Organization,
    Profile,
    Ticket,
)
from epoxa_core.settings import settings
from epoxa_core.uow import UnitOfWork

__all__ = [
    "settings",
    "setup_logging",
    "get_logger",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "check_database_health",
    "UnitOfWork",
    "Base",
    "Organization",
    "Profile",
    "Membership",
    "Customer",
    "CallSession",
    "CallTranscript",
    "LatencyLog",
    "HandoffEvent",
    "Appointment",
    "Ticket",
    "AuditLog",
    "KBDocument",
    "KBChunk",
    "EpoxaException",
    "EntityNotFoundError",
    "ConflictError",
    "ValidationError",
    "UnauthorizedError",
    "ForbiddenError",
    "AbuseLimitExceededError",
    "HandoffStateError",
]
