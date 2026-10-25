import uuid
import secrets
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ticket import SupportTicket, Escalation, TakeoverEvent
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.models.base import utc_now

class TicketRepository:
    def _generate_ticket_number(self) -> str:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        rand_suffix = secrets.token_hex(2).upper()
        return f"EPX-{date_str}-{rand_suffix}"

    async def create_ticket(self, db: AsyncSession, org_id: uuid.UUID, data: TicketCreate) -> SupportTicket:
        ticket = SupportTicket(
            organization_id=org_id,
            business_id=data.business_id,
            customer_id=data.customer_id,
            call_session_id=data.call_session_id,
            ticket_number=self._generate_ticket_number(),
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority,
            status="open"
        )
        db.add(ticket)
        await db.flush()
        return ticket

    async def get_ticket_by_id(
        self, db: AsyncSession, ticket_id: uuid.UUID, org_id: uuid.UUID
    ) -> Optional[SupportTicket]:
        stmt = select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.organization_id == org_id
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_tickets(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[SupportTicket], int]:
        query = select(SupportTicket).where(SupportTicket.organization_id == org_id)
        if status:
            query = query.where(SupportTicket.status == status)
        if priority:
            query = query.where(SupportTicket.priority == priority)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = query.order_by(SupportTicket.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await db.execute(stmt)).scalars().all())

        return items, total

    async def update_ticket(self, db: AsyncSession, ticket: SupportTicket, data: TicketUpdate) -> SupportTicket:
        if data.title is not None:
            ticket.title = data.title
        if data.description is not None:
            ticket.description = data.description
        if data.category is not None:
            ticket.category = data.category
        if data.priority is not None:
            ticket.priority = data.priority
        if data.assigned_supervisor_id is not None:
            ticket.assigned_supervisor_id = data.assigned_supervisor_id
        if data.status is not None:
            ticket.status = data.status
            if data.status in ("resolved", "closed") and not ticket.resolved_at:
                ticket.resolved_at = utc_now()

        await db.flush()
        return ticket

    async def create_escalation(
        self, db: AsyncSession, org_id: uuid.UUID, session_id: uuid.UUID, reason: str, ticket_id: Optional[uuid.UUID] = None
    ) -> Escalation:
        esc = Escalation(
            organization_id=org_id,
            call_session_id=session_id,
            support_ticket_id=ticket_id,
            reason=reason,
            state="pending",
            requested_at=utc_now()
        )
        db.add(esc)
        await db.flush()
        return esc

    async def get_active_escalation(
        self, db: AsyncSession, session_id: uuid.UUID, org_id: uuid.UUID
    ) -> Optional[Escalation]:
        stmt = select(Escalation).where(
            Escalation.call_session_id == session_id,
            Escalation.organization_id == org_id,
            Escalation.state == "pending"
        ).order_by(Escalation.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().first()

    async def update_escalation_state(
        self, db: AsyncSession, escalation: Escalation, state: str, ticket_id: Optional[uuid.UUID] = None
    ) -> Escalation:
        escalation.state = state
        if ticket_id:
            escalation.support_ticket_id = ticket_id
        if state in ("handoff_complete", "fallback_ticket_created"):
            escalation.resolved_at = utc_now()
        await db.flush()
        return escalation

    async def log_takeover_event(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        session_id: uuid.UUID,
        supervisor_id: uuid.UUID,
        action: str,
        notes: Optional[str] = None
    ) -> TakeoverEvent:
        event = TakeoverEvent(
            organization_id=org_id,
            call_session_id=session_id,
            supervisor_id=supervisor_id,
            action=action,
            notes=notes,
            created_at=utc_now()
        )
        db.add(event)
        await db.flush()
        return event

ticket_repo = TicketRepository()
