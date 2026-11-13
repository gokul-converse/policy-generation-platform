"""Search completed document chunks using PostgreSQL full-text search."""

import re

from app.db.session import AsyncSessionLocal
from sqlalchemy import text

_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by",
    "for", "from", "in", "into", "is", "it", "of",
    "on", "or", "that", "the", "this", "to", "with",
}


def _build_search_query(query: str, max_terms: int = 18) -> str:
    """Build a PostgreSQL web-search query from user input.

    OR is retained to provide behaviour similar to the previous
    FTS5 query, which searched for any matching term.
    """
    tokens = re.findall(r"[a-zA-Z0-9_]+", query.casefold())

    filtered_tokens = [
        token for token in tokens
        if token not in _STOP_WORDS
    ][:max_terms]

    if not filtered_tokens:
        return ""

    return " OR ".join(filtered_tokens)


async def _search(
    search_query: str,
    domains: list[str] | None,
    limit: int,
) -> list[dict]:
    """Execute PostgreSQL full-text search against document chunks."""

    params: dict = {
        "query": search_query,
        "limit": limit,
    }

    domain_clause = ""

    if domains:
        domain_params = []

        for index, domain in enumerate(domains):
            param_name = f"domain_{index}"
            domain_params.append(f":{param_name}")
            params[param_name] = domain.casefold()

        domain_clause = (
            f"AND lower(d.domain) IN ({', '.join(domain_params)})"
        )

    sql = text(
        f"""
        SELECT
            d.document_id,
            d.document_name,
            d.domain,
            d.version,
            d.approval_status,
            d.ingestion_status,
            c.chunk_id,
            c.section_title,
            c.page_number,
            c.chunk_text,
            ts_rank(
                (
                    setweight(
                        to_tsvector(
                            'english',
                            coalesce(c.section_title, '')
                        ),
                        'A'
                    )
                    ||
                    setweight(
                        to_tsvector(
                            'english',
                            coalesce(c.chunk_text, '')
                        ),
                        'B'
                    )
                ),
                websearch_to_tsquery('english', :query)
            ) AS relevance_score
        FROM document_chunks AS c
        JOIN documents AS d
            ON d.document_id = c.document_id
        WHERE
            (
                setweight(
                    to_tsvector(
                        'english',
                        coalesce(c.section_title, '')
                    ),
                    'A'
                )
                ||
                setweight(
                    to_tsvector(
                        'english',
                        coalesce(c.chunk_text, '')
                    ),
                    'B'
                )
            ) @@ websearch_to_tsquery('english', :query)
            AND lower(d.ingestion_status) = 'completed'
            {domain_clause}
        ORDER BY relevance_score DESC
        LIMIT :limit
        """
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(sql, params)
        rows = result.mappings().all()

    return [
        {
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
            "relevance_score": row["relevance_score"],
        }
        for row in rows
    ]


async def search_requirement_evidence(
    query: str,
    domain: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Search policy evidence, prioritizing the requested domain."""

    search_query = _build_search_query(query)

    if not search_query:
        return []

    limit = max(1, min(limit, 20))

    if domain:
        preferred_domains = [
            domain.casefold(),
            "general",
        ]

        results = await _search(
            search_query=search_query,
            domains=preferred_domains,
            limit=limit,
        )

        if results:
            return results

    return await _search(
        search_query=search_query,
        domains=None,
        limit=limit,
    )
