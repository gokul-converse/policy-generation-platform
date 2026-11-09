from app.services.requirement_evidence_service import search_requirement_evidence


async def evidence_retrieval_tool(
    query: str,
    domain: str = "general",
) -> list[dict]:
    """Retrieve relevant document evidence from the existing database."""
    return await search_requirement_evidence(query=query, domain=domain)
