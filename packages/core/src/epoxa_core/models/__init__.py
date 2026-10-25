"""
Relational models package for Epoxa.
"""

from epoxa_core.models.base import Base, POSTGRES_NAMING_CONVENTION, TimestampMixin, UUIDMixin, metadata
from epoxa_core.models.entities import (
    Appointment,
    AuditLog,
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

__all__ = [
    "Base",
    "metadata",
    "POSTGRES_NAMING_CONVENTION",
    "UUIDMixin",
    "TimestampMixin",
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
]
