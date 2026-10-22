"""Alembic migration environment for async SQLAlchemy."""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from alembic.autogenerate import comparators
from alembic.autogenerate.compare.schema import PriorityDispatchResult
from alembic.util.langhelpers import DispatchPriority
from app.db.session import DATABASE_URL, Base
from app.models import policy_db, skill_db  # noqa: F401
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config
def get_url() -> str:
    """Return the test database URL when explicitly provided."""
    return os.environ.get("ALEMBIC_DATABASE_URL", DATABASE_URL)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Register the application's SQLAlchemy models.
target_metadata = Base.metadata

def include_object(object, name, type_, reflected, compare_to):
    """Exclude SQLite FTS virtual tables and their shadow tables from autogeneration."""
    if type_ == "table":
        if name == "document_chunks_fts" or name.startswith(
            "document_chunks_fts_"
        ):
            return False

    return True


def run_migrations_offline() -> None:
    """Run migrations without opening a database connection."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Run synchronous Alembic operations on an async connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using the asynchronous database driver."""
    connectable = async_engine_from_config(
        {"sqlalchemy.url": get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()



def run_migrations_online() -> None:
    """Start the asynchronous migration workflow."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
