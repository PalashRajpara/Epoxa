"""
Administrative API endpoints: team invitations, role changes, and member deactivation (Admin only).
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from epoxa_api.auth.dependencies import AuthenticatedContext, require_role
from epoxa_api.schemas import (
    MemberInviteRequest,
    MemberResponse,
    MemberRoleUpdateRequest,
)
from epoxa_core.exceptions import ConflictError, EntityNotFoundError
from epoxa_core.models.entities import Membership, Profile
from epoxa_core.uow import UnitOfWork

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/members", response_model=List[MemberResponse])
async def list_team_members(
    ctx: AuthenticatedContext = Depends(require_role("admin")),
) -> List[MemberResponse]:
    """Lists all team members belonging to the organization."""
    async with UnitOfWork() as uow:
        stmt = (
            select(Membership, Profile)
            .join(Profile, Membership.profile_id == Profile.id)
            .where(Membership.organization_id == ctx.organization_id)
        )
        res = await uow.session.execute(stmt)
        rows = res.all()

        return [
            MemberResponse(
                profile_id=prof.id,
                email=prof.email,
                full_name=prof.full_name,
                role=mem.role,
                is_active=mem.is_active,
                created_at=mem.created_at,
            )
            for mem, prof in rows
        ]


@router.post("/members/invite", response_model=MemberResponse)
async def invite_team_member(
    body: MemberInviteRequest,
    ctx: AuthenticatedContext = Depends(require_role("admin")),
) -> MemberResponse:
    """Invites a new supervisor or admin to the organization."""
    async with UnitOfWork() as uow:
        # Check if profile already exists
        prof_stmt = select(Profile).where(Profile.email == body.email.lower().strip())
        res = await uow.session.execute(prof_stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            profile = Profile(
                id=uuid.uuid4(),
                email=body.email.lower().strip(),
                full_name=body.full_name,
                is_active=True,
            )
            uow.session.add(profile)
            await uow.session.flush()

        # Check existing membership in this organization
        mem = await uow.memberships.get_membership(ctx.organization_id, profile.id)
        if mem:
            raise ConflictError(f"User '{body.email}' is already a member of this organization.")

        membership = Membership(
            organization_id=ctx.organization_id,
            profile_id=profile.id,
            role=body.role,
            is_active=True,
        )
        uow.memberships.add(membership)
        await uow.commit()

        return MemberResponse(
            profile_id=profile.id,
            email=profile.email,
            full_name=profile.full_name,
            role=membership.role,
            is_active=membership.is_active,
            created_at=membership.created_at,
        )


@router.patch("/members/{profile_id}/role", response_model=MemberResponse)
async def update_member_role(
    profile_id: uuid.UUID,
    body: MemberRoleUpdateRequest,
    ctx: AuthenticatedContext = Depends(require_role("owner")),
) -> MemberResponse:
    """Changes a member's role (Owner role required)."""
    async with UnitOfWork() as uow:
        mem = await uow.memberships.get_membership(ctx.organization_id, profile_id)
        if not mem:
            raise EntityNotFoundError("Membership", profile_id)

        mem.role = body.role
        profile = await uow.session.get(Profile, profile_id)
        await uow.commit()

        return MemberResponse(
            profile_id=profile.id,
            email=profile.email,
            full_name=profile.full_name,
            role=mem.role,
            is_active=mem.is_active,
            created_at=mem.created_at,
        )
