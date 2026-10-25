from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.voice_repo import voice_repo
from app.core.config import settings
from app.core.logging import logger

class RetentionService:
    async def purge_expired_transcripts(
        self, db: AsyncSession, retention_days: int = settings.TRANSCRIPT_RETENTION_DAYS
    ) -> int:
        """Enforces transcript content retention by purging records older than retention_days.
        Preserves call audit metadata, timestamps, session links, and summaries.
        """
        logger.info("Starting transcript retention cleanup", retention_days=retention_days)
        purged_count = await voice_repo.purge_expired_transcripts(db, retention_days=retention_days)
        logger.info(
            "Transcript retention cleanup completed successfully",
            retention_days=retention_days,
            purged_records=purged_count
        )
        return purged_count

retention_service = RetentionService()
