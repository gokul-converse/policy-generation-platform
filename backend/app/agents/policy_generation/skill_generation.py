"""
Skill generation orchestration.

This module coordinates the complete skill-generation workflow.

Responsibilities:
    1. Normalize validated requirement input.
    2. Enforce one-to-one requirement-to-skill mapping.
    3. Generate structured skills using the Skill Generator Agent.
    4. Reconstruct Source Requirements from authoritative input.
    5. Perform deterministic structural validation.
    6. Perform independent semantic validation.
    7. Retry generation when validation fails.

This module does not:
    - Modify source requirements.
    - Persist Skill or SkillVersion records.
    - Approve or activate skills.
    - Change business rules.
"""

import json
import re
from typing import Any

from agent_framework import Agent
from app.agents.policy_generation.skill_validation import (
    validate_generated_skills,
)
from app.clients.foundry_client import get_foundry_client
from app.common.logger import get_logger
from app.context.skill_provider import create_skill_generation_provider
from app.models.skills import GeneratedSkillSet
from app.prompts.skills import SKILL_GENERATOR_INSTRUCTIONS

logger = get_logger(__name__)


# ============================================================
# Constants
# ============================================================

REQUIRED_HEADINGS = (
    "# ",
    "## Purpose",
    "## Instructions",
    "## Source Requirements",
)

SOURCE_REQUIREMENTS_HEADING = "## Source Requirements"

PLACEHOLDERS = (
    "[TODO]",
    "[TBD]",
    "TODO:",
    "TBD:",
    "INSERT HERE",
    "PLACEHOLDER",
)

SKILL_NAME_PATTERN = re.compile(
    r"[a-z0-9]+(?:-[a-z0-9]+)*"
)
SKILL_CHARACTER_LIMIT = 64
MAX_GENERATION_RETRIES = 3

# ============================================================
# Exceptions
# ============================================================


class SkillValidationNeedsClarificationError(ValueError):
    """
    Raised when source requirements lack information needed
    to generate a correct skill.

    This is different from a normal generation failure:
    the business requirement itself needs clarification.
    """


# ============================================================
# 1. Requirement normalization
# ============================================================


def _normalize_requirements(
    validated_requirements: dict[str, Any] | list[Any] | Any,
) -> dict[str, Any]:
    """
    Normalize supported requirement inputs.

    Supported input formats:
        - A list of requirement dictionaries.
        - A dictionary containing a 'requirements' list.
        - A Pydantic model containing a 'requirements' list.

    Output format:
        {
            "requirements": [
                {
                    "requirement_id": "REQ-001",
                    "text": "Original validated requirement text"
                }
            ]
        }

    Only requirement IDs and original text are retained because
    these are the fields required by the skill-generation workflow.

    Raises:
        ValueError: If the input structure is invalid.
    """

    if isinstance(validated_requirements, list):
        raw_requirements = validated_requirements

    elif isinstance(validated_requirements, dict):
        raw_requirements = validated_requirements.get("requirements")

    elif hasattr(validated_requirements, "model_dump"):
        dumped = validated_requirements.model_dump()

        if not isinstance(dumped, dict):
            raise ValueError(
                "Requirements model must serialize to a dictionary."
            )

        raw_requirements = dumped.get("requirements")

    else:
        raise ValueError(
            "Unsupported validated_requirements type."
        )

    if not isinstance(raw_requirements, list) or not raw_requirements:
        raise ValueError(
            "A non-empty requirements list is required."
        )

    normalized: list[dict[str, str]] = []

    for item in raw_requirements:

        if isinstance(item, dict):
            requirement = item

        elif hasattr(item, "model_dump"):
            requirement = item.model_dump()

        else:
            raise ValueError(
                "Each requirement must be a dictionary or Pydantic model."
            )

        requirement_id = requirement.get("requirement_id")
        requirement_text = requirement.get("text")

        if (
            not isinstance(requirement_id, str)
            or not requirement_id.strip()
        ):
            raise ValueError(
                "Every requirement needs a valid requirement_id."
            )

        if (
            not isinstance(requirement_text, str)
            or not requirement_text.strip()
        ):
            raise ValueError(
                f"Requirement {requirement_id!r} needs non-empty text."
            )

        normalized.append(
            {
                "requirement_id": requirement_id.strip(),
                "text": requirement_text.strip(),
            }
        )

    return {"requirements": normalized}


# ============================================================
# 2. Requirement input validation
# ============================================================


