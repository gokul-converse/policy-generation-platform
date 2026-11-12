"""Search completed document chunks using SQLite FTS5."""
from __future__ import annotations

import re

from sqlalchemy import text

from app.db.session import AsyncSessionLocal


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could",
    "define", "do", "does", "for", "from", "how", "i", "in", "is", "it",
    "of", "on", "or", "our", "please", "should", "that", "the", "their",
    "this", "to", "want", "we", "what", "when", "which", "who", "with",
    "policy", "requirement", "company", "business",
}


def _build_fts_query(query: str, max_terms: int = 18) -> str:
    tokens = re.findall(r"[a-zA-Z0-9_]+", (query or "").casefold())
    unique = list(dict.fromkeys(
        token for token in tokens
        if len(token) > 2 and token not in _STOP_WORDS
    ))
    return " OR ".join(f'"{token}"' for token in unique[:max_terms])


async def _search(
    fts_query: str,
    domains: list[str] | None,
    limit: int,
) -> list[dict]:
    domain_clause = ""
    params = {"query": fts_query, "limit": max(1, min(limit, 20))}

    if domains:
        placeholders = []
        for index, domain in enumerate(domains):
            key = f"domain_{index}"
            placeholders.append(f":{key}")
            params[key] = domain
        domain_clause = f"AND lower(d.domain) IN ({', '.join(placeholders)})"

    sql = text(f"""
        SELECT d.document_id, d.document_name, d.domain, d.version,
               d.approval_status, d.ingestion_status,
               c.chunk_id, c.section_title, c.page_number, c.chunk_text
        FROM document_chunks_fts
        JOIN document_chunks c
          ON c.chunk_id = document_chunks_fts.rowid
        JOIN documents d
          ON d.document_id = c.document_id
        WHERE document_chunks_fts MATCH :query
          AND lower(d.ingestion_status) = 'completed'
          {domain_clause}
        ORDER BY bm25(document_chunks_fts)
        LIMIT :limit
    """)

    async with AsyncSessionLocal() as db:
        result = await db.execute(sql, params)
        rows = result.mappings().all()

    return [{
        "source_type": "document",
        "document_id": row["document_id"],
        "document_name": row["document_name"],
        "domain": row["domain"],
        "version": row["version"],
        "approval_status": row["approval_status"],
        "ingestion_status": row["ingestion_status"],
        "chunk_id": row["chunk_id"],
        "section_title": row["section_title"],
        "page_number": row["page_number"],
        "evidence_text": row["chunk_text"],
    } for row in rows]


async def search_requirement_evidence(
    query: str,
    domain: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    Prefer same-domain and general documents. Fall back to cross-domain
    evidence only when the preferred search returns no matches.
    Approval status is returned as metadata, never inferred here.
    """
    fts_query = _build_fts_query(query)
    if not fts_query:
        return []

    safe_limit = max(1, min(limit, 20))
    if domain:
        matches = await _search(
            fts_query,
            [domain.casefold(), "general"],
            safe_limit,
        )
        if matches:
            return matches

    return await _search(fts_query, None, safe_limit)
