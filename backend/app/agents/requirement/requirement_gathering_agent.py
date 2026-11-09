"""Gather generic requirements using the shared Foundry client."""

import json

from agent_framework import Message
from pydantic import ValidationError

from app.agents.requirement.prompts.gathering_prompt import GATHERING_PROMPT
from app.agents.requirement.tools.evidence_retrieval_tool import evidence_retrieval_tool
from app.clients.foundry_client import get_foundry_client
from app.schemas.requirements import GatheringResult
from app.services.requirement_reference_service import (
    retrieve_verified_reference_data,
)


async def gather_requirements(
    description: str,
    conversation_history: str = "",
) -> GatheringResult:
    """Extract requirements and retrieve generic reference/document context."""
    client = get_foundry_client()

    # First pass: infer the domain and extract useful search terms.
    response = await client.get_response(
        messages=[
            Message(
                role="user",
                contents=[
                    f"""
{GATHERING_PROMPT}

Original user request:
{description}

Complete conversation and clarification history:
{conversation_history or "No previous conversation."}

Return exactly one JSON object with this structure:
{{
  "requirements": {{
    "policy_name": "string or null",
    "domain": "string containing the best-fit domain label",
    "purpose": "string or null",
    "scope": "string or null",
    "stakeholders": ["string"],
    "rules": ["string"],
    "unresolved_details": ["string"]
  }},
  "evidence": [],
  "reference_data": [],
  "summary": "string"
}}

Requirements:
- Use the exact schema and field types shown above.
- Use arrays of strings for stakeholders, rules, and unresolved_details.
- The domain is an open-ended string; do not restrict it to a predefined list.
- Do not invent missing values or treat evidence as user confirmation.
- Return valid JSON only, without Markdown fences or extra text.
"""
                ],
            )
        ]
    )

    try:
        gathered = GatheringResult.model_validate_json(response.text)
    except (ValidationError, ValueError) as exc:
        raise ValueError(
            "Requirement gathering agent returned invalid JSON or an "
            f"incompatible schema. Details: {exc}. Raw response: "
            f"{response.text[:3000]}"
        ) from exc

    req = gathered.requirements
    evidence_query = " ".join(
        part.strip()
        for part in (
            description,
            req.policy_name or "",
            req.domain or "",
            req.purpose or "",
            req.scope or "",
            " ".join(req.stakeholders),
            " ".join(req.rules),
            " ".join(req.unresolved_details),
        )
        if part and part.strip()
    )

    # These are separate sources and remain separately identifiable.
    reference_data = await retrieve_verified_reference_data(
        query=evidence_query,
        domain=req.domain,
    )
    document_evidence = await evidence_retrieval_tool(
        query=evidence_query,
        domain=req.domain,
    )

    return gathered.model_copy(
        update={
            "reference_data": reference_data,
            "evidence": [
                json.dumps(item, ensure_ascii=False)
                for item in document_evidence
            ],
        }
    )
