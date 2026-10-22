"""Tests for the asynchronous SQLite connection."""

import pytest
from app.db.session import DATABASE_PATH, engine
from sqlalchemy import text


@pytest.mark.asyncio
async def test_database_connection():
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_sqlite_foreign_keys_enabled():
    async with engine.connect() as connection:
        result = await connection.execute(
            text("PRAGMA foreign_keys")
        )

    assert result.scalar_one() == 1


def test_database_file_path():
    assert DATABASE_PATH.name == "enterprise_policy.db"
