"""
Authentication and Role-Based Access Control (RBAC) FastAPI dependencies.
Ensures organization_id is always taken from authenticated membership, never client input.
"""

import uuid
from dataclasses import dataclass
from typing import Callable, Optional
from fastapi import Depends, Header
from sqlalchemy import select

from epoxa_api.auth.jwt import verify_supabase_jwt
from epoxa_core.exceptions import ForbiddenError, UnauthorizedError
from epoxa_core.models.entities import Membership, Organization, Profile
from epoxa_core.uow import UnitOfWork

# Role hierarchy levels
ROLE_LEVELS = {
    "supervisor": 1,
    "admin": 2,
    "owner": 3,
}


@dataclass
class AuthenticatedContext:
    """Carries verified identity and tenant scoping across authenticated request handlers."""

    profile_id: uuid.UUID
    email: str
    organization_id: uuid.UUID
    role: str
    organization_slug: str


async def get_authenticated_context(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AuthenticatedContext:
    """
    FastAPI dependency:
    1. Extracts Bearer token from header.
    2. Validates JWT signature and expiration.
    3. Resolves profile and active membership.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header. Expected 'Bearer <token>'.")

    token = authorization.split("Bearer ", 1)[1].strip()
    payload = verify_supabase_jwt(token)
    user_id_str = payload.get("sub")

    if not user_id_str:
        raise UnauthorizedError("Token payload missing user identifier ('sub').")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError(f"Invalid UUID user identifier in token: '{user_id_str}'")

    async with UnitOfWork() as uow:
        # Load profile
        profile = await uow.session.get(Profile, user_uuid)
        if not profile or not profile.is_active:
            # Auto-provision profile from JWT claims if first login after Supabase seed
            email = payload.get("email", f"user_{str(user_uuid)[:8]}@epoxcel.com")
            if not profile:
                profile = Profile(
                    id=user_uuid,
                    email=email,
                    full_name=payload.get("user_metadata", {}).get("full_name", email.split("@")[0]),
                    is_active=True,
                )
                uow.session.add(profile)
                await uow.session.flush()

        # Load active membership
        memberships = await uow.memberships.list_by_profile(profile.id)
        if not memberships:
            # Fallback: bind to default Epoxcel organization if single-tenant bootstrap
            org_stmt = select(Organization).where(Organization.slug == "epoxcel")
            res = await uow.session.execute(org_stmt)
            default_org = res.scalar_one_or_none()

            if default_org:
                membership = Membership(
                    organization_id=default_org.id,
                    profile_id=profile.id,
                    role="supervisor",
                    is_active=True,
                )
                uow.memberships.add(membership)
                await uow.commit()
                memberships = [membership]
            else:
                raise ForbiddenError("User is not a member of any active organization.")

        active_membership = memberships[0]
        org = await uow.organizations.get_by_id(active_membership.organization_id)
        org_slug = org.slug if org else "epoxcel"

        return AuthenticatedContext(
            profile_id=profile.id,
            email=profile.email,
            organization_id=active_membership.organization_id,
            role=active_membership.role,
            organization_slug=org_slug,
        )


def require_role(min_role: str) -> Callable[[AuthenticatedContext], AuthenticatedContext]:
    """
    Returns a dependency verifying that the user meets or exceeds the required role.
    Hierarchy: owner (3) > admin (2) > supervisor (1).
    """
    min_level = ROLE_LEVELS.get(min_role, 1)

    async def _role_guard(
        ctx: AuthenticatedContext = Depends(get_authenticated_context),
    ) -> AuthenticatedContext:
        user_level = ROLE_LEVELS.get(ctx.role, 0)
        if user_level < min_level:
            raise ForbiddenError(
                f"Role '{min_role}' or higher is required for this operation. Current role: '{ctx.role}'."
            )
        return ctx

    return _role_guard
