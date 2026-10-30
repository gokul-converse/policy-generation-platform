"""Asynchronous SQLite database configuration and FTS5 initialization."""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "enterprise_policy.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH.as_posix()}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)


@event.listens_for(engine.sync_engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    """Enable SQLite foreign-key enforcement on each connection."""
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
    """Create and synchronize the FTS5 index.

    Call after the document_chunks table exists.
    Safe to call repeatedly. Existing FTS tables are not recreated.
    """
    async with engine.begin() as connection:
        # Keep this column order compatible with the FTS table
        # previously created in this project's SQLite database.
        await connection.exec_driver_sql(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts
            USING fts5(
                section_title,
                chunk_text,
                content='document_chunks',
                content_rowid='chunk_id'
            )
            """
        )

        # New source rows.
        await connection.exec_driver_sql(
            """
            CREATE TRIGGER IF NOT EXISTS document_chunks_ai
            AFTER INSERT ON document_chunks
            BEGIN
                INSERT INTO document_chunks_fts(
                    rowid, section_title, chunk_text
                )
                VALUES (
                    new.chunk_id, new.section_title, new.chunk_text
                );
            END
            """
        )

        # Updated source rows: remove old indexed values and add new ones.
        await connection.exec_driver_sql(
            """
            CREATE TRIGGER IF NOT EXISTS document_chunks_au
            AFTER UPDATE ON document_chunks
            BEGIN
                INSERT INTO document_chunks_fts(
                    document_chunks_fts,
                    rowid,
                    section_title,
                    chunk_text
                )
                VALUES (
                    'delete',
                    old.chunk_id,
                    old.section_title,
                    old.chunk_text
                );

                INSERT INTO document_chunks_fts(
                    rowid, section_title, chunk_text
                )
                VALUES (
                    new.chunk_id, new.section_title, new.chunk_text
                );
            END
            """
        )

        # Deleted source rows.
        await connection.exec_driver_sql(
            """
            CREATE TRIGGER IF NOT EXISTS document_chunks_ad
            AFTER DELETE ON document_chunks
            BEGIN
                INSERT INTO document_chunks_fts(
                    document_chunks_fts,
                    rowid,
                    section_title,
                    chunk_text
                )
                VALUES (
                    'delete',
                    old.chunk_id,
                    old.section_title,
                    old.chunk_text
                );
            END
            """
        )

        # Check whether the FTS index matches its external content table.
        # rank=1 requests the external-content consistency check.
        try:
            await connection.exec_driver_sql(
                """
                INSERT INTO document_chunks_fts(
                    document_chunks_fts, rank
                )
                VALUES ('integrity-check', 1)
                """
            )
        except SQLAlchemyError:
            # Recover a stale or missing index without dropping the table
            # or losing the source document chunks.
            await connection.exec_driver_sql(
                """
                INSERT INTO document_chunks_fts(document_chunks_fts)
                VALUES ('rebuild')
                """
            )

            # Ensure the rebuilt index is consistent.
            await connection.exec_driver_sql(
                """
                INSERT INTO document_chunks_fts(
                    document_chunks_fts, rank
                )
                VALUES ('integrity-check', 1)
                """
            )


async def create_db_tables() -> None:
    """Create registered tables for development bootstrap only."""
    import app.models  # noqa: F401
    from app.models import policy_db, skill_db  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    # FTS requires document_chunks to exist first.
    await initialize_fts()


async def dispose_db_engine() -> None:
    """Dispose the asynchronous engine during application shutdown."""
    await engine.dispose()
