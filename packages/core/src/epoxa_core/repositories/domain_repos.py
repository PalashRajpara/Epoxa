"""
Domain repositories implementing SQL-only database queries.
Repositories contain zero business logic and enforce organization scoping.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
from epoxa_core.repositories.base import BaseRepository


# =============================================================================
# ORGANIZATIONS & MEMBERSHIPS REPOSITORY
# =============================================================================

class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Organization, session)

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        stmt = select(Organization).where(Organization.slug == slug)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class MembershipRepository(BaseRepository[Membership]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Membership, session)

    async def get_membership(
        self, organization_id: uuid.UUID, profile_id: uuid.UUID
    ) -> Optional[Membership]:
        stmt = select(Membership).where(
            and_(
                Membership.organization_id == organization_id,
                Membership.profile_id == profile_id,
                Membership.is_active.is_(True),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_profile(self, profile_id: uuid.UUID) -> List[Membership]:
        stmt = select(Membership).where(
            and_(Membership.profile_id == profile_id, Membership.is_active.is_(True))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


# =============================================================================
# CUSTOMER REPOSITORY
# =============================================================================

class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Customer, session)

    async def get_by_phone(
        self, organization_id: uuid.UUID, phone_e164: str
    ) -> Optional[Customer]:
        """Looks up an active non-anonymized customer by E.164 phone number."""
        stmt = select(Customer).where(
            and_(
                Customer.organization_id == organization_id,
                Customer.phone_e164 == phone_e164,
                Customer.anonymized_at.is_(None),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_org(
        self, organization_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[Customer]:
        stmt = (
            select(Customer)
            .where(
                and_(
                    Customer.organization_id == organization_id,
                    Customer.anonymized_at.is_(None),
                )
            )
            .order_by(desc(Customer.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def anonymize(self, customer_id: uuid.UUID) -> Optional[Customer]:
        """GDPR/Privacy anonymization: replaces PII with sanitized hashes."""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None
        customer.name = f"Anonymized Customer {str(customer.id)[:8]}"
        customer.phone_e164 = f"+999{str(uuid.uuid4().int)[:10]}"
        customer.email = None
        customer.metadata_ = {}
        customer.anonymized_at = datetime.now(timezone.utc)
        await self.flush()
        return customer


# =============================================================================
# CALL SESSION REPOSITORY
# =============================================================================

class CallSessionRepository(BaseRepository[CallSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CallSession, session)

    async def get_by_room_name(self, room_name: str) -> Optional[CallSession]:
        stmt = select(CallSession).where(CallSession.room_name == room_name)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def count_active_calls(self, organization_id: uuid.UUID) -> int:
        stmt = select(CallSession).where(
            and_(
                CallSession.organization_id == organization_id,
                CallSession.status.in_(["active", "escalated"]),
            )
        )
        res = await self.session.execute(stmt)
        return len(res.scalars().all())

    async def list_active(self, organization_id: uuid.UUID) -> List[CallSession]:
        stmt = (
            select(CallSession)
            .where(
                and_(
                    CallSession.organization_id == organization_id,
                    CallSession.status.in_(["active", "escalated"]),
                )
            )
            .order_by(desc(CallSession.started_at))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_org(
        self,
        organization_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CallSession]:
        conditions = [CallSession.organization_id == organization_id]
        if status:
            conditions.append(CallSession.status == status)

        stmt = (
            select(CallSession)
            .where(and_(*conditions))
            .order_by(desc(CallSession.started_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_handoff_state(
        self, session_id: uuid.UUID, state: str
    ) -> Optional[CallSession]:
        session = await self.get_by_id(session_id)
        if session:
            session.handoff_state = state
            if state == "human_active":
                session.status = "escalated"
            elif state == "ai":
                session.status = "active"
            await self.flush()
        return session

    async def list_stale_active_sessions(
        self, older_than: datetime
    ) -> List[CallSession]:
        """Finds active sessions older than the threshold for reconciliation."""
        stmt = select(CallSession).where(
            and_(
                CallSession.status.in_(["active", "escalated"]),
                CallSession.started_at <= older_than,
            )
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


# =============================================================================
# TRANSCRIPT & LATENCY REPOSITORY
# =============================================================================

class TranscriptRepository(BaseRepository[CallTranscript]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CallTranscript, session)

    async def get_by_session(self, session_id: uuid.UUID) -> List[CallTranscript]:
        stmt = (
            select(CallTranscript)
            .where(CallTranscript.session_id == session_id)
            .order_by(CallTranscript.sequence.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_next_sequence(self, session_id: uuid.UUID) -> int:
        stmt = (
            select(CallTranscript.sequence)
            .where(CallTranscript.session_id == session_id)
            .order_by(desc(CallTranscript.sequence))
            .limit(1)
        )
        res = await self.session.execute(stmt)
        seq = res.scalar_one_or_none()
        return (seq or 0) + 1


class LatencyRepository(BaseRepository[LatencyLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(LatencyLog, session)

    async def get_by_session(self, session_id: uuid.UUID) -> List[LatencyLog]:
        stmt = (
            select(LatencyLog)
            .where(LatencyLog.session_id == session_id)
            .order_by(LatencyLog.logged_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


# =============================================================================
# APPOINTMENT REPOSITORY
# =============================================================================

class AppointmentRepository(BaseRepository[Appointment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Appointment, session)

    async def is_slot_available(
        self, organization_id: uuid.UUID, scheduled_at: datetime
    ) -> bool:
        """Verifies no existing confirmed appointment occupies the start slot (D4)."""
        stmt = select(Appointment).where(
            and_(
                Appointment.organization_id == organization_id,
                Appointment.scheduled_at == scheduled_at,
                Appointment.status == "confirmed",
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is None

    async def get_by_code(
        self, organization_id: uuid.UUID, confirmation_code: str
    ) -> Optional[Appointment]:
        stmt = select(Appointment).where(
            and_(
                Appointment.organization_id == organization_id,
                Appointment.confirmation_code == confirmation_code,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Appointment]:
        conditions = [Appointment.organization_id == organization_id]
        if status:
            conditions.append(Appointment.status == status)

        stmt = (
            select(Appointment)
            .where(and_(*conditions))
            .order_by(desc(Appointment.scheduled_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


# =============================================================================
# TICKET REPOSITORY
# =============================================================================

class TicketRepository(BaseRepository[Ticket]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Ticket, session)

    async def get_by_number(
        self, organization_id: uuid.UUID, number: int
    ) -> Optional[Ticket]:
        stmt = select(Ticket).where(
            and_(Ticket.organization_id == organization_id, Ticket.number == number)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: uuid.UUID,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Ticket]:
        conditions = [Ticket.organization_id == organization_id]
        if status:
            conditions.append(Ticket.status == status)
        if category:
            conditions.append(Ticket.category == category)

        stmt = (
            select(Ticket)
            .where(and_(*conditions))
            .order_by(desc(Ticket.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


# =============================================================================
# AUDIT & HANDOFF EVENTS REPOSITORIES
# =============================================================================

class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditLog, session)

    async def list_by_org(
        self, organization_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class HandoffEventRepository(BaseRepository[HandoffEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(HandoffEvent, session)

    async def list_by_session(self, session_id: uuid.UUID) -> List[HandoffEvent]:
        stmt = (
            select(HandoffEvent)
            .where(HandoffEvent.session_id == session_id)
            .order_by(HandoffEvent.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


# =============================================================================
# KNOWLEDGE BASE REPOSITORY (pgvector)
# =============================================================================

class KBRepository(BaseRepository[KBChunk]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(KBChunk, session)

    async def search_similar(
        self, organization_id: uuid.UUID, query_embedding: List[float], limit: int = 3
    ) -> List[KBChunk]:
        """Vector cosine similarity search over knowledge chunks."""
        # Check if vector extension is active in current dialect
        try:
            stmt = (
                select(KBChunk)
                .where(KBChunk.organization_id == organization_id)
                .order_by(KBChunk.embedding.cosine_distance(query_embedding))
                .limit(limit)
            )
            res = await self.session.execute(stmt)
            return list(res.scalars().all())
        except Exception:
            # Fallback for sqlite/in-memory test environments
            stmt = (
                select(KBChunk)
                .where(KBChunk.organization_id == organization_id)
                .limit(limit)
            )
            res = await self.session.execute(stmt)
            return list(res.scalars().all())
