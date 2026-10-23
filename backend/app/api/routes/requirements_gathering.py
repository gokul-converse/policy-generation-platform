
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.agents.requirements_gathering import gather_requirements
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/requirements-gathering",
    tags=["Requirements Gathering"],
)


class GatheringRequest(BaseModel):
    user_input: str = Field(
        min_length=3,
        max_length=5000,
        description="Policy requirement described by the user",
    )


def build_fts_query(user_input: str) -> str:
    """Create a safe, basic keyword query for SQLite FTS5."""
    words = re.findall(r"[A-Za-z0-9]+", user_input.lower())

    # Remove duplicate keywords and limit the query size.
    keywords = list(dict.fromkeys(words))[:12]

    if not keywords:
        return ""

    return " OR ".join(f'"{word}"' for word in keywords)


async def retrieve_evidence(user_input: str) -> list[dict]:
    fts_query = build_fts_query(user_input)

    if not fts_query:
        return []

    sql = text("""
        SELECT
            dc.document_id,
            dc.chunk_id,
            dc.section_title,
            dc.chunk_text,
            dc.page_number,
            d.approval_status
        FROM document_chunks_fts
        JOIN document_chunks dc
            ON dc.chunk_id = document_chunks_fts.rowid
        JOIN documents d
            ON d.document_id = dc.document_id
        WHERE document_chunks_fts MATCH :fts_query
        ORDER BY dc.document_id, dc.chunk_index
        LIMIT 5
    """)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            sql,
            {"fts_query": fts_query},
        )

        rows = result.mappings().all()

    return [
        {
            "document_id": row["document_id"],
            "chunk_id": row["chunk_id"],
            "section_title": row["section_title"],
            "excerpt": row["chunk_text"][:1200],
            "page_number": row["page_number"],
            "approval_status": row["approval_status"],
        }
        for row in rows
    ]


@router.post("/test")
async def test_requirements_gathering(
    request: GatheringRequest,
):
    try:
        evidence = await retrieve_evidence(request.user_input)

        logger.info("Retrieved %s evidence chunks", len(evidence))

        result = await gather_requirements(
            user_input=request.user_input,
            evidence=evidence,
        )

        return {
            "agent": "requirements_gathering",
            "user_input": request.user_input,
            "evidence_count": len(evidence),
            "result": result,
        }

    except ValueError as exc:
        logger.exception("Requirements Gathering Agent returned invalid data")
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Requirements Gathering Agent failed")
        raise HTTPException(
            status_code=500,
            detail="Agent execution failed. Check the backend terminal logs.",
        ) from exc
