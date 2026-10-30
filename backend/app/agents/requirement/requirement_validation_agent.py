"""Validate gathered requirements and select the next workflow action."""

from agent_framework import Message
from pydantic import ValidationError

from app.agents.requirement.prompts.validation_prompt import VALIDATION_PROMPT
from app.clients.foundry_client import get_foundry_client
from app.schemas.requirements import GatheringResult, ValidationResult


async def validate_requirements(
    gathered: GatheringResult,
    conversation_history: str = "",
) -> ValidationResult:
    """Ask one useful clarification question or prepare a review draft."""
    client = get_foundry_client()

    response = await client.get_response(
        messages=[
            Message(
                role="user",
                contents=[
                    f"""
{VALIDATION_PROMPT}

Latest gathered requirements and reference evidence:
{gathered.model_dump_json(indent=2)}

Complete conversation and structured clarification history:
{conversation_history or "No previous conversation."}

Return one JSON object with:
- status: "needs_clarification" or "ready_for_confirmation"
- missing_details: list of strings
- question: one question or null
- draft: structured requirements or null
- explanation: string

For needs_clarification:
- Return exactly one new, focused question.
- Set draft to null.

For ready_for_confirmation:
- Set question to null.
- Return a draft matching the RequirementDetails schema.

Never mark requirements as confirmed. Return valid JSON only, without
Markdown fences or additional text.
"""
                ],
            )
        ]
    )

    try:
        result = ValidationResult.model_validate_json(response.text)
    except (ValidationError, ValueError) as exc:
        raise ValueError(
            "Requirement validation agent returned invalid JSON or an "
            f"incompatible schema. Details: {exc}. "
            f"Raw response: {response.text[:3000]}"
        ) from exc

    if result.status == "needs_clarification":
        if not result.question or not result.question.strip():
            raise ValueError(
                "Validation requires clarification but returned no question."
            )
        if result.draft is not None:
            raise ValueError(
                "Clarification response must not contain a draft."
            )

    elif result.status == "ready_for_confirmation":
        if result.draft is None:
            raise ValueError(
                "Validation returned no draft for confirmation."
            )
        if result.question is not None:
            raise ValueError(
                "Draft response must not contain a clarification question."
            )

    return result
