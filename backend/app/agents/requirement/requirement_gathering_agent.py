
"""Gather generic requirements using the shared Foundry client."""

import json

from agent_framework import Message
from pydantic import ValidationError

from app.agents.requirement.prompts.gathering_prompt import GATHERING_PROMPT
from app.agents.requirement.tools.evidence_retrieval_tool import (
    evidence_retrieval_tool,
)
from app.clients.foundry_client import get_foundry_client
from app.schemas.requirements import GatheringResult


async def gather_requirements(
    description: str,
    conversation_history: str = "",
) -> GatheringResult:
    """Extract requirements from the original request and conversation history."""
    client = get_foundry_client()

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
  "summary": "string"
}}

Requirements:
- Use the exact schema and field types shown above.
- Use arrays of strings for stakeholders, rules, and unresolved_details.
- The domain is an open-ended string; do not restrict it to a predefined list.
- Generate a concise, natural title from the actual requirement.
- Do not use a fixed domain-to-policy-name mapping or a closed catalogue.
- Keep thresholds, approval conditions, dates, and detailed rules out
  of the title unless they are essential to the recognized artifact name.
- Keep the purpose, scope, stakeholders, rules, and unresolved details
  separate and consistent.
- Preserve information from earlier answers unless the user corrects it.
- Do not treat assumptions or retrieved evidence as user-approved facts.
- Never invent missing values, organizational rules, or approval limits.
- Use null for an unknown name, purpose, or scope when the schema permits it.
- Return valid JSON only, without Markdown fences or extra text.
"""
                ],
            )
        ]
    )

    raw_text = response.text

    try:
        gathered = GatheringResult.model_validate_json(raw_text)
    except (ValidationError, ValueError) as exc:
        raise ValueError(
            "Requirement gathering agent returned invalid JSON or an "
            f"incompatible schema. Details: {exc}. "
            f"Raw response: {raw_text[:3000]}"
        ) from exc

    requirements = gathered.requirements

    evidence_query = " ".join(
        part.strip()
        for part in (
            description,
            requirements.policy_name or "",
            requirements.purpose or "",
            requirements.scope or "",
            " ".join(requirements.stakeholders),
            " ".join(requirements.rules),
            " ".join(requirements.unresolved_details),
        )
        if part and part.strip()
    )

    evidence = await evidence_retrieval_tool(
        query=evidence_query,
        domain=requirements.domain,
    )

    return gathered.model_copy(
        update={
            "evidence": [
                json.dumps(item, ensure_ascii=False)
                for item in evidence
            ]
        }
    )
