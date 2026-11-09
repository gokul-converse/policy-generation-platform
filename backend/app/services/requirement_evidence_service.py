"""Evidence retrieval from policy documents using SQLite FTS5."""

import re

from sqlalchemy import text

from app.db.session import AsyncSessionLocal


def _build_fts_query(query: str) -> str:
    """Convert natural-language input into a safe FTS5 OR query."""
    tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "define",
        "for", "from", "i", "in", "is", "it", "of", "on", "or",
        "should", "that", "the", "their", "this", "to", "want",
        "what", "with", "policy", "requirement",
    }
    unique_tokens = list(dict.fromkeys(
        token for token in tokens
        if token not in stop_words and len(token) > 1
    ))[:12]
    return " OR ".join(f'"{token}"' for token in unique_tokens)


async def _search(
    fts_query: str,
    domain: str | None,
    limit: int,
) -> list[dict]:
    domain_filter = "AND d.domain = :domain" if domain else ""
    sql = text(f"""
        SELECT
            d.document_id, d.document_name, d.domain, d.version,
            d.approval_status, c.chunk_id, c.section_title,
            c.page_number, c.chunk_text
        FROM document_chunks_fts
        JOIN document_chunks c
            ON c.chunk_id = document_chunks_fts.rowid
        JOIN documents d ON d.document_id = c.document_id
        WHERE document_chunks_fts MATCH :query
        {domain_filter}
        ORDER BY bm25(document_chunks_fts)
        LIMIT :limit
    """)
    params = {"query": fts_query, "limit": max(1, min(limit, 20))}
    if domain:
        params["domain"] = domain

    async with AsyncSessionLocal() as db:
        result = await db.execute(sql, params)
        rows = result.mappings().all()

    return [
        {
            "source_type": "document",
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


async def search_requirement_evidence(
    query: str,
    domain: str = "general",
    limit: int = 5,
) -> list[dict]:
    """Search matching chunks; fall back to all domains if exact match is empty."""
    fts_query = _build_fts_query(query)
    if not fts_query:
        return []

    safe_limit = max(1, min(limit, 20))
    if domain:
        matches = await _search(fts_query, domain, safe_limit)
        if matches:
            return matches

    return await _search(fts_query, None, safe_limit)
