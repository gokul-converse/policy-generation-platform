
"""Create and verify the development database tables."""

import asyncio

from app.db.session import create_db_tables, engine
from sqlalchemy import inspect


async def main():
    await create_db_tables()

    async with engine.connect() as connection:
        table_names = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )

    print("Tables found:", table_names)

    assert "skills" in table_names
    assert "skill_versions" in table_names

    print("Database table creation verified.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        asyncio.run(engine.dispose())
