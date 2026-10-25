import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_supervisor, get_db
from app.schemas.auth import SupervisorContext, AuthTokenResponse, DevLoginRequest, SupervisorLoginRequest
from app.services.auth_service import auth_service
from app.models.tenant import SupervisorProfile, OrganizationMembership, Organization
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["Supervisor Authentication"])

@router.post("/login", response_model=AuthTokenResponse, summary="Supervisor database login")
async def login(req: SupervisorLoginRequest, db: AsyncSession = Depends(get_db)):
    """Verifies email and password against supervisor_profiles in PostgreSQL and returns JWT access token."""
    return await auth_service.login_with_password(db, email=req.email, password=req.password)

@router.get("/me", response_model=SupervisorContext, summary="Get authenticated supervisor profile")
async def get_me(supervisor: SupervisorContext = Depends(get_current_supervisor)):
    return supervisor

@router.post("/dev-token", response_model=AuthTokenResponse, summary="Generate development token for testing")
async def dev_token(req: DevLoginRequest, db: AsyncSession = Depends(get_db)):
    """Convenience endpoint in development mode to sign in or bootstrap demo supervisor."""
    # Find existing or first supervisor
    stmt = select(SupervisorProfile).where(SupervisorProfile.email == req.email)
    res = await db.execute(stmt)
    profile = res.scalars().first()

    if not profile:
        profile = SupervisorProfile(
            id=uuid.uuid4(),
            email=req.email,
            full_name=req.email.split("@")[0].capitalize()
        )
        db.add(profile)
        await db.flush()

    # Ensure organization membership
    stmt_mem = select(OrganizationMembership).where(OrganizationMembership.supervisor_id == profile.id)
    mem_res = await db.execute(stmt_mem)
    membership = mem_res.scalars().first()

    if not membership:
        org_res = await db.execute(select(Organization).order_by(Organization.created_at.asc()))
        org = org_res.scalars().first()
        if not org:
            org = Organization(name="Epoxa Demo Retail", slug="epoxa-demo")
            db.add(org)
            await db.flush()
        membership = OrganizationMembership(organization_id=org.id, supervisor_id=profile.id, role="admin")
        db.add(membership)
        await db.flush()

    token_str = f"dev-supervisor-{str(profile.id)}"
    return AuthTokenResponse(
        access_token=token_str,
        token_type="bearer",
        expires_in=86400,
        user=SupervisorContext(
            user_id=profile.id,
            email=profile.email,
            full_name=profile.full_name,
            organization_id=membership.organization_id,
            role=membership.role
        )
    )
