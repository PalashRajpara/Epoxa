"""
Database engine and asynchronous session management.
Configured specifically for Supabase Supavisor transaction pooler compatibility (port 6543, statement_cache_size=0).
"""

from typing import AsyncGenerator, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from epoxa_core.logging import get_logger
from epoxa_core.settings import settings

logger = get_logger("epoxa_core.database")

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine(db_url: Optional[str] = None) -> AsyncEngine:
    """Creates or returns the cached async SQLAlchemy engine with Supavisor pooler configuration."""
    global _engine
    if _engine is None:
        url = db_url or settings.DATABASE_URL
        connect_args = {}

        # If using asyncpg driver against Supavisor transaction pooler, disable prepared statement cache
        if "asyncpg" in url:
            connect_args["statement_cache_size"] = 0
            connect_args["prepared_statement_name_func"] = lambda: None

        _engine = create_async_engine(
            url,
            echo=(settings.ENVIRONMENT == "local" and settings.LOG_LEVEL == "DEBUG"),
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=300,  # 5 minutes
            connect_args=connect_args,
        )
        logger.info("Async database engine initialized", pool_size=10)
    return _engine


def get_session_factory(engine: Optional[AsyncEngine] = None) -> async_sessionmaker[AsyncSession]:
    """Returns the async session factory."""
    global _session_factory
    if _session_factory is None:
        target_engine = engine or get_engine()
        _session_factory = async_sessionmaker(
            bind=target_engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator yielding an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> bool:
    """Performs an active heartbeat query to verify database connectivity."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("Database health check failed", error=str(e))
        return False
