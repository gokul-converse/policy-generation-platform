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

def _normalize_validation_requirements(
    validated_requirements: dict[str, Any] | list[Any],
) -> dict[str, Any]:
    """
    Normalize validated requirements into a dictionary keyed by requirement_id.

    The validated requirements are the authoritative source for validation.
    """

    if isinstance(validated_requirements, list):
        requirements = validated_requirements

    elif isinstance(validated_requirements, dict):
        requirements = validated_requirements.get("requirements")

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
                for requirement_id, requirement in validated_requirements.items()
            ]

    else:
        raise ValueError(
            "Validated requirements must be a dictionary or a list."
        )

    if not isinstance(requirements, list) or not requirements:
        raise ValueError("No validated requirements were provided.")

    normalized: dict[str, Any] = {}

    for requirement in requirements:
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

        if requirement_id in normalized:
            raise ValueError(
                f"Duplicate requirement ID found: {requirement_id}"
            )

        normalized[requirement_id] = {
            **requirement,
            "requirement_id": requirement_id,
            "requirement_text": requirement_text,
        }

    return normalized


def _validate_finding_requirement_ids(
    validation_result: SkillValidationResult,
    known_requirement_ids: set[str],
) -> None:
    """
    Ensure that the semantic validator references only known requirement IDs.
    """

    for finding in validation_result.findings:
        requirement_id = finding.requirement_id.strip()

        if requirement_id not in known_requirement_ids:
            raise ValueError(
                "Skill Validation Agent returned a finding for an "
                f"unknown requirement ID: {requirement_id}"
            )


def _build_validation_prompt(
    validated_requirements: dict[str, Any],
    generated_skill_set: GeneratedSkillSet,
) -> str:
    """
    Build the independent semantic validation input.
    """

    requirements_json = json.dumps(
        list(validated_requirements.values()),
        ensure_ascii=False,
        indent=2,
    )

    if hasattr(generated_skill_set, "model_dump"):
        skills_data = generated_skill_set.model_dump(mode="json")
    else:
        skills_data = generated_skill_set.dict()

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


async def validate_generated_skills(
    validated_requirements: dict[str, Any] | list[Any],
    generated_skill_set: GeneratedSkillSet,
    client: Any = None,
) -> SkillValidationResult:
    """
    Independently validate generated skills against validated requirements.

    PASS:
        All generated skills comply with the requirements.

    FAIL:
        The generated skills contain unsupported, altered, missing,
        conflicting, or otherwise non-compliant content.

    NEEDS_CLARIFICATION:
        The authoritative requirements do not provide enough information
        to determine whether the generated skills are correct.
    """

    normalized_requirements = _normalize_validation_requirements(
        validated_requirements
    )

    known_requirement_ids = set(normalized_requirements.keys())

    prompt = _build_validation_prompt(
        validated_requirements=normalized_requirements,
        generated_skill_set=generated_skill_set,
    )

    llm_client = client or get_foundry_client()

    agent = Agent(
        client=llm_client,
        name="SkillValidationAgent",
        instructions=SKILL_VALIDATION_INSTRUCTIONS,
        default_options={
            "response_format": SkillValidationResult,
        },
    )

    logger.info(
        "Starting semantic skill validation for %s requirements.",
        len(normalized_requirements),
    )

    result = await agent.run(prompt)

    value = getattr(result, "value", None)

    if value is not None:
        validation_result = SkillValidationResult.model_validate(value)

    else:
        result_text = getattr(result, "text", None)

        if not result_text:
            raise ValueError(
                "Skill Validation Agent returned no structured output."
            )

        validation_result = SkillValidationResult.model_validate_json(
            result_text
        )

    _validate_finding_requirement_ids(
        validation_result=validation_result,
        known_requirement_ids=known_requirement_ids,
    )

    logger.info(
        "Skill semantic validation completed. Status: %s | Findings: %s",
        validation_result.overall_status,
        len(validation_result.findings),
    )

    return validation_result
