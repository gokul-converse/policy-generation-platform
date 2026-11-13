"""Retrieve relevant verified structured records across registered tables."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select

from app.db.session import AsyncSessionLocal, Base

# Ensure mapped tables are registered before inspecting metadata.
import app.models.requirement_db  # noqa: F401


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOP_WORDS = {
    "a", "about", "all", "also", "an", "and", "any", "are", "as", "at",
    "be", "been", "being", "but", "by", "can", "could", "company", "cover",
    "define", "do", "does", "for", "from", "get", "give", "has", "have",
    "help", "how", "i", "if", "in", "include", "into", "is", "it", "its",
    "may", "me", "need", "not", "of", "on", "or", "our", "please", "policy",
    "provide", "request", "should", "some", "such", "that", "the", "their",
    "them", "there", "these", "this", "those", "to", "us", "want", "we",
    "what", "when", "where", "which", "who", "why", "will", "with", "would",
    "you", "your", "employee", "employees", "organisation", "organization",
    "business", "requirement", "requirements",
}
_DOMAIN_ALIASES = {
    "human resources": "hr",
    "human_resource": "hr",
    "human_resources": "hr",
    "it security": "it_security",
    "information security": "it_security",
    "information_security": "it_security",
    "general": "general",
    "common": "general",
}


def _tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in _TOKEN_RE.findall(value or "")
        if len(token) > 2 and token.casefold() not in _STOP_WORDS
    }


def _normalise_domain(value: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", (value or "").strip().casefold())
    return _DOMAIN_ALIASES.get(cleaned, cleaned.replace(" ", "_"))


def _serialise(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _record_text(table_name: str, record: dict[str, Any]) -> str:
    excluded = {
        "data_status", "source_document_id", "id", "created_at",
        "updated_at", "modified_at",
    }
    values = [table_name.replace("_", " ")]
    values.extend(
        str(value)
        for key, value in record.items()
        if key.casefold() not in excluded and value is not None
    )
    return " ".join(values)


def _score_record(
    table_name: str,
    record: dict[str, Any],
    query_tokens: set[str],
    requested_domain: str,
) -> tuple[int, int]:
    record_tokens = _tokens(_record_text(table_name, record))
    matched = query_tokens & record_tokens
    overlap = len(matched)

    if not overlap:
        return 0, 0

    record_domain = _normalise_domain(str(record.get("domain") or ""))
    if requested_domain and record_domain:
        # A cross-domain row is excluded rather than rescued by common words.
        if record_domain not in {requested_domain, "general"}:
            return 0, overlap

    # Require at least two meaningful matches, or one unusually specific term.
    specific_match = any(len(token) >= 10 for token in matched)
    if overlap < 2 and not specific_match:
        return 0, overlap

    score = overlap * 4
    if requested_domain and record_domain == requested_domain:
        score += 3
    elif record_domain == "general":
        score += 1

    return score, overlap


async def retrieve_verified_reference_data(
    query: str,
    domain: str = "",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Return verified records with meaningful subject overlap.

    `verified` describes record data status only. It is not interpreted as
    formal policy approval. Provenance and original record fields are retained.
    """
    query_tokens = _tokens(query)
    requested_domain = _normalise_domain(domain)

    if not query_tokens:
        return []

    candidates: list[tuple[int, int, dict[str, Any]]] = []

    async with AsyncSessionLocal() as db:
        for table in Base.metadata.sorted_tables:
            if "data_status" not in table.c:
                continue

            result = await db.execute(
                select(table)
                .where(table.c.data_status == "verified")
                .limit(200)
            )

            for row in result.mappings().all():
                record = {
                    key: _serialise(value)
                    for key, value in dict(row).items()
                }
                score, overlap = _score_record(
                    table.name, record, query_tokens, requested_domain
                )
                if score <= 0:
                    continue

                primary_keys = list(table.primary_key.columns)
                source_id = (
                    record.get(primary_keys[0].name)
                    if primary_keys else None
                )
                candidates.append((score, overlap, {
                    "source_type": "sqlite_reference",
                    "source_table": table.name,
                    "source_id": (
                        str(source_id) if source_id is not None else None
                    ),
                    "source_document_id": record.get("source_document_id"),
                    "data_status": record.get("data_status"),
                    "record": record,
                }))

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [
        item[2]
        for item in candidates[:max(1, min(limit, 30))]
    ]