def validate_requirement_input(
    validated_requirements: dict[str, Any],
) -> set[str]:
    """
    Validate normalized requirements and return their unique IDs.

    Checks:
        - The input contains a non-empty requirements list.
        - Each requirement has an ID and text.
        - Requirement IDs are unique.

    Returns:
        Set of known requirement IDs.
    """

    if not isinstance(validated_requirements, dict):
        raise ValueError(
            "Requirements input must be a dictionary."
        )

    requirements = validated_requirements.get("requirements")

    if not isinstance(requirements, list) or not requirements:
        raise ValueError(
            "Input must contain a non-empty 'requirements' list."
        )

    known_ids: set[str] = set()

    for requirement in requirements:

        if not isinstance(requirement, dict):
            raise ValueError(
                "Each requirement must be a dictionary."
            )

        requirement_id = requirement.get("requirement_id")
        requirement_text = requirement.get("text")

        if (
            not isinstance(requirement_id, str)
            or not requirement_id.strip()
        ):
            raise ValueError(
                "Every requirement needs a valid requirement_id."
            )

        if (
            not isinstance(requirement_text, str)
            or not requirement_text.strip()
        ):
            raise ValueError(
                f"Requirement {requirement_id!r} needs non-empty text."
            )

        requirement_id = requirement_id.strip()

        if requirement_id in known_ids:
            raise ValueError(
                f"Duplicate requirement ID: {requirement_id}"
            )

        known_ids.add(requirement_id)

    return known_ids


# ============================================================
# 3. Reconstruct authoritative Source Requirements
# ============================================================


def canonicalize_source_requirements(
    skill_set: GeneratedSkillSet,
    validated_requirements: dict[str, Any],
) -> None:
    """
    Rebuild each skill's Source Requirements section.

    The LLM selects the requirement ID associated with a skill.
    Python reconstructs the original requirement text.

    This prevents the model from accidentally changing or
    paraphrasing authoritative source requirement wording.

    The existing Instructions content is retained.
    """

    requirement_text_by_id = {
        requirement["requirement_id"]: requirement["text"]
        for requirement in validated_requirements["requirements"]
    }

    for skill in skill_set.skills:

        unknown_ids = (
            set(skill.requirement_ids)
            - set(requirement_text_by_id)
        )

        if unknown_ids:
            raise ValueError(
                f"Skill {skill.name!r} contains unknown requirement IDs: "
                f"{sorted(unknown_ids)}"
            )

        # Reconstruct the source section using the original input.
        source_lines = [
            f"- {requirement_id}: "
            f"{requirement_text_by_id[requirement_id]}"
            for requirement_id in skill.requirement_ids
        ]

        source_section = (
            f"{SOURCE_REQUIREMENTS_HEADING}\n\n"
            + "\n".join(source_lines)
        )

        body = skill.instructions.strip()

        # Remove any Source Requirements section generated by the LLM.
        # Python replaces it with the authoritative original text.
        heading_position = body.find(SOURCE_REQUIREMENTS_HEADING)

        if heading_position >= 0:
            body = body[:heading_position].rstrip()

        skill.instructions = (
            f"{body}\n\n{source_section}"
        )


# ============================================================
# 4. Validate generated skill mapping
# ============================================================


def _validate_requirement_mapping(
    skill_set: GeneratedSkillSet,
    known_requirement_ids: set[str],
) -> None:
    """
    Enforce exactly one skill per requirement ID.

    Each skill must:
        - Reference exactly one requirement ID.
        - Reference a known requirement.
        - Have a unique mapping.

    The complete generated mapping must match the input mapping.
    """

    if len(skill_set.skills) != len(known_requirement_ids):
        raise ValueError(
            "One-to-one requirement mapping failed. "
            f"Expected {len(known_requirement_ids)} skills, "
            f"but generated {len(skill_set.skills)}."
        )

    generated_ids: list[str] = []

    for skill in skill_set.skills:

        if len(skill.requirement_ids) != 1:
            raise ValueError(
                f"Skill {skill.name!r} must reference exactly one "
                f"requirement ID. Found: {skill.requirement_ids}"
            )

        generated_ids.extend(skill.requirement_ids)

    if len(generated_ids) != len(set(generated_ids)):
        raise ValueError(
            "A requirement ID cannot be assigned to multiple skills."
        )

    generated_requirement_ids = set(generated_ids)

    if generated_requirement_ids != known_requirement_ids:

        missing_ids = (
            known_requirement_ids - generated_requirement_ids
        )

        unknown_ids = (
            generated_requirement_ids - known_requirement_ids
        )

        raise ValueError(
            "Generated skills must have an exact one-to-one mapping "
            "with all input requirement IDs. "
            f"Missing IDs: {sorted(missing_ids)}. "
            f"Unknown IDs: {sorted(unknown_ids)}."
        )


