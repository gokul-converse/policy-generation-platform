
"""Gather generic requirements using the shared Foundry client."""

import json

from agent_framework import Message
from pydantic import ValidationError

from app.agents.requirement.prompts.gathering_prompt import (
    GATHERING_PROMPT,
)
from app.agents.requirement.tools.evidence_retrieval_tool import (
    evidence_retrieval_tool,
)
from app.clients.foundry_client import get_foundry_client
from app.schemas.requirements import GatheringResult


async def gather_requirements(
    description: str,
    conversation_history: str = "",
) -> GatheringResult:
    """Extract and update requirements using the full conversation."""
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

Return exactly one JSON object in this structure:
{{
  "requirements": {{
    "policy_name": "string or null",
    "domain": "hr, finance, it_security, or general",
    "purpose": "string or null",
    "scope": "string or null",
    "stakeholders": ["string"],
    "rules": ["string"],
    "unresolved_details": ["string"]
  }},
  "evidence": [],
  "summary": "string"
}}

Output constraints:
- stakeholders, rules, and unresolved_details must be arrays of strings.
- Do not place objects inside those arrays.
- Preserve information already supplied in previous answers.
- Keep unapproved assumptions distinguishable from confirmed facts.
- Return valid JSON only. No Markdown fences.
"""
                ],
            )
        ]
    )

    raw_text = response.text

    try:
        gathered = GatheringResult.model_validate_json(raw_text)
    except ValidationError as exc:
        raise ValueError(
            "Requirement gathering agent returned invalid JSON "
            f"or an incompatible schema. Details: {exc}. "
            f"Raw response: {raw_text[:3000]}"
        ) from exc

    requirements = gathered.requirements

    # Retrieve evidence after extracting a query from the user's request
    # and current requirements. Evidence is reference material only.
    evidence_query = " ".join(
        value
        for value in (
            description,
            requirements.policy_name or "",
            requirements.purpose or "",
            requirements.scope or "",
            " ".join(requirements.rules),
        )
        if value.strip()
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
