"""
Asynchronous Unit of Work pattern ensuring explicit transaction boundaries.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from epoxa_core.database import get_session_factory
from epoxa_core.repositories.domain_repos import (
    AppointmentRepository,
    AuditLogRepository,
    CallSessionRepository,
    CustomerRepository,
    HandoffEventRepository,
    KBRepository,
    LatencyRepository,
    MembershipRepository,
    OrganizationRepository,
    TicketRepository,
    TranscriptRepository,
)


class UnitOfWork:
    """Encapsulates a database transaction and provides access to all domain repositories."""

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        # Instantiate repositories bound to this session
        self.organizations = OrganizationRepository(self.session)
        self.memberships = MembershipRepository(self.session)
        self.customers = CustomerRepository(self.session)
        self.call_sessions = CallSessionRepository(self.session)
        self.transcripts = TranscriptRepository(self.session)
        self.latencies = LatencyRepository(self.session)
        self.appointments = AppointmentRepository(self.session)
        self.tickets = TicketRepository(self.session)
        self.audit_logs = AuditLogRepository(self.session)
        self.handoff_events = HandoffEventRepository(self.session)
        self.kb = KBRepository(self.session)
        return self

    async def __aexit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Any) -> None:
        if self.session is not None:
            if exc_type is not None:
                await self.session.rollback()
            await self.session.close()

    async def commit(self) -> None:
        """Commits the active transaction."""
        if self.session is not None:
            await self.session.commit()

    async def rollback(self) -> None:
        """Rolls back the active transaction."""
        if self.session is not None:
            await self.session.rollback()
