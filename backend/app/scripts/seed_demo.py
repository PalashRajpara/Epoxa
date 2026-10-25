import asyncio
import uuid
import sys
import os
from typing import Optional

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import AsyncSessionFactory
from app.core.config import settings
from app.core.logging import logger
from app.models.tenant import Organization, Business, BusinessLocation, SupervisorProfile, OrganizationMembership
from app.models.customer import Customer
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk, AgentConfig
from app.models.ticket import SupportTicket
from app.models.base import utc_now

async def seed_demo_data(session: Optional[AsyncSession] = None, force_prod: bool = False):
    """Idempotently seeds synthetic demo content for Epoxa V1."""
    if settings.APP_ENV == "production" and not force_prod:
        logger.error("Refusing to run seed script against production without explicit override!")
        sys.exit(1)

    logger.info("Starting Epoxa synthetic demo seed", environment=settings.APP_ENV)

    if session is not None:
        await _execute_seed(session)
    else:
        async with AsyncSessionFactory() as db:
            await _execute_seed(db)
            await db.commit()

async def _execute_seed(db: AsyncSession):
        # 1. Check or create demo organization
        stmt = select(Organization).where(Organization.slug == "apex-retail")
        res = await db.execute(stmt)
        org = res.scalars().first()

        if not org:
            org = Organization(
                id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                name="Apex Global Retail",
                slug="apex-retail",
                status="active"
            )
            db.add(org)
            await db.flush()
            logger.info("Created demo organization", org_id=str(org.id), slug=org.slug)
        else:
            logger.info("Demo organization already exists", org_id=str(org.id))

        # 2. Check or create demo business
        stmt = select(Business).where(Business.organization_id == org.id)
        res = await db.execute(stmt)
        biz = res.scalars().first()
        if not biz:
            biz = Business(
                id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                organization_id=org.id,
                name="Apex E-Commerce & Retail",
                category="retail",
                status="active"
            )
            db.add(biz)
            await db.flush()

            loc = BusinessLocation(
                id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
                business_id=biz.id,
                name="Main Distribution Center",
                address="100 Enterprise Way, Suite 400",
                timezone="America/New_York",
                status="active"
            )
            db.add(loc)
            await db.flush()
            logger.info("Created demo business and location")

        # 3. Check or create demo supervisor profile
        from app.core.security import get_password_hash
        sup_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        demo_password_hash = get_password_hash("EpoxaDemo@2026")

        stmt = select(SupervisorProfile).where(SupervisorProfile.email == "supervisor@epoxa.demo")
        res = await db.execute(stmt)
        sup = res.scalars().first()
        if not sup:
            sup = SupervisorProfile(
                id=sup_id,
                email="supervisor@epoxa.demo",
                full_name="Alex Mercer (Lead Supervisor)",
                password_hash=demo_password_hash,
                status="active"
            )
            db.add(sup)
            await db.flush()

            mem = OrganizationMembership(
                organization_id=org.id,
                supervisor_id=sup.id,
                role="admin",
                status="active"
            )
            db.add(mem)
            await db.flush()
            logger.info("Created demo supervisor profile with password and admin membership")
        else:
            sup.password_hash = demo_password_hash
            await db.flush()
            logger.info("Updated demo supervisor profile password hash")

        # 4. Check or create synthetic customers
        stmt = select(Customer).where(Customer.organization_id == org.id)
        res = await db.execute(stmt)
        if not res.scalars().first():
            customers = [
                Customer(
                    id=uuid.UUID("55555555-5555-5555-5555-555555555551"),
                    organization_id=org.id,
                    business_id=biz.id,
                    display_name="Sarah Connor",
                    phone_number="+15550192834",
                    email="sarah.c@example.invalid",
                    company_name="Cyberdyne Logistics",
                    metadata_={"loyalty_tier": "gold", "notes": "VIP business account"}
                ),
                Customer(
                    id=uuid.UUID("55555555-5555-5555-5555-555555555552"),
                    organization_id=org.id,
                    business_id=biz.id,
                    display_name="David Martinez",
                    phone_number="+15550149201",
                    email="david.m@example.invalid",
                    company_name=None,
                    metadata_={"loyalty_tier": "standard"}
                )
            ]
            db.add_all(customers)
            await db.flush()
            logger.info("Seeded synthetic customers")

        # 5. Check or create Knowledge base documents and chunks
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.organization_id == org.id)
        res = await db.execute(stmt)
        if not res.scalars().first():
            doc1 = KnowledgeDocument(
                id=uuid.UUID("66666666-6666-6666-6666-666666666661"),
                organization_id=org.id,
                business_id=biz.id,
                title="Return and Refund Policy",
                document_type="policy",
                metadata_={"source": "customer-service-handbook-v2"}
            )
            doc2 = KnowledgeDocument(
                id=uuid.UUID("66666666-6666-6666-6666-666666666662"),
                organization_id=org.id,
                business_id=biz.id,
                title="Shipping SLAs & Delivery Timelines",
                document_type="faq",
                metadata_={"source": "logistics-faq"}
            )
            db.add_all([doc1, doc2])
            await db.flush()

            chunks = [
                KnowledgeChunk(
                    document_id=doc1.id,
                    organization_id=org.id,
                    chunk_content=(
                        "Our standard return policy allows customers to return any unused retail item within 30 days of delivery "
                        "for a full refund to the original payment method. Items must include original packaging and receipt. "
                        "Return shipping is complimentary for damaged or defective goods. Opened software or consumable items are non-refundable."
                    ),
                    chunk_hash="hash_ret_01",
                    metadata_={"section": "return_window"}
                ),
                KnowledgeChunk(
                    document_id=doc1.id,
                    organization_id=org.id,
                    chunk_content=(
                        "Refund processing takes 3 to 5 business days after our fulfillment center inspects the returned package. "
                        "If a customer requests an immediate cash or store credit override exceeding $150, the AI agent must escalate to a live supervisor."
                    ),
                    chunk_hash="hash_ret_02",
                    metadata_={"section": "refund_processing"}
                ),
                KnowledgeChunk(
                    document_id=doc2.id,
                    organization_id=org.id,
                    chunk_content=(
                        "Standard ground shipping takes 3-5 business days across the continental US. "
                        "Expedited 2-day shipping is available for an extra $15. Orders placed before 2:00 PM EST ship the same business day."
                    ),
                    chunk_hash="hash_ship_01",
                    metadata_={"section": "shipping_times"}
                )
            ]
            db.add_all(chunks)
            await db.flush()
            logger.info("Seeded knowledge documents and chunks")

        # 6. Check or create Agent Config
        stmt = select(AgentConfig).where(AgentConfig.organization_id == org.id)
        res = await db.execute(stmt)
        cfg = res.scalars().first()
        if not cfg:
            cfg = AgentConfig(
                organization_id=org.id,
                business_id=biz.id,
                system_prompt=(
                    "You are Epoxa AI, the customer support specialist for Apex Global Retail. "
                    "You are polite, precise, and speak concisely in spoken English. "
                    "Use official company guidelines for returns and shipping. "
                    "If you cannot verify an answer, offer to connect the customer with a supervisor or file a ticket."
                ),
                voice_model="aura-asteria-en",
                llm_model="qwen/qwen3.8-27b",
                temperature=0.1,
                is_active=True
            )
            db.add(cfg)
            await db.flush()
            logger.info("Created default agent configuration")
        else:
            cfg.llm_model = "qwen/qwen3.8-27b"
            await db.flush()
            logger.info("Updated agent configuration to qwen/qwen3.8-27b")

        # 7. Check or create sample support tickets
        stmt = select(SupportTicket).where(SupportTicket.organization_id == org.id)
        res = await db.execute(stmt)
        if not res.scalars().first():
            ticket1 = SupportTicket(
                organization_id=org.id,
                business_id=biz.id,
                ticket_number="EPX-20261025-A101",
                title="Damaged package received on order #89211",
                description="Customer reported outer box crushed and contents damaged during transit. Requested replacement unit.",
                category="technical",
                priority="high",
                status="open",
                assigned_supervisor_id=sup.id
            )
            ticket2 = SupportTicket(
                organization_id=org.id,
                business_id=biz.id,
                ticket_number="EPX-20261025-B202",
                title="Billing inquiry regarding duplicate subscription charge",
                description="Customer noticed double billing on monthly premium plan. Refund requested for second transaction.",
                category="billing",
                priority="medium",
                status="in_progress"
            )
            db.add_all([ticket1, ticket2])
            await db.flush()
            logger.info("Seeded sample support tickets")

        await db.flush()
        logger.info("Synthetic demo seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_demo_data())
