import time
from typing import Optional
from app.core.config import settings
from app.core.logging import logger

try:
    from livekit import api
    LIVEKIT_AVAILABLE = True
except ImportError:
    LIVEKIT_AVAILABLE = False

class LiveKitService:
    def __init__(self):
        self.is_configured = bool(
            settings.LIVEKIT_URL and settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET
        )

    def generate_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: Optional[str] = None,
        is_supervisor: bool = False,
        ttl_seconds: int = 900
    ) -> str:
        """Generates a room-scoped LiveKit access token with restricted permissions."""
        if not self.is_configured or not LIVEKIT_AVAILABLE:
            # Fallback mock token for tests and offline development
            return f"mock-livekit-token-{room_name}-{participant_identity}"

        token = api.AccessToken(
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET
        )
        token.with_identity(participant_identity)
        if participant_name:
            token.with_name(participant_name)

        import datetime as dt

        # Room scoped grant
        grant = api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        )
        token.with_grants(grant)
        token.with_ttl(dt.timedelta(seconds=ttl_seconds))

        return token.to_jwt()

livekit_service = LiveKitService()