# ============================================================
# 5. Validate individual skill content
# ============================================================


def _validate_skill_content(skill: Any) -> None:
    """
    Validate the name, description, and Markdown structure of one skill.

    These checks are deterministic. They do not replace
    independent semantic validation.
    """

    if not SKILL_NAME_PATTERN.fullmatch(skill.name):
        raise ValueError(
            f"Skill name {skill.name!r} must use lowercase kebab-case."
        )

    if len(skill.name) > SKILL_CHARACTER_LIMIT:
        raise ValueError(
            f"Skill name {skill.name!r} exceeds {SKILL_CHARACTER_LIMIT} characters."
        )

    if not skill.description or not skill.description.strip():
        raise ValueError(
            f"Skill {skill.name!r} has an empty description."
        )

    body = skill.instructions.strip()

    if not body:
        raise ValueError(
            f"Skill {skill.name!r} has empty instructions."
        )

    if body.startswith("---"):
        raise ValueError(
            f"Skill {skill.name!r} must not contain YAML frontmatter "
            "inside instructions."
        )

    upper_body = body.upper()

    for placeholder in PLACEHOLDERS:

        if placeholder in upper_body:
            raise ValueError(
                f"Skill {skill.name!r} contains placeholder "
                f"{placeholder}."
            )

    # Verify all required headings exist in the expected order.
    heading_positions: list[int] = []

    for heading in REQUIRED_HEADINGS:

        position = body.find(heading)

        if position == -1:
            raise ValueError(
                f"Skill {skill.name!r} is missing heading {heading!r}."
            )

        heading_positions.append(position)

    if heading_positions != sorted(heading_positions):
        raise ValueError(
            f"Skill {skill.name!r} has headings in the wrong order."
        )


# ============================================================
# 6. Validate complete generated skill set
# ============================================================


def validate_generated_skill_set(
    skill_set: GeneratedSkillSet,
    validated_requirements: dict[str, Any],
    known_requirement_ids: set[str],
) -> None:
    """
    Run deterministic validation on the complete generated skill set.

    Validation includes:
        1. Unique skill names.
        2. One-to-one requirement mapping.
        3. Valid skill metadata.
        4. Required Markdown headings.
        5. Original source requirement preservation.

    Semantic correctness is checked separately by the
    Skill Validation Agent.
    """

    if not skill_set.skills:
        raise ValueError(
            "The generated skill set is empty."
        )

    # Check that every skill name is unique.
    names = [skill.name for skill in skill_set.skills]

    if len(names) != len(set(names)):
        raise ValueError(
            "Generated skill names must be unique."
        )

    # Check requirement-to-skill mapping.
    _validate_requirement_mapping(
        skill_set=skill_set,
        known_requirement_ids=known_requirement_ids,
    )

    requirement_text_by_id = {
        requirement["requirement_id"]: requirement["text"]
        for requirement in validated_requirements["requirements"]
    }

    # Validate every individual skill.
    for skill in skill_set.skills:

        _validate_skill_content(skill)

        # Verify that the original requirement text is present.
        for requirement_id in skill.requirement_ids:

            original_text = requirement_text_by_id[requirement_id]

            expected_line = (
                f"- {requirement_id}: {original_text}"
            )

            if expected_line not in skill.instructions:
                raise ValueError(
                    f"Skill {skill.name!r} must preserve the original "
                    f"text for requirement {requirement_id!r}."
                )


# ============================================================
# 7. Build generation and repair prompts
# ============================================================


