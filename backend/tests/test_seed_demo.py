import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.scripts.seed_demo import seed_demo_data
from app.models.tenant import Organization
from app.models.customer import Customer
from app.models.knowledge import KnowledgeDocument

@pytest.mark.asyncio
async def test_seed_demo_idempotency(db_session: AsyncSession):
    # Running seed script twice must succeed without unique constraint violations
    await seed_demo_data(session=db_session, force_prod=True)
    await seed_demo_data(session=db_session, force_prod=True)

    # Verify seeded organization
    stmt = select(Organization).where(Organization.slug == "apex-retail")
    org = (await db_session.execute(stmt)).scalars().first()
    assert org is not None
    assert org.name == "Apex Global Retail"

    # Verify seeded customers exist
    cust_stmt = select(Customer).where(Customer.organization_id == org.id)
    customers = list((await db_session.execute(cust_stmt)).scalars().all())
    assert len(customers) >= 2

    # Verify knowledge documents exist
    doc_stmt = select(KnowledgeDocument).where(KnowledgeDocument.organization_id == org.id)
    docs = list((await db_session.execute(doc_stmt)).scalars().all())
    assert len(docs) >= 2
