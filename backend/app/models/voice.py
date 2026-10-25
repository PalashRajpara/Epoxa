import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, JSON, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.base import GUID, TimestampMixin, utc_now

class CallSession(Base, TimestampMixin):
    __tablename__ = "call_sessions"

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

    room_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="initiating", nullable=False, index=True)
    # Statuses: initiating, active, escalated, supervisor_takeover, completed, failed

    handoff_state: Mapped[str] = mapped_column(String(50), default="none", nullable=False)
    # Handoff states: none, requested, accepted, rejected, returned_to_ai

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    termination_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    custom_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)

    # Relationships
    events: Mapped[List["CallEvent"]] = relationship(back_populates="call_session", cascade="all, delete-orphan")
    transcripts: Mapped[List["Transcript"]] = relationship(back_populates="call_session", cascade="all, delete-orphan")
    summary: Mapped[Optional["CallSummary"]] = relationship(back_populates="call_session", uselist=False, cascade="all, delete-orphan")

class CallEvent(Base):
    __tablename__ = "call_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    call_session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(50), default="system", nullable=False)
    # Actors: customer, ai_agent, supervisor, system

    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True
    )

    call_session: Mapped["CallSession"] = relationship(back_populates="events")

class Transcript(Base):
    """Stores individual speech transcript turns. Expired after 30 days by retention job."""
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    call_session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    speaker: Mapped[str] = mapped_column(String(50), nullable=False)
    # Speakers: customer, ai_agent, supervisor

    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_purged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    purged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True
    )

    call_session: Mapped["CallSession"] = relationship(back_populates="transcripts")

class CallSummary(Base, TimestampMixin):
    """Concise AI-generated summary and intent analysis for calls."""
    __tablename__ = "call_summaries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    call_session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    primary_intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    detected_sentiment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    call_session: Mapped["CallSession"] = relationship(back_populates="summary")
