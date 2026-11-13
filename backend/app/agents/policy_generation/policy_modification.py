"""Agents for understanding policy feedback and modifying skill content."""

import json
from functools import lru_cache
from typing import Any, Literal

from agent_framework import Agent
from app.clients.foundry_client import get_foundry_client
from app.prompts.policy import (
    POLICY_FEEDBACK_UNDERSTANDING_INSTRUCTIONS,
)
from app.prompts.skills import SKILL_MODIFICATION_INSTRUCTIONS
from app.services.skill_file_service import (
    validate_source_requirements,
)
from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Structured outputs
# ============================================================================


class PolicyFeedbackAnalysis(BaseModel):
    """Decision produced by the policy feedback understanding agent."""

    model_config = ConfigDict(extra="forbid")

    requires_skill_modification: bool = Field(
        description=(
            "Whether the existing skill must be modified before "
            "regenerating the complete policy."
        )
    )

    change_scope: Literal[
        "none",
        "instructions",
        "source_requirements",
        "both",
    ] = Field(
        description=(
            "Which part of the existing skill needs modification."
        )
    )

    reason: str = Field(
        min_length=1,
        description="Reason for the modification decision.",
    )

    policy_generation_guidance: str = Field(
        min_length=1,
        description=(
            "Instructions for regenerating the complete policy "
            "after applying the feedback."
        ),
    )


class SkillModificationOutput(BaseModel):
    """Modified skill components returned by the modification agent."""

    model_config = ConfigDict(extra="forbid")

    instructions: str | None = Field(
        default=None,
        description=(
            "Complete revised skill instruction body. "
            "Return null when instructions do not need modification."
        ),
    )

    source_requirements: str | None = Field(
        default=None,
        description=(
            "Complete revised Source Requirements Markdown section, "
            "including its heading. Return null when it does not need "
            "modification."
        ),
    )

    change_summary: str = Field(
        min_length=1,
        description="Summary of the modifications made.",
    )



# ============================================================================
# Agent factories
# ============================================================================


@lru_cache(maxsize=1)
def get_policy_feedback_understanding_agent() -> Agent:
    """Create the feedback understanding agent."""

    return Agent(
        client=get_foundry_client(),
        name="PolicyFeedbackUnderstandingAgent",
        instructions=POLICY_FEEDBACK_UNDERSTANDING_INSTRUCTIONS,
        default_options={
            "response_format": PolicyFeedbackAnalysis,
        },
    )


@lru_cache(maxsize=1)
def get_skill_modification_agent() -> Agent:
    """Create the skill modification agent."""

    return Agent(
        client=get_foundry_client(),
        name="SkillModificationAgent",
        instructions=SKILL_MODIFICATION_INSTRUCTIONS,
        default_options={
            "response_format": SkillModificationOutput,
        },
    )


# ============================================================================
# Structured response parsing
# ============================================================================


def _parse_structured_result(
    result: Any,
    response_model: type[BaseModel],
) -> BaseModel:
    """Parse an Agent Framework structured response."""

    value = getattr(result, "value", None)

    if value is not None:
        return response_model.model_validate(value)

    result_text = getattr(result, "text", None)

    if not result_text:
        raise ValueError(
            "Agent returned neither a structured value nor response text."
        )

    return response_model.model_validate_json(result_text)


# ============================================================================
# Feedback analysis
# ============================================================================



