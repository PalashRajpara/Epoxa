"""
Background retention job for purging expired transcripts and latency telemetry.
Advisory-locked to prevent concurrent execution across replicas.
Enforces Decision D6 (Transcripts 90 days, Latency logs 30 days).
"""

import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, text

from epoxa_core.logging import get_logger
from epoxa_core.models.entities import CallTranscript, LatencyLog
from epoxa_core.uow import UnitOfWork

logger = get_logger("epoxa_api.retention")

RETENTION_LOCK_ID = 10928374


async def purge_expired_records_once() -> None:
    """Executes a single retention purge cycle."""
    async with UnitOfWork() as uow:
        lock_res = await uow.session.execute(
            text(f"SELECT pg_try_advisory_xact_lock({RETENTION_LOCK_ID});")
        )
        if not lock_res.scalar():
            return

        now = datetime.now(timezone.utc)

        # 1. Purge Transcripts older than 90 days
        transcript_cutoff = now - timedelta(days=90)
        stmt_transcripts = delete(CallTranscript).where(CallTranscript.spoken_at < transcript_cutoff)
        del_transcripts = await uow.session.execute(stmt_transcripts)

        # 2. Purge Latency logs older than 30 days
        latency_cutoff = now - timedelta(days=30)
        stmt_latencies = delete(LatencyLog).where(LatencyLog.logged_at < latency_cutoff)
        del_latencies = await uow.session.execute(stmt_latencies)

        await uow.commit()

        if del_transcripts.rowcount > 0 or del_latencies.rowcount > 0:
            logger.info(
                "Purged expired retention records",
                purged_transcripts=del_transcripts.rowcount,
                purged_latencies=del_latencies.rowcount,
            )


async def run_retention_worker(interval_hours: int = 24) -> None:
    """Scheduled background worker running once per day."""
    logger.info("Starting background retention worker", interval_hours=interval_hours)
    while True:
        try:
            await purge_expired_records_once()
        except Exception as e:
            logger.error("Error in retention worker cycle", error=str(e))
        await asyncio.sleep(interval_hours * 3600)
