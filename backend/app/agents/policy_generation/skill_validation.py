"""
Skill semantic validation agent.

Responsibilities:
    1. Normalize authoritative validated requirements.
    2. Prepare the validation prompt.
    3. Execute the Skill Validation Agent.
    4. Parse its structured response.
    5. Verify that findings reference valid requirement IDs.

This module performs semantic validation.

It does not modify or rewrite generated skills.
"""

import json
from typing import Any

from agent_framework import Agent
from app.clients.foundry_client import get_foundry_client
from app.common.logger import get_logger
from app.models.skills import (
    GeneratedSkillSet,
    SkillValidationResult,
)
from app.prompts.skills import SKILL_VALIDATION_INSTRUCTIONS

logger = get_logger(__name__)


# ============================================================
# 1. Requirement normalization
# ============================================================


def _normalize_validation_requirements(
    validated_requirements: dict[str, Any] | list[Any],
) -> dict[str, Any]:
    """
    Convert supported requirement inputs into a normalized dictionary.

    Supported inputs:
        1. A list of requirement dictionaries/models.
        2. A dictionary containing a 'requirements' list.
        3. A dictionary keyed by requirement ID.

    Returns:
        Dictionary keyed by requirement ID.

    Raises:
        ValueError: If requirements are missing, invalid, or duplicated.
    """

    if isinstance(validated_requirements, list):
        requirements = validated_requirements

    elif isinstance(validated_requirements, dict):
        requirements = validated_requirements.get("requirements")

        # Support dictionaries keyed directly by requirement ID.
        if requirements is None:
            requirements = [
                {
                    "requirement_id": requirement_id,
                    **(
                        requirement
                        if isinstance(requirement, dict)
                        else {"requirement_text": requirement}
                    ),
                }
                for requirement_id, requirement
                in validated_requirements.items()
            ]

    else:
        raise ValueError(
            "Validated requirements must be a dictionary or a list."
        )

    if not isinstance(requirements, list) or not requirements:
        raise ValueError("No validated requirements were provided.")

    normalized_requirements: dict[str, Any] = {}

    for requirement in requirements:

        # Convert Pydantic objects into dictionaries.
        if hasattr(requirement, "model_dump"):
            requirement = requirement.model_dump(mode="json")

        elif hasattr(requirement, "dict"):
            requirement = requirement.dict()

        if not isinstance(requirement, dict):
            raise ValueError(
                "Each validated requirement must be a dictionary."
            )

        requirement_id = str(
            requirement.get("requirement_id", "")
        ).strip()

        requirement_text = str(
            requirement.get("requirement_text")
            or requirement.get("text")
            or ""
        ).strip()

        if not requirement_id:
            raise ValueError(
                "A validated requirement is missing requirement_id."
            )

        if not requirement_text:
            raise ValueError(
                f"Requirement '{requirement_id}' has no requirement text."
            )

        if requirement_id in normalized_requirements:
            raise ValueError(
                f"Duplicate requirement ID found: {requirement_id}"
            )

        normalized_requirements[requirement_id] = {
            **requirement,
            "requirement_id": requirement_id,
            "requirement_text": requirement_text,
        }

    return normalized_requirements


# ============================================================
# 2. Validation response checks
# ============================================================


def _validate_finding_requirement_ids(
    validation_result: SkillValidationResult,
    known_requirement_ids: set[str],
) -> None:
    """
    Ensure every validation finding references a known requirement.

    The validation agent must not invent requirement IDs.
    """

    for finding in validation_result.findings:

        requirement_id = finding.requirement_id.strip()

        if requirement_id not in known_requirement_ids:
            raise ValueError(
                "Skill Validation Agent returned a finding for an "
                f"unknown requirement ID: {requirement_id}"
            )


def _parse_validation_response(
    result: Any,
) -> SkillValidationResult:
    """
    Parse the Agent Framework response into SkillValidationResult.

    Supports both structured response values and JSON text responses.
    """

    response_value = getattr(result, "value", None)

    if response_value is not None:
        return SkillValidationResult.model_validate(response_value)

    response_text = getattr(result, "text", None)

    if not response_text:
        raise ValueError(
            "Skill Validation Agent returned no structured output."
        )

    return SkillValidationResult.model_validate_json(response_text)