async def analyze_policy_feedback(
    feedback: str,
    existing_skill_instructions: str,
    existing_source_requirements: str,
) -> PolicyFeedbackAnalysis:
    """
    Analyse overall feedback and decide which skill components
    require modification.
    """

    # 1. Validate inputs safely
    def validate_input(value, field_name: str) -> str:
        if value is None:
            raise ValueError(f"{field_name} cannot be None.")

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string, "
                f"received {type(value).__name__}."
            )

        value = value.strip()

        if not value:
            raise ValueError(f"{field_name} cannot be empty.")

        return value

    feedback = validate_input(feedback, "Policy feedback")

    existing_skill_instructions = validate_input(
        existing_skill_instructions,
        "Existing skill instructions",
    )

    existing_source_requirements = validate_input(
        existing_source_requirements,
        "Existing Source Requirements",
    )

    # 2. Prepare prompt data
    prompt_data = {
        "user_feedback": feedback,
        "existing_skill_instructions": existing_skill_instructions,
        "existing_source_requirements": existing_source_requirements,
    }

    # 3. Initialize agent
    agent = get_policy_feedback_understanding_agent()

    if agent is None:
        raise RuntimeError(
            "Policy feedback understanding agent is not initialized."
        )

    # 4. Execute agent
    result = await agent.run(
        "Analyse the following overall policy feedback and decide "
        "whether skill instructions, Source Requirements, or both "
        "need modification.\n\n"
        + json.dumps(
            prompt_data,
            ensure_ascii=False,
            indent=2,
        )
    )

    if result is None:
        raise ValueError(
            "Policy feedback agent returned None."
        )

    # 5. Parse structured response
    try:
        analysis = _parse_structured_result(
            result,
            PolicyFeedbackAnalysis,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(
            f"Failed to parse policy feedback response: {exc}"
        ) from exc

    if analysis is None:
        raise ValueError(
            "Policy feedback analysis returned None."
        )

    # 6. Validate response object
    if not isinstance(analysis, PolicyFeedbackAnalysis):
        raise TypeError(
            "Invalid feedback analysis response. "
            f"Expected PolicyFeedbackAnalysis, "
            f"received {type(analysis).__name__}."
        )

    # 7. Safely access response attributes
    change_scope = getattr(analysis, "change_scope", None)

    requires_skill_modification = getattr(
        analysis,
        "requires_skill_modification",
        None,
    )

    if change_scope is None:
        raise ValueError("Feedback analysis change_scope cannot be None.")

    if requires_skill_modification is None:
        raise ValueError(
            "Feedback analysis requires_skill_modification cannot be None."
        )

    if not isinstance(change_scope, str):
        raise TypeError("change_scope must be a string.")

    if not isinstance(requires_skill_modification, bool):
        raise TypeError(
            "requires_skill_modification must be a boolean."
        )

    # 8. Validate modification scope
    valid_scopes = {
        "none",
        "skill",
        "requirements",
        "both",
    }

    if change_scope not in valid_scopes:
        raise ValueError(
            f"Invalid change_scope: {change_scope}"
        )

    # 9. Validate business logic
    expected_modification = change_scope in {"skill", "both"}

    if requires_skill_modification != expected_modification:
        raise ValueError(
            "Feedback analysis returned inconsistent modification fields."
        )

    return analysis



# ============================================================================
# Skill modification
# ============================================================================



async def modify_skill_content(
    feedback: str,
    existing_instructions: str,
    existing_source_requirements: str,
    change_scope: Literal[
        "instructions",
        "source_requirements",
        "both",
    ],
    change_reason: str,
) -> SkillModificationOutput:
    """
    Modify skill instructions and/or Source Requirements.

    YAML metadata is deliberately excluded.

    When Source Requirements change, the agent may also revise
    instructions if existing hardcoded rules become outdated.
    """

    if not feedback or not feedback.strip():
        raise ValueError("Policy feedback cannot be empty.")

    if not existing_instructions or not existing_instructions.strip():
        raise ValueError("Existing skill instructions cannot be empty.")

    if (
        not existing_source_requirements
        or not existing_source_requirements.strip()
    ):
        raise ValueError("Existing Source Requirements cannot be empty.")

    if change_scope not in {
        "instructions",
        "source_requirements",
        "both",
    }:
        raise ValueError(
            f"Invalid skill modification scope: {change_scope}"
        )

    prompt_data = {
        "user_feedback": feedback.strip(),
        "change_scope": change_scope,
        "change_reason": change_reason,
        "existing_skill_instructions": existing_instructions,
        "existing_source_requirements": existing_source_requirements,
    }

    agent = get_skill_modification_agent()

    result = await agent.run(
        "Modify the requested skill components according to the "
        "user feedback and selected change scope.\n\n"
        "Important: When Source Requirements change, inspect whether "
        "the existing instructions contain hardcoded rules that are "
        "now outdated. Return revised instructions when necessary "
        "to keep the skill internally consistent. Do not invent "
        "requirement IDs or attach new independent requirements "
        "to existing unrelated IDs.\n\n"
        + json.dumps(
            prompt_data,
            ensure_ascii=False,
            indent=2,
        )
    )

    modification = _parse_structured_result(
        result,
        SkillModificationOutput,
    )

    if not isinstance(modification, SkillModificationOutput):
        raise TypeError("Invalid skill modification response.")

    # Validate according to the requested scope.
    if change_scope == "instructions":

        if (
            modification.instructions is None
            or not modification.instructions.strip()
        ):
            raise ValueError(
                "Skill Modification Agent did not return "
                "revised instructions."
            )

        if modification.source_requirements is not None:
            raise ValueError(
                "Agent returned Source Requirements even though "
                "only instructions should change."
            )

    elif change_scope == "source_requirements":

        if (
            modification.source_requirements is None
            or not modification.source_requirements.strip()
        ):
            raise ValueError(
                "Skill Modification Agent did not return "
                "revised Source Requirements."
            )

        # Instructions are optional for this scope.
        # If returned, they must be valid and consistent.

        if modification.instructions is not None:
            if not modification.instructions.strip():
                raise ValueError(
                    "Agent returned empty revised instructions."
                )

    elif change_scope == "both":

        if (
            modification.instructions is None
            or not modification.instructions.strip()
        ):
            raise ValueError("Revised instructions are missing.")

        if (
            modification.source_requirements is None
            or not modification.source_requirements.strip()
        ):
            raise ValueError(
                "Revised Source Requirements are missing."
            )

    # Validate revised Source Requirements structure.
    if modification.source_requirements is not None:
        modification.source_requirements = (
            validate_source_requirements(
                modification.source_requirements
            )
        )

    # Ensure instructions do not contain the Source Requirements section.
    if modification.instructions is not None:
        if any(
            line.strip() == "## Source Requirements"
            for line in modification.instructions.splitlines()
        ):
            raise ValueError(
                "Revised instructions must not contain "
                "the Source Requirements section."
            )

    if not modification.change_summary.strip():
        raise ValueError(
            "Skill Modification Agent returned an empty change summary."
        )

    return modification



def validate_skill_modification_output(
    original_instructions: str,
    original_source_requirements: str,
    revised_instructions: str,
    revised_source_requirements: str,
    change_scope: Literal[
        "none",
        "instructions",
        "source_requirements",
        "both",
    ],
) -> None:
    """
    Validate revised skill content and enforce the requested
    modification scope before creating a new SkillVersion.

    When Source Requirements change, instructions may also change
    if necessary to keep the skill consistent with those requirements.
    """

    if change_scope == "none":
        raise ValueError(
            "Skill modification validation was called "
            "when no skill modification was required."
        )

    original_instructions = original_instructions.strip()
    original_source_requirements = original_source_requirements.strip()
    revised_instructions = revised_instructions.strip()
    revised_source_requirements = revised_source_requirements.strip()

    if not revised_instructions:
        raise ValueError(
            "Revised skill instructions cannot be empty."
        )

    if not revised_source_requirements:
        raise ValueError(
            "Revised Source Requirements cannot be empty."
        )

    if (
        change_scope == "instructions"
        and revised_source_requirements != original_source_requirements
    ):
        raise ValueError(
            "Source Requirements changed even though "
            "only instructions were requested to change."
        )

    if (
        change_scope == "instructions"
        and revised_instructions == original_instructions
    ):
        raise ValueError(
            "The requested skill instruction modification "
            "was not applied."
        )

    if (
        change_scope == "source_requirements"
        and revised_source_requirements == original_source_requirements
    ):
        raise ValueError(
            "The requested Source Requirements modification "
            "was not applied."
        )

    if (
        change_scope == "both"
        and revised_instructions == original_instructions
    ):
        raise ValueError(
            "The requested skill instruction modification "
            "was not applied."
        )

    if (
        change_scope == "both"
        and revised_source_requirements == original_source_requirements
    ):
        raise ValueError(
            "The requested Source Requirements modification "
            "was not applied."
        )

    validate_source_requirements(revised_source_requirements)
