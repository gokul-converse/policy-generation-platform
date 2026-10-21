import asyncio
from sqlalchemy import text
from app.db.session import engine


async def main():
    async with engine.connect() as conn:
        for table in ("skills", "skill_versions"):
            result = await conn.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            )
            print(f"{table} rows:", result.scalar_one())

        result = await conn.execute(
            text("SELECT version_num FROM alembic_version")
        )
        print("Alembic revision:", result.scalar_one())

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