# ============================================================
# 3. Validation prompt construction
# ============================================================


def _build_validation_prompt(
    validated_requirements: dict[str, Any],
    generated_skill_set: GeneratedSkillSet,
) -> str:
    """
    Build the input supplied to the Skill Validation Agent.

    Validated requirements are authoritative.
    Generated skills are the content being evaluated.
    """

    requirements_json = json.dumps(
        list(validated_requirements.values()),
        ensure_ascii=False,
        indent=2,
    )

    skills_data = generated_skill_set.model_dump(mode="json")

    skills_json = json.dumps(
        skills_data,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
Validate the generated skills against the authoritative validated
requirements.

AUTHORITATIVE VALIDATED REQUIREMENTS:
{requirements_json}

GENERATED SKILLS:
{skills_json}

VALIDATION RULES:

1. Treat the validated requirements as the only source of truth.
2. Verify that every requirement has exactly one corresponding skill.
3. Verify that each skill maps to the correct requirement ID.
4. Check that the meaning of each requirement is preserved.
5. Check all numeric values, dates, durations, units, conditions,
   responsibilities, obligations, exceptions, and approval rules.
6. Identify unsupported instructions or invented business rules.
7. Identify missing requirement details or altered meaning.
8. Identify conflicts or unintended overlaps between skills.
9. Do not assume missing business information.
10. Do not rewrite or correct the generated skills.

Return only the structured SkillValidationResult.
"""


# ============================================================
# 4. Public validation operation
# ============================================================


async def validate_generated_skills(
    validated_requirements: dict[str, Any] | list[Any],
    generated_skill_set: GeneratedSkillSet,
    client: Any = None,
) -> SkillValidationResult:
    """
    Independently validate generated skills against validated requirements.

    Workflow:
        1. Normalize validated requirements.
        2. Build the semantic validation prompt.
        3. Initialize the Skill Validation Agent.
        4. Execute the agent.
        5. Parse the structured result.
        6. Validate requirement references.
        7. Return the validation result.

    Args:
        validated_requirements:
            Authoritative requirements used to generate the skills.

        generated_skill_set:
            Skills that need semantic validation.

        client:
            Optional Agent Framework client.
            The default Foundry client is used when omitted.

    Returns:
        SkillValidationResult:
            Structured semantic validation result.

    Raises:
        ValueError:
            If the requirements or agent response are invalid.
    """

    # Step 1: Normalize the authoritative requirements.
    normalized_requirements = _normalize_validation_requirements(
        validated_requirements
    )

    known_requirement_ids = set(normalized_requirements.keys())

    # Step 2: Prepare the validation input.
    prompt = _build_validation_prompt(
        validated_requirements=normalized_requirements,
        generated_skill_set=generated_skill_set,
    )

    # Step 3: Resolve the LLM client.
    llm_client = client or get_foundry_client()

    # Step 4: Initialize the validation agent.
    agent = Agent(
        client=llm_client,
        name="SkillValidationAgent",
        instructions=SKILL_VALIDATION_INSTRUCTIONS,
        default_options={
            "response_format": SkillValidationResult,
        },
    )

    logger.info(
        "Starting semantic skill validation. Requirements: %s | Skills: %s",
        len(normalized_requirements),
        len(generated_skill_set.skills),
    )

    # Step 5: Execute semantic validation.
    result = await agent.run(prompt)

    # Step 6: Parse the agent response.
    validation_result = _parse_validation_response(result)

    # Step 7: Verify that all findings reference valid requirements.
    _validate_finding_requirement_ids(
        validation_result=validation_result,
        known_requirement_ids=known_requirement_ids,
    )

    logger.info(
        "Skill semantic validation completed. "
        "Status: %s | Findings: %s",
        validation_result.overall_status,
        len(validation_result.findings),
    )

    return validation_result
