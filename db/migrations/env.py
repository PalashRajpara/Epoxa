"""
Alembic asynchronous migration environment.
Includes schema filtering to protect Supabase-owned schemas (auth, storage, realtime, etc.).
"""

import asyncio
from logging.config import fileConfig
from typing import Any
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from epoxa_core.models.base import Base
from epoxa_core.settings import settings

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target model metadata for 'autogenerate' support
target_metadata = Base.metadata

# Schemas managed exclusively by Supabase platform
SUPABASE_MANAGED_SCHEMAS = {
    "auth",
    "storage",
    "realtime",
    "vault",
    "extensions",
    "graphql",
    "graphql_public",
    "pgbouncer",
    "supabase_functions",
    "pg_toast",
    "pg_catalog",
    "information_schema",
}


def include_object(
    object: Any,
    name: str,
    type_: str,
    reflected: bool,
    compare_to: Any,
) -> bool:
    """Filters out Supabase internal schemas and tables so autogenerate never touches them."""
    if type_ == "table":
        # Check schema
        if hasattr(object, "schema") and object.schema in SUPABASE_MANAGED_SCHEMAS:
            return False
        # Do not manage Supabase audit or auth tables
        if name in ("schema_migrations", "supabase_migrations"):
            return False
    return True


def get_url() -> str:
    """Returns the migration database URL (Session mode / direct connection)."""
    url = settings.MIGRATION_DATABASE_URL or settings.DATABASE_URL
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an AsyncEngine and associate a connection with the context."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
