import asyncio
from sqlalchemy import text
from app.db.session import engine

async def main():
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = '_alembic_tmp_skill_versions'
            """)
        )
        table_name = result.scalar_one_or_none()
        print("Temporary table found:", table_name)

        if table_name:
            await conn.execute(
                text("DROP TABLE _alembic_tmp_skill_versions")
            )
            print("Temporary table removed.")
        else:
            print("No temporary table needs cleanup.")

    await engine.dispose()

asyncio.run(main())
