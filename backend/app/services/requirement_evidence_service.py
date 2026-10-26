
"""Evidence retrieval from existing policy documents using SQLite FTS5."""

import re

from sqlalchemy import text

from app.db.session import AsyncSessionLocal


def _build_fts_query(query: str) -> str:
    """Convert natural-language input into a safe FTS5 query."""
    tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())

    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by",
        "define", "for", "from", "i", "in", "is", "it",
        "of", "on", "or", "should", "that", "the", "their",
        "this", "to", "want", "what", "with",
    }

    unique_tokens = list(
        dict.fromkeys(
            token
            for token in tokens
            if token not in stop_words and len(token) > 1
        )
    )

    # Keep the query small and quote each token to avoid FTS5 syntax errors.
    unique_tokens = unique_tokens[:12]

    if not unique_tokens:
        return ""

    return " OR ".join(f'"{token}"' for token in unique_tokens)


async def search_requirement_evidence(
    query: str,
    domain: str = "general",
    limit: int = 5,
) -> list[dict]:
    """Search existing document chunks using SQLite FTS5."""

    fts_query = _build_fts_query(query)

    if not fts_query:
        return []

    sql = text(
        """
        SELECT
            d.document_id,
            d.document_name,
            d.domain,
            d.version,
            d.approval_status,
            c.chunk_id,
            c.section_title,
            c.page_number,
            c.chunk_text
        FROM document_chunks_fts
        JOIN document_chunks c
            ON c.chunk_id = document_chunks_fts.rowid
        JOIN documents d
            ON d.document_id = c.document_id
        WHERE document_chunks_fts MATCH :query
          AND d.domain = :domain
        ORDER BY bm25(document_chunks_fts)
        LIMIT :limit
        """
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            sql,
            {
                "query": fts_query,
                "domain": domain,
                "limit": max(1, min(limit, 10)),
            },
        )
        rows = result.mappings().all()

    return [
        {
            "document_id": row["document_id"],
            "document_name": row["document_name"],
            "domain": row["domain"],
            "version": row["version"],
            "approval_status": row["approval_status"],
            "chunk_id": row["chunk_id"],
            "section_title": row["section_title"],
            "page_number": row["page_number"],
            "evidence_text": row["chunk_text"],
        }
        for row in rows
    ]
