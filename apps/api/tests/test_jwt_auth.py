"""Test suite for Supabase JWT verification and RBAC guards."""

import pytest
from epoxa_core.exceptions import UnauthorizedError, ForbiddenError
from epoxa_api.auth.jwt import SupabaseJWTVerifier

def test_jwt_verifier_initialization() -> None:
    verifier = SupabaseJWTVerifier()
    assert verifier is not None

def test_missing_token_raises_unauthorized() -> None:
    # Verifying an empty or malformed token string raises UnauthorizedError
    verifier = SupabaseJWTVerifier()
    with pytest.raises(UnauthorizedError):
        verifier.decode_token("")
