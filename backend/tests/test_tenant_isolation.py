import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.customer_repo import customer_repo
from app.repositories.ticket_repo import ticket_repo
from app.repositories.voice_repo import voice_repo
from app.schemas.customer import CustomerCreate
from app.schemas.ticket import TicketCreate
from app.services.handoff_service import handoff_service
from app.core.exceptions import ResourceNotFoundError

@pytest.mark.asyncio
async def test_cross_tenant_customer_isolation(db_session: AsyncSession, org_a, org_b):
    shared_phone = "+15551239999"

    # Create customer in Org A
    cust_a = await customer_repo.create(
        db_session,
        org_id=org_a.id,
        data=CustomerCreate(display_name="Customer In A", phone_number=shared_phone, email="cust_a@test.com")
    )

    # Create customer in Org B with same phone
    cust_b = await customer_repo.create(
        db_session,
        org_id=org_b.id,
        data=CustomerCreate(display_name="Customer In B", phone_number=shared_phone, email="cust_b@test.com")
    )

    # Match search in Org A must ONLY return cust_a
    matched_a = await customer_repo.find_match(db_session, org_id=org_a.id, phone=shared_phone)
    assert matched_a is not None
    assert matched_a.id == cust_a.id
    assert matched_a.display_name == "Customer In A"

    # Match search in Org B must ONLY return cust_b
    matched_b = await customer_repo.find_match(db_session, org_id=org_b.id, phone=shared_phone)
    assert matched_b is not None
    assert matched_b.id == cust_b.id
    assert matched_b.display_name == "Customer In B"

    # Org A attempting to retrieve Org B customer by ID must return None
    cross_lookup = await customer_repo.get_by_id(db_session, customer_id=cust_b.id, org_id=org_a.id)
    assert cross_lookup is None

@pytest.mark.asyncio
async def test_cross_tenant_ticket_isolation(db_session: AsyncSession, org_a, org_b):
    ticket_b = await ticket_repo.create_ticket(
        db_session,
        org_id=org_b.id,
        data=TicketCreate(title="Confidential Issue in Org B", description="Private data")
    )

    # Lookup by Org A should return None
    res = await ticket_repo.get_ticket_by_id(db_session, ticket_id=ticket_b.id, org_id=org_a.id)
    assert res is None

    # Listing tickets in Org A should not include ticket_b
    items, total = await ticket_repo.list_tickets(db_session, org_id=org_a.id)
    assert ticket_b.id not in [t.id for t in items]

@pytest.mark.asyncio
async def test_cross_tenant_takeover_prevention(db_session: AsyncSession, org_a, org_b, supervisor_a):
    # Org B call session
    call_b = await voice_repo.create_session(
        db_session,
        org_id=org_b.id,
        room_name="epoxa-org-b-room-123"
    )

    # Supervisor from Org A tries to take over Org B call -> Must raise ResourceNotFoundError
    with pytest.raises(ResourceNotFoundError):
        await handoff_service.request_takeover(
            db_session,
            org_id=org_a.id,  # Supervisor A's tenant
            session_id=call_b.id,
            supervisor_id=supervisor_a.id,
            supervisor_name=supervisor_a.full_name
        )