def _build_prompt(
    requirements_json: str,
    validation_error: str | None = None,
    previous_skill_set_json: str | None = None,
) -> str:
    """
    Build the prompt for either initial generation or repair.

    Initial generation:
        Generates skills from validated requirements.

    Repair:
        Corrects a previous output using structural or
        semantic validation findings.

    The original requirements are included in both cases
    so they remain the authoritative source.
    """

    if validation_error:

        previous_output = (
            previous_skill_set_json
            or "No previous generated skill output is available."
        )

        return f"""
REPAIR THE PREVIOUSLY GENERATED SKILL SET.

The previous output failed validation.

Review:
1. The original validated requirements.
2. The previous generated skills.
3. The validation findings.

PREVIOUS GENERATED SKILL SET:
{previous_output}

VALIDATION FINDINGS:
{validation_error}

REPAIR RULES:

- Correct every identified validation failure.
- Preserve valid instructions from the previous output.
- Do not unnecessarily rewrite valid content.
- Do not introduce new business rules.
- Do not change authoritative requirement meaning.
- Preserve requirement IDs.
- Preserve original requirement wording.
- Preserve numeric values, dates, units, conditions,
  exceptions, obligations, and scope.

STRICT MAPPING RULES:

- Generate exactly one skill for each unique requirement ID.
- Each skill must reference exactly one requirement ID.
- Do not merge different requirement IDs.
- Do not create duplicate skills.
- Do not omit any requirement ID.
- Do not introduce unknown requirement IDs.

AUTHORITATIVE VALIDATED REQUIREMENTS:
{requirements_json}

Return the complete corrected skill set using the
GeneratedSkillSet structured output format.
"""

    return f"""
Generate enterprise-ready, reusable operational Agent Skills
from the supplied validated requirements.

REQUIREMENT MAPPING:

- Generate exactly one skill per unique requirement ID.
- Each skill must map to exactly one requirement ID.
- Do not combine multiple requirement IDs into one skill.
- Do not create multiple skills for the same requirement.
- Preserve original requirement IDs and meaning.

SKILL QUALITY:

- Define a clear purpose and scope.
- Provide actionable, reusable instructions.
- Preserve all supported conditions and constraints.
- Define responsibility boundaries.
- Identify prohibited assumptions.
- Identify unresolved business decisions.
- Avoid generic and repetitive instructions.

Follow the configured company-policy-generator built-in skill
and the supplied Skill Generator instructions.

AUTHORITATIVE VALIDATED REQUIREMENTS:
{requirements_json}

Return only GeneratedSkillSet structured output.
"""


# ============================================================
# 8. Parse structured Agent response
# ============================================================


def _parse_generated_skill_set(
    result: Any,
) -> GeneratedSkillSet:
    """
    Convert the Agent Framework response into GeneratedSkillSet.

    Supports:
        - Structured response value.
        - JSON text response.

    Raises:
        ValueError: If the agent returns empty or invalid output.
    """

    response_value = getattr(result, "value", None)

    if response_value is not None:
        return GeneratedSkillSet.model_validate(response_value)

    response_text = getattr(result, "text", None)

    if not response_text:
        raise ValueError(
            "Skill Generator Agent returned no structured output."
        )

    return GeneratedSkillSet.model_validate_json(response_text)


# ============================================================
# 9. Create Skill Generator Agent
# ============================================================


def _create_skill_generator_agent(
    client: Any,
) -> Agent:
    """
    Initialize the Skill Generator Agent.

    The skill generation provider supplies the reusable
    company-policy-generator skill context.
    """

    skill_generation_provider = create_skill_generation_provider()

    return Agent(
        client=client,
        name="SkillGeneratorAgent",
        instructions=SKILL_GENERATOR_INSTRUCTIONS,
        context_providers=[skill_generation_provider],
        default_options={
            "response_format": GeneratedSkillSet,
        },
    )


# ============================================================
# 10. Main skill generation workflow
# ============================================================


