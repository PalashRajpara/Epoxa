"""
Ticket service for managing customer support issues and escalations.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from epoxa_core.exceptions import EntityNotFoundError, ValidationError
from epoxa_core.models.entities import Ticket
from epoxa_core.uow import UnitOfWork


class TicketService:
    """Handles support ticket logging and supervisor status updates."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create_ticket(
        self,
        organization_id: uuid.UUID,
        category: str,
        description: str,
        customer_id: Optional[uuid.UUID] = None,
        session_id: Optional[uuid.UUID] = None,
        priority: str = "normal",
    ) -> Ticket:
        desc_clean = description.strip()
        if not desc_clean:
            raise ValidationError("Ticket description cannot be empty.")
        if len(desc_clean) > 2000:
            raise ValidationError("Ticket description cannot exceed 2000 characters.")

        ticket = Ticket(
            organization_id=organization_id,
            customer_id=customer_id,
            session_id=session_id,
            category=category,
            priority=priority,
            description=desc_clean,
            status="open",
        )
        self.uow.tickets.add(ticket)
        await self.uow.commit()
        return ticket

    async def update_ticket(
        self,
        organization_id: uuid.UUID,
        ticket_id: uuid.UUID,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[uuid.UUID] = None,
    ) -> Ticket:
        ticket = await self.uow.tickets.get_by_id(ticket_id)
        if not ticket or ticket.organization_id != organization_id:
            raise EntityNotFoundError("Ticket", ticket_id)

        if status:
            ticket.status = status
            if status in ("resolved", "closed"):
                ticket.resolved_at = datetime.now(timezone.utc)
        if priority:
            ticket.priority = priority
        if assigned_to is not None:
            ticket.assigned_to = assigned_to

        await self.uow.commit()
        return ticket

    async def list_tickets(
        self,
        organization_id: uuid.UUID,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Ticket]:
        return await self.uow.tickets.list_by_org(
            organization_id, status=status, category=category, limit=limit, offset=offset
        )
