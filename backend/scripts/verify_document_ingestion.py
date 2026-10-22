
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as session:
        print("\n=== DOCUMENTS ===")
        result = await session.execute(text("""
            SELECT document_id, document_name, version,
                   approval_status, ingestion_status
            FROM documents
            ORDER BY document_id
        """))
        for row in result.all():
            print(tuple(row))

        print("\n=== CHUNK COUNTS ===")
        result = await session.execute(text("""
            SELECT d.document_name, COUNT(c.chunk_id)
            FROM documents d
            LEFT JOIN document_chunks c
                ON c.document_id = d.document_id
            GROUP BY d.document_id, d.document_name
            ORDER BY d.document_id
        """))
        for row in result.all():
            print(tuple(row))

        print("\n=== SECTION TITLE CHECK ===")
        result = await session.execute(text("""
            SELECT d.document_name, c.page_number,
                   c.chunk_index, c.section_title,
                   substr(c.chunk_text, 1, 100)
            FROM document_chunks c
            JOIN documents d ON d.document_id = c.document_id
            ORDER BY d.document_id, c.chunk_index
            LIMIT 20
        """))
        for row in result.all():
            print(tuple(row))

        result = await session.execute(text("""
            SELECT COUNT(*) AS total,
                   SUM(CASE
                       WHEN section_title IS NULL
                         OR trim(section_title) = ''
                       THEN 1 ELSE 0
                   END) AS missing_titles
            FROM document_chunks
        """))
        row = result.one()
        print(f"\nTotal chunks: {row.total}")
        print(f"Missing section titles: {row.missing_titles or 0}")

        print("\n=== FTS5 SEARCH ===")
        try:
            result = await session.execute(text("""
                SELECT COUNT(*)
                FROM document_chunks_fts
                WHERE chunk_text MATCH :query
            """), {"query": "leave"})
            print(f"'leave' matches: {result.scalar_one()}")
        except Exception as exc:
            print(f"FTS5 search failed: {exc}")

        print("\n=== FTS5 INDEX COUNT ===")
        try:
            result = await session.execute(text("""
                SELECT COUNT(*) FROM document_chunks_fts
            """))
            print(f"Indexed rows: {result.scalar_one()}")
        except Exception as exc:
            print(f"FTS5 index check failed: {exc}")

        print("\n=== REFERENCE DATA COUNTS ===")
        for table_name in (
            "leave_types",
            "expense_categories",
            "access_roles",
            "approval_rules",
        ):
            result = await session.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}"')
            )
            print(f"{table_name}: {result.scalar_one()}")


if __name__ == "__main__":
    asyncio.run(main())
