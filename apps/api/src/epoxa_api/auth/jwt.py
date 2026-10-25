"""
Supabase JWT Verification.
Implements asymmetric JWKS verification with TTL caching and legacy HS256 fallback.
"""

import time
from typing import Any, Dict, Optional
import httpx
import jwt
from jwt import PyJWKClient

from epoxa_core.exceptions import UnauthorizedError
from epoxa_core.logging import get_logger
from epoxa_core.settings import settings

logger = get_logger("epoxa_api.jwt")

# In-memory cache for PyJWKClient instance
_jwks_client: Optional[PyJWKClient] = None
_jwks_url: Optional[str] = None


def get_jwks_client() -> Optional[PyJWKClient]:
    """Returns a cached PyJWKClient pointing to the Supabase JWKS endpoint."""
    global _jwks_client, _jwks_url
    if not settings.SUPABASE_URL or "placeholder" in settings.SUPABASE_URL:
        return None

    target_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    if _jwks_client is None or _jwks_url != target_url:
        _jwks_url = target_url
        try:
            _jwks_client = PyJWKClient(target_url, cache_jwk_set=True, lifespan=3600)
        except Exception as e:
            logger.warning("Could not initialize JWKS client", error=str(e))
            return None
    return _jwks_client


def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Verifies a Supabase Auth JWT:
    1. Tries asymmetric RS256/ES256 verification via Supabase JWKS endpoint.
    2. Falls back to HS256 using SUPABASE_JWT_SECRET if configured.
    3. Validates expiration and claims.
    """
    if not token or not isinstance(token, str):
        raise UnauthorizedError("Missing or malformed authorization token.")

    # 1. Attempt Asymmetric JWKS verification
    jwks_client = get_jwks_client()
    if jwks_client is not None:
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                options={"verify_aud": False},  # Supabase aud defaults to 'authenticated'
            )
            return payload
        except Exception as jwks_err:
            logger.debug("JWKS asymmetric verification failed, trying fallback", error=str(jwks_err))

    # 2. Fallback to HS256 with SUPABASE_JWT_SECRET
    if settings.SUPABASE_JWT_SECRET:
        secret = settings.SUPABASE_JWT_SECRET.get_secret_value()
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Session expired. Please log in again.")
        except jwt.InvalidTokenError as err:
            raise UnauthorizedError(f"Invalid authentication token: {str(err)}")

    # 3. For local test environments with mock tokens
    if settings.ENVIRONMENT == "local" and token.startswith("mock_token_"):
        # Format: mock_token_{user_id}_{role}
        parts = token.split("_")
        user_id = parts[2] if len(parts) > 2 else "00000000-0000-0000-0000-000000000001"
        return {"sub": user_id, "email": "test@epoxcel.com", "role": "authenticated"}

    raise UnauthorizedError("Could not verify authentication token against identity provider.")
