import asyncio
import sys
import os

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.session import AsyncSessionFactory
from app.services.retention_service import retention_service
from app.core.config import settings
from app.core.logging import logger

async def run_cleanup():
    """CLI task to enforce 30-day transcript retention."""
    logger.info("Executing scheduled transcript retention purge job")
    async with AsyncSessionFactory() as db:
        purged = await retention_service.purge_expired_transcripts(db, retention_days=settings.TRANSCRIPT_RETENTION_DAYS)
        await db.commit()
        print(f"Transcript retention cleanup finished. Purged records: {purged}")

if __name__ == "__main__":
    asyncio.run(run_cleanup())
