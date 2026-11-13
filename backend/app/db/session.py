"""Asynchronous Postgres database configuration and FTS5 initialization."""
import os
from dotenv import load_dotenv
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event
# from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load PostgreSQL credentials from .env
load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured.")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

@event.listens_for(engine.sync_engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    if engine.dialect.name == "sqlite":
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


class Base(DeclarativeBase):
    """Base class for database models."""


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        yield session

async def initialize_fts() -> None:
    """Create the PostgreSQL full-text search index.

    PostgreSQL automatically maintains the GIN index when
    document_chunks rows are inserted, updated, or deleted.
    """
    if engine.dialect.name != "postgresql":
        raise RuntimeError(
            "PostgreSQL full-text search requires a PostgreSQL database."
        )

    async with engine.begin() as connection:
        await connection.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS ix_document_chunks_search
            ON document_chunks
            USING GIN (
                (
                    setweight(
                        to_tsvector(
                            'english',
                            coalesce(section_title, '')
                        ),
                        'A'
                    )
                    ||
                    setweight(
                        to_tsvector(
                            'english',
                            coalesce(chunk_text, '')
                        ),
                        'B'
                    )
                )
            )
            """
        )

async def create_db_tables() -> None:
    """Create registered tables for development bootstrap only."""
    import app.models  # noqa: F401
    from app.models import policy_db, skill_db  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    await initialize_fts()


async def dispose_db_engine() -> None:
    """Dispose the asynchronous engine during application shutdown."""
    await engine.dispose()
