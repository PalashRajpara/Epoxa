import uuid
from typing import AsyncGenerator, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db_session
from app.services.auth_service import auth_service
from app.schemas.auth import SupervisorContext
from app.models.tenant import Organization
from app.core.exceptions import AuthenticationError

security_scheme = HTTPBearer(auto_error=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session

async def get_current_supervisor(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> SupervisorContext:
    """Dependency enforcing supervisor authentication and tenant context."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header with Bearer token is required"
        )
    try:
        return await auth_service.authenticate_supervisor(db, token=credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

async def get_public_organization(
    org_slug: Optional[str] = Header(default=None, alias="X-Organization-Slug"),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    """Resolves default demo organization for customer voice interactions."""
    if org_slug:
        stmt = select(Organization).where(Organization.slug == org_slug)
        result = await db.execute(stmt)
        org = result.scalars().first()
        if org:
            return org

    # Fallback to the primary active organization
    stmt = select(Organization).order_by(Organization.created_at.asc())
    result = await db.execute(stmt)
    org = result.scalars().first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No active organization found; demo database must be seeded."
        )
    return org
