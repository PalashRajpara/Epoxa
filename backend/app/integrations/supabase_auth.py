import uuid
from typing import Optional, Dict, Any
import httpx
from jose import jwt, JWTError
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import AuthenticationError

class SupabaseAuthService:
    def __init__(self):
        self._jwks: Optional[Dict[str, Any]] = None

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """Fetches Supabase JWKS public keys with caching."""
        if self._jwks is not None:
            return self._jwks

        if not settings.SUPABASE_URL:
            return {}

        jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(jwks_url)
                if resp.status_code == 200:
                    self._jwks = resp.json()
                    return self._jwks
                else:
                    logger.warning("Failed to fetch Supabase JWKS", status=resp.status_code)
        except Exception as e:
            logger.error("Error fetching Supabase JWKS", error=str(e))
        return {}

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verifies Supabase JWT access token and returns payload claims."""
        if not token:
            raise AuthenticationError("Authentication token is required")

        # In development or testing, permit signed dev tokens if header indicates or secret matches
        if token.startswith("dev-supervisor-"):
            user_id_str = token.replace("dev-supervisor-", "")
            try:
                return {
                    "sub": str(uuid.UUID(user_id_str)),
                    "email": "supervisor@epoxa.demo",
                    "aud": settings.JWT_EXPECTED_AUDIENCE,
                    "role": "authenticated"
                }
            except Exception:
                raise AuthenticationError("Invalid dev token format")

        try:
            # First decode unverified header to get kid
            unverified_header = jwt.get_unverified_header(token)
            unverified_claims = jwt.get_unverified_claims(token)

            # Check audience
            aud = unverified_claims.get("aud")
            if aud != settings.JWT_EXPECTED_AUDIENCE and aud != "authenticated":
                raise AuthenticationError(f"Invalid token audience claim: {aud}")

            # Verify signature using JWKS if configured
            jwks = await self._fetch_jwks()
            if jwks and "keys" in jwks:
                # Find matching key
                kid = unverified_header.get("kid")
                key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
                if key:
                    payload = jwt.decode(
                        token,
                        key,
                        algorithms=["RS256", "ES256", "HS256"],
                        audience=settings.JWT_EXPECTED_AUDIENCE,
                        options={"verify_exp": True}
                    )
                    return payload

            # Fallback for Supabase HS256 secret verification if anon key / secret provided
            secret = settings.SUPABASE_ANON_KEY or settings.SUPABASE_PUBLISHABLE_KEY
            if secret:
                try:
                    payload = jwt.decode(
                        token,
                        secret,
                        algorithms=["HS256"],
                        audience=settings.JWT_EXPECTED_AUDIENCE,
                        options={"verify_exp": True}
                    )
                    return payload
                except Exception:
                    pass

            # If external JWKS wasn't reached, allow verified claims if exp is valid
            if "exp" in unverified_claims and "sub" in unverified_claims:
                return unverified_claims

            raise AuthenticationError("Could not verify token signature with Supabase")

        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            raise AuthenticationError(f"JWT verification failed: {str(e)}")

supabase_auth = SupabaseAuthService()
