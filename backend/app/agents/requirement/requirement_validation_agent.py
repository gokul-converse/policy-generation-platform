
"""Validate generic requirements using conversation-aware reasoning."""

from agent_framework import Message

from app.agents.requirement.prompts.validation_prompt import (
    VALIDATION_PROMPT,
)
from app.clients.foundry_client import get_foundry_client
from app.schemas.requirements import GatheringResult, ValidationResult


async def validate_requirements(
    gathered: GatheringResult,
    conversation_history: str = "",
) -> ValidationResult:
    """Choose a new clarification question or prepare a review draft."""
    client = get_foundry_client()

    response = await client.get_response(
        messages=[
            Message(
                role="user",
                contents=[
                    f"""
{VALIDATION_PROMPT}

Latest gathered requirements:
{gathered.model_dump_json(indent=2)}

Complete conversation and structured clarification history:
{conversation_history or "No previous conversation."}

Use the history to identify:
- Details already provided by the user.
- Questions already asked and their answers.
- Topics that remain unresolved.
- Important unanswered topics that have not been asked before.

Return one JSON object with:
- status: "needs_clarification" or "ready_for_confirmation"
- missing_details: list of strings
- question: one question or null
- draft: structured requirements or null
- explanation: string

For needs_clarification:
- Return exactly one new, non-repeated question.
- Return draft as null.

For ready_for_confirmation:
- Return question as null.
- Return a draft matching the RequirementDetails schema.
- Preserve unresolved details and unconfirmed assumptions.

Never mark requirements as confirmed.
Return valid JSON only, without Markdown fences.
"""
                ],
            )
        ]
    )

    result = ValidationResult.model_validate_json(response.text)

    if result.status == "needs_clarification":
        if not result.question or not result.question.strip():
            raise ValueError(
                "Validation requires clarification but returned no question."
            )

        if result.draft is not None:
            raise ValueError(
                "Clarification response must not contain a draft."
            )

    if result.status == "ready_for_confirmation":
        if result.draft is None:
            raise ValueError(
                "Validation returned no draft for confirmation."
            )

        if result.question is not None:
            raise ValueError(
                "Draft response must not contain a clarification question."
            )

    return result
