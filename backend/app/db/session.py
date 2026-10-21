
"""Asynchronous SQLite database configuration."""

from pathlib import Path

from sqlalchemy import event, text
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
    """Enable SQLite foreign-key enforcement."""

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    """Base class for database models."""


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """Provide an asynchronous database session."""

    async with AsyncSessionLocal() as session:
        yield session


FTS_INIT_STATEMENTS = [
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(
        chunk_text,
        section_title,
        content='document_chunks',
        content_rowid='chunk_id'
    );
    """,
    """
    CREATE TRIGGER IF NOT EXISTS document_chunks_ai AFTER INSERT ON document_chunks BEGIN
        INSERT INTO document_chunks_fts(rowid, chunk_text, section_title)
        VALUES (new.chunk_id, new.chunk_text, COALESCE(new.section_title, ''));
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS document_chunks_ad AFTER DELETE ON document_chunks BEGIN
        INSERT INTO document_chunks_fts(document_chunks_fts, rowid, chunk_text, section_title)
        VALUES ('delete', old.chunk_id, old.chunk_text, COALESCE(old.section_title, ''));
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS document_chunks_au AFTER UPDATE ON document_chunks BEGIN
        INSERT INTO document_chunks_fts(document_chunks_fts, rowid, chunk_text, section_title)
        VALUES ('delete', old.chunk_id, old.chunk_text, COALESCE(old.section_title, ''));
        INSERT INTO document_chunks_fts(rowid, chunk_text, section_title)
        VALUES (new.chunk_id, new.chunk_text, COALESCE(new.section_title, ''));
    END;
    """,
]


async def create_db_tables():
    """Create registered tables and FTS5 search index in the development database."""
    # Import all models so SQLAlchemy registers all table definitions.
    import app.models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        for stmt in FTS_INIT_STATEMENTS:
            await connection.execute(text(stmt))

