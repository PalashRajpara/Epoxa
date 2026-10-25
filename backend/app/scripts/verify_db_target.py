import asyncio
import sys
import os
import re

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def verify_target():
    """Safely inspects database target without leaking secrets or passwords."""
    raw_url = settings.DATABASE_URL
    async_url = settings.async_database_url

    # Redact credentials for display
    redacted_url = re.sub(r"://([^:@]+):([^@]+)@", r"://\1:***@", raw_url)

    print("=" * 60)
    print("EPOXA DATABASE TARGET VERIFICATION")
    print("=" * 60)
    print(f"Configured Target: {redacted_url}")
    print(f"Environment:       {settings.APP_ENV}")

    if not raw_url or "sqlite" in raw_url:
        print("\nNote: Configured for local SQLite database.")
        return

    try:
        engine = create_async_engine(async_url, echo=False)
        async with engine.connect() as conn:
            # Safe PostgreSQL queries
            ver = (await conn.execute(text("SELECT version()"))).scalar()
            db_name = (await conn.execute(text("SELECT current_database()"))).scalar()
            current_user = (await conn.execute(text("SELECT current_user"))).scalar()
            schema_name = (await conn.execute(text("SELECT current_schema()"))).scalar()

            # Query existing user tables
            table_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = current_schema() 
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = list((await conn.execute(table_query)).scalars().all())

            print("\nConnection Status: SUCCESSFUL")
            print(f"PostgreSQL Version: {ver}")
            print(f"Database Name:      {db_name}")
            print(f"Current User:       {current_user}")
            print(f"Schema:             {schema_name}")
            print(f"Existing Tables ({len(tables)}): {', '.join(tables) if tables else '<empty database - ready for migration>'}")

        await engine.dispose()
        print("=" * 60)
    except Exception as e:
        print("\nConnection Status: FAILED")
        print(f"Safe Error: {type(e).__name__}: {str(e)}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(verify_target())
