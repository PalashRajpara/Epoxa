"""
Complete domain relational models for Epoxa conforming to PostgreSQL 15+ & Supabase specifications.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from epoxa_core.models.base import Base, TimestampMixin, UUIDMixin

try:
    from pgvector.sqlalchemy import Vector
    _VECTOR_AVAILABLE = True
except ImportError:
    _VECTOR_AVAILABLE = False


# =============================================================================
# 1. ORGANIZATIONS (Multi-Tenant Foundation)
# =============================================================================

class Organization(Base, UUIDMixin, TimestampMixin):
    """Represents a tenant organization (e.g., Epoxcel)."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {
            "business_hours": {"start": 9, "end": 18, "days": [1, 2, 3, 4, 5, 6]},
            "default_phone_region": "IN",
            "retention_days": {"transcripts": 90, "latency_logs": 30},
        },
        nullable=False,
    )

    # Relationships
    memberships: Mapped[List["Membership"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    customers: Mapped[List["Customer"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    call_sessions: Mapped[List["CallSession"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    tickets: Mapped[List["Ticket"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


# =============================================================================
# 2. PROFILES (Linked to Supabase auth.users)
# =============================================================================

class Profile(Base, TimestampMixin):
    """User profile for supervisors and administrators, keyed to Supabase auth.users(id)."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    memberships: Mapped[List["Membership"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


# =============================================================================
# 3. MEMBERSHIPS (RBAC per Tenant)
# =============================================================================

class Membership(Base, UUIDMixin, TimestampMixin):
    """Links profiles to organizations with assigned role."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "profile_id", name="uq_memberships_org_profile"),
        CheckConstraint("role IN ('owner', 'admin', 'supervisor')", name="ck_memberships_role"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), default="supervisor", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    profile: Mapped["Profile"] = relationship(back_populates="memberships")


# =============================================================================
# 4. CUSTOMERS (Voice Caller Identity)
# =============================================================================

class Customer(Base, UUIDMixin, TimestampMixin):
    """Verified caller profiles identified by E.164 phone number."""

    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("tier IN ('Basic', 'Standard', 'Premium', 'VIP')", name="ck_customers_tier"),
        CheckConstraint("phone_e164 ~ '^\\+[1-9][0-9]{7,14}$'", name="ck_customers_phone_e164"),
        Index("idx_customers_org_phone", "organization_id", "phone_e164", unique=True, postgresql_where="anonymized_at IS NULL"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tier: Mapped[str] = mapped_column(String(20), default="Standard", nullable=False)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    anonymized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="customers")
    call_sessions: Mapped[List["CallSession"]] = relationship(back_populates="customer")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="customer")
    tickets: Mapped[List["Ticket"]] = relationship(back_populates="customer")


# =============================================================================
# 5. CALL SESSIONS (Voice Call State & Telemetry)
# =============================================================================

class CallSession(Base, UUIDMixin, TimestampMixin):
    """Tracks each WebRTC voice call session from inception to termination."""

    __tablename__ = "call_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'escalated', 'completed', 'dropped', 'timeout', 'error')",
            name="ck_call_sessions_status",
        ),
        CheckConstraint(
            "handoff_state IN ('ai', 'human_pending', 'human_active')",
            name="ck_call_sessions_handoff_state",
        ),
        CheckConstraint("duration_seconds >= 0", name="ck_call_sessions_duration_nonneg"),
        Index("idx_call_sessions_org_status_started", "organization_id", "status", "started_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    livekit_room_sid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    participant_identity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    participant_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    handoff_state: Mapped[str] = mapped_column(String(20), default="ai", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default="NOW()",
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    end_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_version: Mapped[str] = mapped_column(String(30), default="1.0.0", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(30), default="v1", nullable=False)
    llm_model: Mapped[str] = mapped_column(String(60), default="llama-3.1-8b-instant", nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="call_sessions")
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="call_sessions")
    transcripts: Mapped[List["CallTranscript"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    latency_logs: Mapped[List["LatencyLog"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    handoff_events: Mapped[List["HandoffEvent"]] = relationship(back_populates="session", cascade="all, delete-orphan")


# =============================================================================
# 6. CALL TRANSCRIPTS (Ordered Utterance Log)
# =============================================================================

class CallTranscript(Base):
    """Discrete utterance transcript turn."""

    __tablename__ = "call_transcripts"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_transcripts_session_sequence"),
        CheckConstraint("role IN ('user', 'agent', 'supervisor')", name="ck_transcripts_role"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    speaker_identity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    content: Mapped[str] = mapped_column(String(4000), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    spoken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default="NOW()",
        nullable=False,
    )
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    session: Mapped["CallSession"] = relationship(back_populates="transcripts")


# =============================================================================
# 7. LATENCY LOGS (Step Turnaround Timing)
# =============================================================================

class LatencyLog(Base):
    """High-precision latency telemetry per step."""

    __tablename__ = "latency_logs"
    __table_args__ = (
        CheckConstraint("step IN ('stt', 'llm', 'tts', 'e2e')", name="ck_latency_step"),
        CheckConstraint("duration_ms >= 0", name="ck_latency_duration_nonneg"),
        Index("idx_latency_session_id", "session_id"),
        Index("idx_latency_logged_at", "logged_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    step: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_ms: Mapped[float] = mapped_column(nullable=False)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default="NOW()",
        nullable=False,
    )

    # Relationships
    session: Mapped["CallSession"] = relationship(back_populates="latency_logs")


# =============================================================================
# 8. HANDOFF EVENTS (Append-Only Supervisor Takeover Audit)
# =============================================================================

class HandoffEvent(Base, UUIDMixin):
    """Append-only log of supervisor takeovers and returns."""

    __tablename__ = "handoff_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('takeover_requested', 'takeover', 'return_to_ai', 'disconnect')",
            name="ck_handoff_action",
        ),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default="NOW()",
        nullable=False,
    )

    # Relationships
    session: Mapped["CallSession"] = relationship(back_populates="handoff_events")


# =============================================================================
# 9. APPOINTMENTS (Persisted Customer Bookings)
# =============================================================================

class Appointment(Base, UUIDMixin, TimestampMixin):
    """Persisted calendar booking slots."""

    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('confirmed', 'cancelled', 'completed', 'rescheduled', 'no_show')",
            name="ck_appointments_status",
        ),
        UniqueConstraint("organization_id", "confirmation_code", name="uq_appointments_org_code"),
        Index("idx_appointments_org_slot_confirmed", "organization_id", "scheduled_at", unique=True, postgresql_where="status = 'confirmed'"),
        Index("idx_appointments_customer", "customer_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    confirmation_code: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="appointments")
    customer: Mapped["Customer"] = relationship(back_populates="appointments")


# =============================================================================
# 10. TICKETS (Support Grievances & Escalations)
# =============================================================================

class Ticket(Base, UUIDMixin, TimestampMixin):
    """Customer support issues and escalations."""

    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "category IN ('Complaint', 'Escalation', 'Billing', 'General', 'Technical')",
            name="ck_tickets_category",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_tickets_priority",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_tickets_status",
        ),
        Index("idx_tickets_org_status_created", "organization_id", "status", "created_at"),
    )

    number: Mapped[int] = mapped_column(BigInteger, autoincrement=True, unique=True, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(String(30), default="General", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="tickets")
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="tickets")


# =============================================================================
# 11. AUDIT LOGS (Compliance Trail)
# =============================================================================

class AuditLog(Base, UUIDMixin):
    """Append-only audit record for critical operational events."""

    __tablename__ = "audit_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default="NOW()",
        nullable=False,
    )


# =============================================================================
# 12. KNOWLEDGE BASE (pgvector Documents & Chunks)
# =============================================================================

class KBDocument(Base, UUIDMixin, TimestampMixin):
    """Source documents for the tenant knowledge base."""

    __tablename__ = "kb_documents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    chunks: Mapped[List["KBChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class KBChunk(Base, UUIDMixin):
    """Vectorized knowledge chunk for RAG semantic search."""

    __tablename__ = "kb_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kb_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Vector embedding (384 dimensions matching all-MiniLM-L6-v2)
    # If pgvector is installed, use Vector(384). Fallback to JSONB if extension not loaded in driver.
    if _VECTOR_AVAILABLE:
        embedding = mapped_column(Vector(384), nullable=True)
    else:
        embedding = mapped_column(JSONB, nullable=True)

    # Relationships
    document: Mapped["KBDocument"] = relationship(back_populates="chunks")
