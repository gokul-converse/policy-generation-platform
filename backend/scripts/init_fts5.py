
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as session:
        try:
            # Remove existing triggers so their definitions are refreshed.
            for trigger in (
                "document_chunks_ai",
                "document_chunks_au",
                "document_chunks_ad",
            ):
                await session.execute(
                    text(f"DROP TRIGGER IF EXISTS {trigger}")
                )

            # Create the FTS5 virtual table if it does not exist.
            await session.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts
                USING fts5(
                    chunk_text,
                    section_title,
                    document_id UNINDEXED,
                    page_number UNINDEXED
                )
            """))

            # Rebuild the current index from the source table.
            await session.execute(
                text("DELETE FROM document_chunks_fts")
            )

            await session.execute(text("""
                INSERT INTO document_chunks_fts(
                    rowid,
                    chunk_text,
                    section_title,
                    document_id,
                    page_number
                )
                SELECT
                    chunk_id,
                    chunk_text,
                    COALESCE(section_title, ''),
                    document_id,
                    page_number
                FROM document_chunks
            """))

            # INSERT trigger
            await session.execute(text("""
                CREATE TRIGGER document_chunks_ai
                AFTER INSERT ON document_chunks
                BEGIN
                    INSERT INTO document_chunks_fts(
                        rowid, chunk_text, section_title,
                        document_id, page_number
                    )
                    VALUES (
                        new.chunk_id,
                        new.chunk_text,
                        COALESCE(new.section_title, ''),
                        new.document_id,
                        new.page_number
                    );
                END
            """))

            # UPDATE trigger
            await session.execute(text("""
                CREATE TRIGGER document_chunks_au
                AFTER UPDATE ON document_chunks
                BEGIN
                    DELETE FROM document_chunks_fts
                    WHERE rowid = old.chunk_id;

                    INSERT INTO document_chunks_fts(
                        rowid, chunk_text, section_title,
                        document_id, page_number
                    )
                    VALUES (
                        new.chunk_id,
                        new.chunk_text,
                        COALESCE(new.section_title, ''),
                        new.document_id,
                        new.page_number
                    );
                END
            """))

            # DELETE trigger
            await session.execute(text("""
                CREATE TRIGGER document_chunks_ad
                AFTER DELETE ON document_chunks
                BEGIN
                    DELETE FROM document_chunks_fts
                    WHERE rowid = old.chunk_id;
                END
            """))

            # Verify index row count before committing.
            result = await session.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM document_chunks) AS source_count,
                    (SELECT COUNT(*) FROM document_chunks_fts) AS index_count
            """))
            source_count, index_count = result.one()

            if source_count != index_count:
                raise RuntimeError(
                    f"FTS5 row count mismatch: source={source_count}, "
                    f"index={index_count}"
                )

            await session.commit()

            print("FTS5 initialization successful.")
            print(f"Source chunks: {source_count}")
            print(f"Indexed chunks: {index_count}")
            print("INSERT / UPDATE / DELETE triggers recreated.")

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
