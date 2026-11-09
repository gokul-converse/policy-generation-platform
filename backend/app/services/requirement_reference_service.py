"""Generic retrieval of verified structured reference records.

Any SQLAlchemy table registered in Base.metadata with a `data_status`
column can participate. No domain-specific table list is maintained here.
"""

import re
from typing import Any

from sqlalchemy import select

from app.db.session import AsyncSessionLocal, Base

# Import the model module so its tables are registered in Base.metadata.
# This is the same module used by the existing workflow.
import app.models.requirement_db  # noqa: F401


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(value: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(value or "")
        if len(token) > 1
    }


def _serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _record_text(table_name: str, record: dict[str, Any]) -> str:
    values = [table_name.replace("_", " ")]
    values.extend(
        str(value)
        for key, value in record.items()
        if value is not None and key not in {"data_status"}
    )
    return " ".join(values).lower()


def _score_record(
    table_name: str,
    record: dict[str, Any],
    query_tokens: set[str],
    domain_tokens: set[str],
) -> int:
    haystack = _record_text(table_name, record)
    haystack_tokens = _tokens(haystack)
    score = len(query_tokens.intersection(haystack_tokens)) * 2

    record_domain = str(record.get("domain") or "").lower()
    if record_domain:
        if domain_tokens.intersection(_tokens(record_domain)):
            score += 4
        elif domain_tokens:
            # Do not exclude other domains automatically. They may still
            # contain relevant generic reference information.
            score -= 1

    return score


async def retrieve_verified_reference_data(
    query: str,
    domain: str = "",
    limit: int = 30,
) -> list[dict[str, Any]]:
    """Retrieve relevant rows from every registered table with data_status.

    Only rows explicitly marked `verified` are returned. Applicability is
    evaluated by relevance scoring; the function does not assume that a
    domain label alone proves organizational applicability.
    """
    query_tokens = _tokens(query)
    domain_tokens = _tokens(domain)
    if not query_tokens and not domain_tokens:
        return []

    candidates: list[tuple[int, dict[str, Any]]] = []

    async with AsyncSessionLocal() as db:
        for table in Base.metadata.sorted_tables:
            if "data_status" not in table.c:
                continue

            statement = (
                select(table)
                .where(table.c.data_status == "verified")
                .limit(200)
            )
            result = await db.execute(statement)
            rows = result.mappings().all()

            for row in rows:
                record = {
                    key: _serialize_value(value)
                    for key, value in dict(row).items()
                }
                score = _score_record(
                    table.name, record, query_tokens, domain_tokens
                )
                if score > 0:
                    primary_keys = list(table.primary_key.columns)
                    source_id = (
                        record.get(primary_keys[0].name)
                        if primary_keys
                        else None
                    )
                    source_document_id = record.get("source_document_id")
                    item = {
                        "source_type": "sqlite_reference",
                        "source_table": table.name,
                        "source_id": str(source_id) if source_id is not None else None,
                        "source_document_id": source_document_id,
                        "data_status": record.get("data_status"),
                        "record": record,
                    }
                    candidates.append((score, item))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in candidates[: max(1, min(limit, 100))]]
