import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.tenant import Organization, Business, BusinessLocation, SupervisorProfile, OrganizationMembership

class TenantRepository:
    async def get_organization_by_id(self, db: AsyncSession, org_id: uuid.UUID) -> Optional[Organization]:
        stmt = select(Organization).where(Organization.id == org_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_organization_by_slug(self, db: AsyncSession, slug: str) -> Optional[Organization]:
        stmt = select(Organization).where(Organization.slug == slug)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_businesses(self, db: AsyncSession, org_id: uuid.UUID) -> List[Business]:
        stmt = select(Business).where(Business.organization_id == org_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_supervisor_profile(self, db: AsyncSession, supervisor_id: uuid.UUID) -> Optional[SupervisorProfile]:
        stmt = select(SupervisorProfile).where(SupervisorProfile.id == supervisor_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_supervisor_by_email(self, db: AsyncSession, email: str) -> Optional[SupervisorProfile]:
        stmt = select(SupervisorProfile).where(SupervisorProfile.email == email)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_supervisor_membership(
        self, db: AsyncSession, supervisor_id: uuid.UUID, org_id: Optional[uuid.UUID] = None
    ) -> Optional[OrganizationMembership]:
        stmt = select(OrganizationMembership).options(
            selectinload(OrganizationMembership.organization)
        ).where(OrganizationMembership.supervisor_id == supervisor_id)
        if org_id:
            stmt = stmt.where(OrganizationMembership.organization_id == org_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create_organization(self, db: AsyncSession, name: str, slug: str) -> Organization:
        org = Organization(name=name, slug=slug)
        db.add(org)
        await db.flush()
        return org

    async def create_supervisor_profile(self, db: AsyncSession, user_id: uuid.UUID, email: str, full_name: str) -> SupervisorProfile:
        profile = SupervisorProfile(id=user_id, email=email, full_name=full_name)
        db.add(profile)
        await db.flush()
        return profile

    async def add_membership(
        self, db: AsyncSession, org_id: uuid.UUID, supervisor_id: uuid.UUID, role: str = "supervisor"
    ) -> OrganizationMembership:
        membership = OrganizationMembership(organization_id=org_id, supervisor_id=supervisor_id, role=role)
        db.add(membership)
        await db.flush()
        return membership

tenant_repo = TenantRepository()
