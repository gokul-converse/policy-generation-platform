import asyncio
from sqlalchemy import text
from app.db.session import engine


async def main():
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, name FROM skills")
        )
        print("Skills:")
        for row in result.mappings():
            print(dict(row))

        result = await conn.execute(
            text("""
                SELECT id, skill_id, version, description,
                       instructions, status
                FROM skill_versions
            """)
        )
        print("\nSkill versions:")
        for row in result.mappings():
            record = dict(row)
            # Show lengths rather than dumping potentially long instructions.
            record["description"] = (
                f"<{len(record['description'])} characters>"
                if record["description"] else None
            )
            record["instructions"] = (
                f"<{len(record['instructions'])} characters>"
                if record["instructions"] else None
            )
            print(record)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
