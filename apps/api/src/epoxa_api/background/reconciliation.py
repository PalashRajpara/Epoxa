"""
Background task for stale call session reconciliation.
Advisory-locked to prevent race conditions across multiple API replicas.
Preserves the 60-second grace period (Invariant #5).
"""

import asyncio
from datetime import datetime, timedelta, timezone
from livekit import api as lk_api
from sqlalchemy import text

from epoxa_core.logging import get_logger
from epoxa_core.settings import settings
from epoxa_core.uow import UnitOfWork

logger = get_logger("epoxa_api.reconciliation")

RECONCILIATION_LOCK_ID = 98765432


async def reconcile_stale_sessions_once() -> int:
    """Executes one pass of stale call auto-healing with an advisory lock."""
    async with UnitOfWork() as uow:
        # Acquire PostgreSQL transaction-level advisory lock
        lock_res = await uow.session.execute(
            text(f"SELECT pg_try_advisory_xact_lock({RECONCILIATION_LOCK_ID});")
        )
        has_lock = lock_res.scalar()
        if not has_lock:
            # Another replica is currently reconciling
            return 0

        # 1. Fetch active rooms from LiveKit Cloud Server
        active_room_names = set()
        try:
            lk_client = lk_api.LiveKitAPI(
                url=settings.LIVEKIT_URL,
                api_key=settings.LIVEKIT_API_KEY.get_secret_value(),
                api_secret=settings.LIVEKIT_API_SECRET.get_secret_value(),
            )
            async with lk_client as client:
                res = await client.room.list_rooms(lk_api.ListRoomsRequest())
                for room in res.rooms:
                    active_room_names.add(room.name)
        except Exception as e:
            logger.warning("Could not reach LiveKit server to fetch rooms for reconciliation", error=str(e))
            return 0

        # 2. Query sessions older than 60-second grace period
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
        stale_candidates = await uow.call_sessions.list_stale_active_sessions(cutoff)

        healed_count = 0
        for session in stale_candidates:
            if session.room_name not in active_room_names:
                now_utc = datetime.now(timezone.utc)
                duration = int((now_utc - session.started_at).total_seconds())

                session.status = "completed"
                session.ended_at = now_utc
                session.duration_seconds = max(duration, 0)
                session.end_reason = "reconciled_stale_room"
                healed_count += 1

        if healed_count > 0:
            await uow.commit()
            logger.info("Auto-healed stale sessions", count=healed_count)

        return healed_count


async def run_reconciliation_worker(interval_seconds: int = 30) -> None:
    """Continuous background worker loop."""
    logger.info("Starting background reconciliation worker", interval=interval_seconds)
    while True:
        try:
            await reconcile_stale_sessions_once()
        except Exception as e:
            logger.error("Error in reconciliation worker pass", error=str(e))
        await asyncio.sleep(interval_seconds)
