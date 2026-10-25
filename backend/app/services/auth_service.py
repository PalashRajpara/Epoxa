import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.integrations.supabase_auth import supabase_auth
from app.repositories.tenant_repo import tenant_repo
from app.schemas.auth import SupervisorContext
from app.core.exceptions import AuthenticationError, AuthorizationError

class AuthService:
    async def authenticate_supervisor(self, db: AsyncSession, token: str) -> SupervisorContext:
        """Verifies JWT and resolves the supervisor's active organization membership."""
        claims = await supabase_auth.verify_token(token)
        sub_str = claims.get("sub")
        if not sub_str:
            raise AuthenticationError("Token missing user identifier (sub)")

        try:
            user_id = uuid.UUID(sub_str)
        except ValueError:
            raise AuthenticationError("Malformed user identifier in token")

        # Resolve supervisor profile
        profile = await tenant_repo.get_supervisor_profile(db, supervisor_id=user_id)
        if not profile:
            # Check if this is a first-time signin that needs profile registration
            email = claims.get("email", f"user_{str(user_id)[:6]}@epoxa.demo")
            full_name = claims.get("user_metadata", {}).get("full_name", email.split("@")[0].capitalize())
            profile = await tenant_repo.create_supervisor_profile(db, user_id=user_id, email=email, full_name=full_name)

        # Resolve organization membership
        membership = await tenant_repo.get_supervisor_membership(db, supervisor_id=user_id)
        if not membership:
            # If no membership exists, auto-link to default demo organization if one exists
            from app.models.tenant import Organization
            from sqlalchemy import select
            res = await db.execute(select(Organization).order_by(Organization.created_at.asc()))
            demo_org = res.scalars().first()
            if demo_org:
                membership = await tenant_repo.add_membership(db, org_id=demo_org.id, supervisor_id=user_id, role="supervisor")
            else:
                raise AuthorizationError("Supervisor is not a member of any active organization")

        return SupervisorContext(
            user_id=profile.id,
            email=profile.email,
            full_name=profile.full_name,
            organization_id=membership.organization_id,
            role=membership.role
        )

    async def login_with_password(self, db: AsyncSession, email: str, password: str):
        from app.core.security import verify_password, create_access_token
        from app.schemas.auth import AuthTokenResponse

        profile = await tenant_repo.get_supervisor_by_email(db, email=email)
        if not profile:
            raise AuthenticationError("Invalid email or password")

        if not profile.password_hash or not verify_password(password, profile.password_hash):
            raise AuthenticationError("Invalid email or password")

        membership = await tenant_repo.get_supervisor_membership(db, supervisor_id=profile.id)
        if not membership:
            raise AuthorizationError("Supervisor is not a member of any active organization")

        token = create_access_token({
            "sub": str(profile.id),
            "email": profile.email,
            "org_id": str(membership.organization_id),
            "role": membership.role
        })

        return AuthTokenResponse(
            access_token=token,
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

auth_service = AuthService()
