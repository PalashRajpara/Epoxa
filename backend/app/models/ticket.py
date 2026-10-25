import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.base import GUID, TimestampMixin, utc_now

class SupportTicket(Base, TimestampMixin):
    __tablename__ = "support_tickets"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    business_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    call_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("call_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    assigned_supervisor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("supervisor_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    ticket_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    # Categories: general, technical, billing, escalation

    priority: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)
    # Priorities: low, medium, high, urgent

    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False, index=True)
    # Statuses: open, in_progress, pending_customer, resolved, closed

    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    call_session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    support_ticket_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("support_tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    # States: pending, accepted, handoff_complete, fallback_ticket_created

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )

class TakeoverEvent(Base):
    """Audit log of supervisor actions during a live call."""
    __tablename__ = "takeover_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    call_session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    supervisor_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("supervisor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # Actions: takeover_started, handback_to_ai, call_ended

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True
    )
