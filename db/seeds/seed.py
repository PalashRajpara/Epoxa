"""
Idempotent database seed script.
Seeds:
  1. Default tenant organization ('Epoxcel')
  2. Initial admin profile & membership
  3. FAQ Knowledge Base source documents & chunks
"""

import asyncio
import hashlib
import os
import uuid
from sqlalchemy import select

from epoxa_core.database import get_session_factory
from epoxa_core.logging import get_logger, setup_logging
from epoxa_core.models.entities import (
    KBChunk,
    KBDocument,
    Membership,
    Organization,
    Profile,
)
from epoxa_core.uow import UnitOfWork

logger = get_logger("epoxa.seeds")


async def seed_database() -> None:
    """Executes idempotent seeds."""
    setup_logging(level="INFO")
    logger.info("Starting database seed script...")

    async with UnitOfWork() as uow:
        # 1. Seed Organization: Voice AI Agent
        org_stmt = select(Organization).where(Organization.slug.in_(["voice-ai-agent", "epoxcel"]))
        res = await uow.session.execute(org_stmt)
        org = res.scalar_one_or_none()

        if not org:
            org = Organization(
                name="Voice AI Agent",
                slug="voice-ai-agent",
                timezone="Asia/Kolkata",
                settings={
                    "business_hours": {"start": 9, "end": 18, "days": [0, 1, 2, 3, 4, 5]},
                    "default_phone_region": "IN",
                    "retention_days": {"transcripts": 90, "latency_logs": 30},
                },
            )
            uow.organizations.add(org)
            await uow.session.flush()
            logger.info("Seeded organization 'Voice AI Agent'", org_id=str(org.id))
        else:
            logger.info("Organization 'Voice AI Agent' already exists", org_id=str(org.id))

        # 2. Seed Default Admin Profile
        admin_email = os.getenv("FIRST_ADMIN_EMAIL", "admin@epoxcel.com").lower().strip()
        prof_stmt = select(Profile).where(Profile.email == admin_email)
        res = await uow.session.execute(prof_stmt)
        admin_prof = res.scalar_one_or_none()

        if not admin_prof:
            admin_prof = Profile(
                id=uuid.uuid4(),
                email=admin_email,
                full_name="Epoxcel System Administrator",
                is_active=True,
            )
            uow.session.add(admin_prof)
            await uow.session.flush()
            logger.info("Seeded admin profile", email=admin_email)

        # Ensure Membership
        membership = await uow.memberships.get_membership(org.id, admin_prof.id)
        if not membership:
            membership = Membership(
                organization_id=org.id,
                profile_id=admin_prof.id,
                role="owner",
                is_active=True,
            )
            uow.memberships.add(membership)
            await uow.session.flush()
            logger.info("Created owner membership for admin")

        # 3. Seed FAQ Knowledge Base Documents
        faq_dir = os.path.join(os.path.dirname(__file__), "..", "..", "agent", "faq_docs")
        if os.path.exists(faq_dir):
            for filename in sorted(os.listdir(faq_dir)):
                if not filename.endswith(".txt"):
                    continue
                file_path = os.path.join(faq_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                content_hash = hashlib.sha256(content.encode()).hexdigest()
                doc_title = filename.replace(".txt", "").replace("_", " ").title()

                doc_stmt = select(KBDocument).where(
                    KBDocument.organization_id == org.id,
                    KBDocument.title == doc_title,
                )
                res = await uow.session.execute(doc_stmt)
                doc = res.scalar_one_or_none()

                if not doc:
                    doc = KBDocument(
                        organization_id=org.id,
                        title=doc_title,
                        source_path=f"faq_docs/{filename}",
                        content_hash=content_hash,
                        is_active=True,
                    )
                    uow.session.add(doc)
                    await uow.session.flush()

                    chunk = KBChunk(
                        document_id=doc.id,
                        organization_id=org.id,
                        content=content,
                        position=0,
                        embedding=None,  # Embeddings populated by worker or pgvector trigger
                    )
                    uow.session.add(chunk)
                    logger.info("Seeded FAQ document and chunk", title=doc_title)
                else:
                    logger.info("FAQ document up to date", title=doc_title)

        await uow.commit()
        logger.info("Database seeding successfully completed.")


if __name__ == "__main__":
    asyncio.run(seed_database())
