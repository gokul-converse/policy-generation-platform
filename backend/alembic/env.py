
"""Alembic migration environment for async SQLAlchemy."""

import asyncio
from logging.config import fileConfig

from alembic import context
from alembic.autogenerate import comparators
from alembic.autogenerate.compare.schema import PriorityDispatchResult
from alembic.util.langhelpers import DispatchPriority
from app.db.session import DATABASE_URL, Base
import app.models  # noqa: F401
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Register the application's SQLAlchemy models.
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Filter out objects that should not be compared by Alembic."""
    if type_ == "table":
        # Exclude SQLite FTS5 virtual table and its internal shadow tables
        # as they are managed separately from standard ORM models.
        if name == "document_chunks_fts" or name.startswith("document_chunks_fts_"):
            return False
    return True


@comparators.dispatch_for("column", priority=DispatchPriority.FIRST, subgroup="nullable")
def compare_column_pk_nullable(
    autogen_context,
    alter_column_op,
    schema,
    tname,
    cname,
    conn_col,
    metadata_col,
):
    """Prevent SQLite primary-key reflection discrepancies from generating false modify_nullable ops.

    In SQLite, reflected primary key columns report nullable=True unless explicitly declared
    with NOT NULL in DDL. SQLAlchemy models declare primary_key=True (which defaults nullable=False).
    When comparing SQLite primary key columns whose model specifies primary_key=True,
    this comparator avoids generating false-positive nullability alterations,
    while leaving legitimate nullability changes on non-PK columns detectable.
    """
    if autogen_context.dialect.name == "sqlite":
        if conn_col.primary_key and metadata_col.primary_key:
            if conn_col.nullable and not metadata_col.nullable:
                alter_column_op.existing_nullable = conn_col.nullable
                return PriorityDispatchResult.STOP
    return PriorityDispatchResult.CONTINUE


def get_url() -> str:
    """Return database URL, honoring CLI overrides (-x db_url=...) or custom test configs."""
    x_args = context.get_x_argument(as_dictionary=True)
    if "db_url" in x_args:
        return x_args["db_url"]
    config_url = config.get_main_option("sqlalchemy.url")
    if config_url and not config_url.endswith("./data/enterprise_policy.db"):
        return config_url
    return DATABASE_URL


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
