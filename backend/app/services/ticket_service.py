import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.ticket_repo import ticket_repo
from app.models.ticket import SupportTicket
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.core.exceptions import ResourceNotFoundError

class TicketService:
    async def create_ticket(self, db: AsyncSession, org_id: uuid.UUID, data: TicketCreate) -> SupportTicket:
        return await ticket_repo.create_ticket(db, org_id=org_id, data=data)

    async def get_ticket(self, db: AsyncSession, org_id: uuid.UUID, ticket_id: uuid.UUID) -> SupportTicket:
        ticket = await ticket_repo.get_ticket_by_id(db, ticket_id=ticket_id, org_id=org_id)
        if not ticket:
            raise ResourceNotFoundError("SupportTicket", ticket_id)
        return ticket

    async def list_tickets(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[SupportTicket], int]:
        return await ticket_repo.list_tickets(db, org_id=org_id, status=status, priority=priority, page=page, page_size=page_size)

    async def update_ticket(
        self, db: AsyncSession, org_id: uuid.UUID, ticket_id: uuid.UUID, data: TicketUpdate
    ) -> SupportTicket:
        ticket = await self.get_ticket(db, org_id=org_id, ticket_id=ticket_id)
        return await ticket_repo.update_ticket(db, ticket=ticket, data=data)

ticket_service = TicketService()
