"""
Current authenticated profile and membership resolution endpoint.
"""

from fastapi import APIRouter, Depends

from epoxa_api.auth.dependencies import AuthenticatedContext, get_authenticated_context
from epoxa_api.schemas import ProfileMeResponse

router = APIRouter(tags=["User"])


@router.get("/me", response_model=ProfileMeResponse)
async def get_current_user_profile(
    ctx: AuthenticatedContext = Depends(get_authenticated_context),
) -> ProfileMeResponse:
    """Returns the verified profile, organization context, and role of the caller."""
    return ProfileMeResponse(
        profile_id=ctx.profile_id,
        email=ctx.email,
        organization_id=ctx.organization_id,
        organization_slug=ctx.organization_slug,
        role=ctx.role,
    )
