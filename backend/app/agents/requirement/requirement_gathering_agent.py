"""Extract the initial requirement, then retrieve supporting context."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from agent_framework import Message
from pydantic import ValidationError

from app.agents.requirement.prompts.gathering_prompt import GATHERING_PROMPT
from app.agents.requirement.tools.evidence_retrieval_tool import evidence_retrieval_tool
from app.clients.foundry_client import get_foundry_client
from app.schemas.requirements import GatheringResult, RequirementDetails
from app.services.requirement_reference_service import retrieve_verified_reference_data

logger = logging.getLogger(__name__)

_PLACEHOLDER_PHRASES = (
    "shall define",
    "should define",
    "must define",
    "shall specify",
    "should specify",
    "must specify",
    "shall cover",
    "should cover",
    "must cover",
    "needs to define",
    "needs to specify",
    "to be determined",
    "to be decided",
    "to be confirmed",
    "to be defined",
    "to be clarified",
    "to be finalized",
    "to be resolved",
    "tbd",
    "will be defined",
    "will be specified",
    "will be determined",
    "shall be determined",
    "shall be decided",
    "as per company policy",
    "as per policy",
    "per policy",
)


def _extract_json_block(text: str) -> str:
    """Extract clean JSON object from model response, stripping markdown code fences."""
    raw = (text or "").strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return raw[first_brace : last_brace + 1].strip()
    return raw


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
    query = " ".join(part.strip() for part in parts if part and part.strip())
    return query[:2500]


def _as_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return {"value": str(item)}


def _clean_extracted_requirements(req: RequirementDetails) -> RequirementDetails:
    """
    Ensure placeholder statements erroneously placed in rules are
    moved to unresolved_details so rules contain only confirmed decisions.
    """
    confirmed_rules: list[str] = []
    unresolved = list(req.unresolved_details)
    seen_unresolved = {" ".join(u.casefold().split()) for u in unresolved}

    for rule in req.rules:
        is_placeholder = any(phrase in rule.casefold() for phrase in _PLACEHOLDER_PHRASES)
        if is_placeholder:
            norm_rule = " ".join(rule.casefold().split())
            if norm_rule not in seen_unresolved:
                unresolved.append(f"{rule} (unresolved business decision)")
                seen_unresolved.add(norm_rule)
        else:
            confirmed_rules.append(rule)

    return req.model_copy(
        update={
            "rules": confirmed_rules,
            "unresolved_details": unresolved,
        }
    )


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

    clean_json = _extract_json_block(response.text)

    try:
        gathered = GatheringResult.model_validate_json(clean_json)
    except (ValidationError, ValueError) as exc:
        raise ValueError(
            "Gathering Agent returned invalid JSON or an incompatible schema: "
            f"{exc}. Response: {response.text[:2500]}"
        ) from exc

    # Sanitize any placeholder rules into unresolved_details
    cleaned_req = _clean_extracted_requirements(gathered.requirements)

    query = _build_retrieval_query(description, cleaned_req)
    domain = _retrieval_domain(cleaned_req.domain)

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

    # Reference data is stored for schema compatibility and audit only.
    # It is NEVER used to populate or infer business rules.
    requirements = cleaned_req.model_copy(
        update={"reference_data": verified_references}
    )

    return gathered.model_copy(update={
        "requirements": requirements,
        "evidence": evidence_items,
        "reference_data": verified_references,
        "summary": gathered.summary or (
            f"Extracted {requirements.policy_name or 'the requested requirement'}; "
            f"identified {len(requirements.rules)} confirmed rules and "
            f"{len(requirements.unresolved_details)} unresolved items."
        ),
    })
