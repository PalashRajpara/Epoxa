from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger

class Base(DeclarativeBase):
    """SQLAlchemy 2.0 Declarative Base with strict typing."""
    pass

# Engine initialization
# For SQLite test DB, avoid pool_size; for Postgres, configure pool
is_sqlite = settings.async_database_url.startswith("sqlite")
engine_kwargs = {
    "echo": False,
    "future": True,
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_timeout": 30,
    })

engine = create_async_engine(settings.async_database_url, **engine_kwargs)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing a transactional database session per request."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def check_database_health() -> bool:
    """Safely executes a SELECT 1 query to verify database connectivity without leaking info."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database readiness check failed", error=str(e))
        return False
