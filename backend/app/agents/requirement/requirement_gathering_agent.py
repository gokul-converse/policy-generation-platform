"""Extract the initial requirement, then retrieve supporting context."""
from __future__ import annotations

import asyncio
import json
import logging
import re

from agent_framework import Message
from pydantic import ValidationError

from app.agents.requirement.prompts.gathering_prompt import GATHERING_PROMPT
from app.agents.requirement.tools.evidence_retrieval_tool import evidence_retrieval_tool
from app.clients.foundry_client import get_foundry_client
from app.schemas.requirements import GatheringResult, RequirementDetails
from app.services.requirement_reference_service import retrieve_verified_reference_data

logger = logging.getLogger(__name__)


def _retrieval_domain(domain: str | None) -> str | None:
    """Normalise familiar labels while allowing arbitrary domain names."""
    value = re.sub(r"\s+", " ", (domain or "").strip().casefold())
    if not value or value == "general":
        return None
    if value == "hr" or "human resource" in value:
        return "hr"
    if "finance" in value or "account" in value:
        return "finance"
    if "security" in value or value.startswith("it "):
        return "it_security"
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_") or None


def _build_retrieval_query(description: str, requirements: RequirementDetails) -> str:
    """Build a compact query from the requirement's meaningful content."""
    parts = [
        requirements.policy_name or "",
        requirements.domain or "",
        requirements.purpose or "",
        requirements.scope or "",
        " ".join(requirements.rules),
        " ".join(requirements.stakeholders),
        description,
    ]
    # Keep enough context for retrieval without allowing a long conversation
    # to crowd all useful subject terms out of the search query.
    query = " ".join(part.strip() for part in parts if part and part.strip())
    return query[:2500]


def _as_dict(item):
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return {"value": str(item)}


async def gather_requirements(
    description: str,
    conversation_history: str = "",
) -> GatheringResult:
    """Run extraction once for a session's initial request."""
    client = get_foundry_client()
    prompt = f"""{GATHERING_PROMPT}

ORIGINAL USER REQUEST:
{description}

COMPLETE CONVERSATION HISTORY:
{conversation_history or "No previous conversation."}

Extract the requirement and return the exact JSON contract.
"""
    response = await client.get_response(
        messages=[Message(role="user", contents=[prompt])]
    )

    try:
        gathered = GatheringResult.model_validate_json(response.text)
    except (ValidationError, ValueError) as exc:
        raise ValueError(
            "Gathering Agent returned invalid JSON or an incompatible schema: "
            f"{exc}. Response: {response.text[:2500]}"
        ) from exc

    query = _build_retrieval_query(description, gathered.requirements)
    domain = _retrieval_domain(gathered.requirements.domain)

    evidence, references = await asyncio.gather(
        evidence_retrieval_tool(query=query, domain=domain),
        retrieve_verified_reference_data(query=query, domain=domain or ""),
    )

    evidence_items = [_as_dict(item) for item in evidence]
    reference_items = [_as_dict(item) for item in references]

    # data_status is a record-quality flag, not proof of policy approval.
    verified_references = [
        item for item in reference_items
        if str(item.get("data_status", "")).casefold() == "verified"
    ]

    requirements = gathered.requirements.model_copy(
        update={"reference_data": verified_references}
    )

    return gathered.model_copy(update={
        "requirements": requirements,
        "evidence": evidence_items,
        "reference_data": verified_references,
        "summary": gathered.summary or (
            f"Extracted {requirements.policy_name or 'the requested requirement'}; "
            f"retrieved {len(evidence_items)} evidence items and "
            f"{len(verified_references)} verified reference records."
        ),
    })
