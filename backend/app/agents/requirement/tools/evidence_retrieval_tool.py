"""Retrieve supporting document evidence for extracted requirements."""
from app.services.requirement_evidence_service import search_requirement_evidence


async def evidence_retrieval_tool(
    query: str,
    domain: str | None = None,
) -> list[dict]:
    return await search_requirement_evidence(query=query, domain=domain)