async def generate_skills(
    validated_requirements: dict[str, Any] | list[Any],
    client: Any = None,
    max_retries: int = MAX_GENERATION_RETRIES,
) -> GeneratedSkillSet:
    """
    Generate and validate reusable Agent Skills.

    Workflow:
        1. Normalize validated requirements.
        2. Validate requirement IDs.
        3. Initialize the Skill Generator Agent.
        4. Generate structured skills.
        5. Reconstruct authoritative Source Requirements.
        6. Run deterministic validation.
        7. Run independent semantic validation.
        8. Repair and retry when validation returns FAIL.

    Retry behavior:
        Structural failure:
            Retry generation with validation findings.

        Semantic FAIL:
            Retry generation with semantic findings.

        NEEDS_CLARIFICATION:
            Stop immediately because source requirements
            need clarification.

        PASS:
            Return the validated skill set.

    Args:
        validated_requirements:
            Authoritative validated requirements.

        client:
            Optional Agent Framework client.

        max_retries:
            Maximum number of generation attempts.

    Returns:
        GeneratedSkillSet:
            Successfully generated and validated skills.

    Raises:
        ValueError:
            If generation or validation fails.

        SkillValidationNeedsClarificationError:
            If source requirements need clarification.
    """

    if max_retries < 1:
        raise ValueError(
            "max_retries must be at least 1."
        )

    # Step 1: Normalize and validate requirements.
    requirements = _normalize_requirements(
        validated_requirements
    )

    known_ids = validate_requirement_input(requirements)

    logger.info(
        "Starting skill generation for %d requirements.",
        len(known_ids),
    )

    # Step 2: Initialize the LLM client and generator agent.
    llm_client = client or get_foundry_client()

    agent = _create_skill_generator_agent(
        client=llm_client
    )

    requirements_json = json.dumps(
        requirements,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    # State retained across retry attempts.
    validation_error: str | None = None
    previous_skill_set_json: str | None = None

    # Step 3: Generate and validate.
    for attempt in range(1, max_retries + 1):

        logger.info(
            "Skill generation attempt %d/%d.",
            attempt,
            max_retries,
        )

        prompt = _build_prompt(
            requirements_json=requirements_json,
            validation_error=validation_error,
            previous_skill_set_json=previous_skill_set_json,
        )

        # ----------------------------------------------------
        # 3.1 Generate structured skill output
        # ----------------------------------------------------

        try:
            result = await agent.run(prompt)

            skill_set = _parse_generated_skill_set(result)

            # Preserve the model output for possible repair.
            previous_skill_set_json = skill_set.model_dump_json(
                indent=2
            )

            # Replace generated source text with authoritative text.
            canonicalize_source_requirements(
                skill_set=skill_set,
                validated_requirements=requirements,
            )

            # Run deterministic validation.
            validate_generated_skill_set(
                skill_set=skill_set,
                validated_requirements=requirements,
                known_requirement_ids=known_ids,
            )

        except Exception as exc:

            validation_error = (
                "Generation or structural validation failed: "
                f"{str(exc)[:2000]}"
            )

            logger.warning(
                "Skill generation failed on attempt %d/%d: %s",
                attempt,
                max_retries,
                validation_error,
            )

            if attempt == max_retries:
                raise ValueError(
                    "Skill generation failed after all attempts. "
                    f"Last error: {validation_error}"
                ) from exc

            continue

        # ----------------------------------------------------
        # 3.2 Independent semantic validation
        # ----------------------------------------------------

        # Keep semantic validation outside the generation exception
        # handler. An Azure or network error must not be treated as
        # a semantic failure and retried as if the skill were invalid.
        validation_result = await validate_generated_skills(
            validated_requirements=requirements,
            generated_skill_set=skill_set,
            client=llm_client,
        )

        validation_status = validation_result.overall_status

        # ----------------------------------------------------
        # 3.3 PASS: return validated skills
        # ----------------------------------------------------

        if validation_status == "PASS":

            logger.info(
                "Skill generation completed successfully. "
                "Attempt: %d | Skills: %d",
                attempt,
                len(skill_set.skills),
            )

            return skill_set

        # ----------------------------------------------------
        # 3.4 NEEDS_CLARIFICATION: stop generation
        # ----------------------------------------------------

        if validation_status == "NEEDS_CLARIFICATION":

            clarification_details = [
                finding.model_dump(mode="json")
                for finding in validation_result.findings
            ]

            logger.warning(
                "Skill generation requires clarification. "
                "Findings: %s",
                len(clarification_details),
            )

            raise SkillValidationNeedsClarificationError(
                "Skill generation stopped because authoritative "
                "requirements need clarification. "
                "Resolve the following items before generating skills: "
                f"{json.dumps(clarification_details, ensure_ascii=False)}"
            )

        # ----------------------------------------------------
        # 3.5 FAIL: prepare repair prompt
        # ----------------------------------------------------

        if validation_status == "FAIL":

            validation_findings = [
                finding.model_dump(mode="json")
                for finding in validation_result.findings
            ]

            validation_error = json.dumps(
                validation_findings,
                ensure_ascii=False,
                indent=2,
            )

            logger.warning(
                "Semantic skill validation failed. "
                "Attempt: %d/%d | Findings: %d",
                attempt,
                max_retries,
                len(validation_findings),
            )

            if attempt == max_retries:
                raise ValueError(
                    "Generated skills failed semantic validation "
                    f"after {max_retries} attempts: "
                    f"{validation_error}"
                )

            continue

        # Defensive check if the validation response schema changes.
        raise ValueError(
            f"Unsupported skill validation status: {validation_status!r}"
        )

    raise RuntimeError(
        "Skill generation failed after all validation attempts."
    )
