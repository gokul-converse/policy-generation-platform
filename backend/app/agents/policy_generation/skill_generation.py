"""Generate reusable draft skills from validated requirements."""

import json
import re
from typing import Any

from agent_framework import Agent
from app.clients.foundry_client import get_foundry_client
from app.common.logger import get_logger
from app.context.skill_provider import create_skill_generation_provider
from app.models.skills import GeneratedSkillSet
from app.prompts.skills import SKILL_GENERATOR_INSTRUCTIONS

logger = get_logger(__name__)

REQUIRED_HEADINGS = [
    "# ",
    "## Purpose",
    "## Instructions",
    "## Source Requirements",
]

PLACEHOLDERS = (
    "[TODO]",
    "[TBD]",
    "TODO:",
    "TBD:",
    "INSERT HERE",
    "PLACEHOLDER",
)




def _normalize_requirements(
    validated_requirements: dict[str, Any] | list[Any] | Any,
) -> dict[str, Any]:
    """Normalize supported inputs and remove irrelevant envelope fields."""

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
        raise ValueError("Unsupported validated_requirements type.")

    if not isinstance(raw_requirements, list) or not raw_requirements:
        raise ValueError("A non-empty requirements list is required.")

    compact_requirements: list[dict[str, str]] = []

    for item in raw_requirements:
        if isinstance(item, dict):
            requirement = item

        elif hasattr(item, "model_dump"):
            requirement = item.model_dump()

        else:
            raise ValueError(
                "Each requirement must be a dictionary or model."
            )

        requirement_id = requirement.get("requirement_id")
        requirement_text = requirement.get("text")

        if not isinstance(requirement_id, str) or not requirement_id.strip():
            raise ValueError(
                "Every requirement needs a valid requirement_id."
            )

        if not isinstance(requirement_text, str) or not requirement_text.strip():
            raise ValueError(
                f"Requirement {requirement_id!r} needs non-empty text."
            )

        compact_requirements.append(
            {
                "requirement_id": requirement_id.strip(),
                "text": requirement_text.strip(),
            }
        )

    return {"requirements": compact_requirements}


def validate_requirement_input(
    validated_requirements: dict[str, Any],
) -> set[str]:
    """Validate input and collect known requirement IDs."""

    if not isinstance(validated_requirements, dict):
        raise ValueError("Requirements input must be a dictionary.")

    requirements = validated_requirements.get("requirements")

    if not isinstance(requirements, list) or not requirements:
        raise ValueError(
            "Input must contain a non-empty 'requirements' list."
        )

    known_ids: set[str] = set()

    for requirement in requirements:
        if not isinstance(requirement, dict):
            raise ValueError("Each requirement must be a dictionary.")

        requirement_id = requirement.get("requirement_id")
        text = requirement.get("text")

        if not isinstance(requirement_id, str) or not requirement_id.strip():
            raise ValueError(
                "Every requirement needs a valid requirement_id."
            )

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Requirement {requirement_id!r} needs non-empty text."
            )

        if requirement_id in known_ids:
            raise ValueError(
                f"Duplicate requirement ID: {requirement_id}"
            )

        known_ids.add(requirement_id)

    return known_ids


def canonicalize_source_requirements(
    skill_set: GeneratedSkillSet,
    validated_requirements: dict[str, Any],
) -> None:
    """
    Rebuild source requirement sections using authoritative input text.

    The model must select valid requirement IDs, but it must not be
    trusted to reproduce the original requirement wording.
    """

    requirement_text_by_id = {
        requirement["requirement_id"]: requirement["text"]
        for requirement in validated_requirements["requirements"]
    }

    for skill in skill_set.skills:
        unknown_ids = (
            set(skill.requirement_ids) - set(requirement_text_by_id)
        )

        if unknown_ids:
            raise ValueError(
                f"Skill {skill.name!r} contains unknown requirement IDs: "
                f"{sorted(unknown_ids)}"
            )

        source_lines = [
            f"- {requirement_id}: "
            f"{requirement_text_by_id[requirement_id]}"
            for requirement_id in skill.requirement_ids
        ]

        source_section = (
            "## Source Requirements\n\n"
            + "\n".join(source_lines)
        )

        body = skill.instructions.strip()

        heading = "## Source Requirements"
        heading_position = body.find(heading)

        if heading_position >= 0:
            body = body[:heading_position].rstrip()

        skill.instructions = (
            f"{body}\n\n{source_section}"
        )



def validate_generated_skill_set(
    skill_set: GeneratedSkillSet,
    validated_requirements: dict[str, Any],
    known_requirement_ids: set[str],
) -> None:
    """Validate generated metadata, one-to-one requirement mapping,
    coverage and Markdown structure.
    """

    if not skill_set.skills:
        raise ValueError("The generated skill set is empty.")

    requirement_text_by_id = {
        requirement["requirement_id"]: requirement["text"]
        for requirement in validated_requirements["requirements"]
    }

    names = [skill.name for skill in skill_set.skills]

    if len(names) != len(set(names)):
        raise ValueError("Generated skill names must be unique.")

    # ---------------------------------------------------------
    # 1. Enforce one requirement ID = exactly one generated skill
    # ---------------------------------------------------------

    if len(skill_set.skills) != len(known_requirement_ids):
        raise ValueError(
            "One-to-one requirement mapping failed. "
            f"Expected {len(known_requirement_ids)} skills, "
            f"but generated {len(skill_set.skills)}."
        )

    skill_requirement_ids = [
        requirement_id
        for skill in skill_set.skills
        for requirement_id in skill.requirement_ids
    ]

    # Each skill must reference exactly one requirement ID.
    for skill in skill_set.skills:
        if len(skill.requirement_ids) != 1:
            raise ValueError(
                f"Skill {skill.name!r} must reference exactly one "
                f"requirement ID. Found: {skill.requirement_ids}"
            )

    # A requirement ID must not be assigned to multiple skills.
    if len(skill_requirement_ids) != len(set(skill_requirement_ids)):
        raise ValueError(
            "A requirement ID cannot be assigned to multiple skills."
        )

    # Every input requirement must have exactly one generated skill.
    generated_requirement_ids = set(skill_requirement_ids)

    if generated_requirement_ids != known_requirement_ids:
        missing_ids = known_requirement_ids - generated_requirement_ids
        unknown_ids = generated_requirement_ids - known_requirement_ids

        raise ValueError(
            "Generated skills must have an exact one-to-one mapping "
            "with all input requirement IDs. "
            f"Missing IDs: {sorted(missing_ids)}. "
            f"Unknown IDs: {sorted(unknown_ids)}."
        )

    # ---------------------------------------------------------
    # 2. Validate individual skills
    # ---------------------------------------------------------

    covered_requirement_ids: set[str] = set()

    for skill in skill_set.skills:

        if not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*",
            skill.name,
        ):
            raise ValueError(
                f"Skill name {skill.name!r} must use lowercase kebab-case."
            )

        if len(skill.name) > 64:
            raise ValueError(
                f"Skill name {skill.name!r} exceeds 64 characters."
            )

        if not skill.description or not skill.description.strip():
            raise ValueError(
                f"Skill {skill.name!r} has an empty description."
            )

        if not skill.requirement_ids:
            raise ValueError(
                f"Skill {skill.name!r} must reference source requirements."
            )

        unknown_ids = (
            set(skill.requirement_ids) - known_requirement_ids
        )

        if unknown_ids:
            raise ValueError(
                f"Skill {skill.name!r} contains unknown requirement IDs: "
                f"{sorted(unknown_ids)}"
            )

        if len(skill.requirement_ids) != len(set(skill.requirement_ids)):
            raise ValueError(
                f"Skill {skill.name!r} contains duplicate requirement IDs."
            )

        covered_requirement_ids.update(skill.requirement_ids)

        # -----------------------------------------------------
        # 3. Validate Markdown instructions
        # -----------------------------------------------------

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

        positions = []

        for heading in REQUIRED_HEADINGS:
            position = body.find(heading)

            if position == -1:
                raise ValueError(
                    f"Skill {skill.name!r} is missing heading "
                    f"{heading!r}."
                )

            positions.append(position)

        if positions != sorted(positions):
            raise ValueError(
                f"Skill {skill.name!r} has headings in the wrong order."
            )

        # -----------------------------------------------------
        # 4. Validate authoritative source requirement text
        # -----------------------------------------------------

        for requirement_id in skill.requirement_ids:
            original_text = requirement_text_by_id[requirement_id]

            expected_line = (
                f"- {requirement_id}: {original_text}"
            )

            if expected_line not in body:
                raise ValueError(
                    f"Skill {skill.name!r} must preserve the original text "
                    f"for requirement {requirement_id!r}."
                )

    # ---------------------------------------------------------
    # 5. Final requirement coverage validation
    # ---------------------------------------------------------

    uncovered_ids = known_requirement_ids - covered_requirement_ids

    if uncovered_ids:
        raise ValueError(
            "The generated skills do not cover all input requirements. "
            f"Uncovered requirement IDs: {sorted(uncovered_ids)}"
        )



def _build_prompt(
    requirements_json: str,
    validation_error: str | None = None,
) -> str:
    """Build an initial generation or repair prompt."""

    if validation_error:
        return (
            "Repair the generated skill set based on the following "
            "validation failure:\n"
            f"{validation_error}\n\n"
            "Preserve valid existing content. Correct the identified "
            "issues without inventing business rules. Ensure all "
            "requirements are covered and source IDs remain valid.\n\n"
            f"Validated requirements:\n{requirements_json}"
        )

    return (
        "Generate reusable operational Agent Skills from these "
        "validated requirements.\n\n"
        "Follow the supplied skill-generation instructions and the "
        "configured company-policy-generator built-in skill.\n"
        "Analyze capability boundaries, consolidate related tasks, "
        "prevent semantic overlap, and preserve requirement traceability.\n\n"
        f"Validated requirements:\n{requirements_json}"
    )




async def generate_skills(
    validated_requirements: dict[str, Any] | list[Any],
    client: Any = None,
    max_retries: int = 3,
) -> GeneratedSkillSet:
    """Generate and validate reusable draft skills."""

    if max_retries < 1:
        raise ValueError("max_retries must be at least 1.")

    requirements = _normalize_requirements(validated_requirements)

    known_ids = validate_requirement_input(requirements)

    logger.info(
        "Generating skills for %d requirements.",
        len(known_ids),
    )

    llm_client = client or get_foundry_client()

    skill_generation_provider = create_skill_generation_provider()

    agent = Agent(
        client=llm_client,
        name="SkillGeneratorAgent",
        instructions=SKILL_GENERATOR_INSTRUCTIONS,
        context_providers=[skill_generation_provider],
        default_options={
            "response_format": GeneratedSkillSet,
        },
    )

    requirements_json = json.dumps(
        requirements,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    validation_error: str | None = None

    for attempt in range(1, max_retries + 1):

        prompt = _build_prompt(
            requirements_json=requirements_json,
            validation_error=validation_error,
        )

        try:
            result = await agent.run(prompt)

            value = getattr(result, "value", None)

            if value is not None:
                skill_set = GeneratedSkillSet.model_validate(value)

            else:
                result_text = getattr(result, "text", None)

                if not result_text:
                    raise ValueError(
                        "Agent returned no structured output."
                    )

                skill_set = GeneratedSkillSet.model_validate_json(
                    result_text
                )

            # Source text is authoritative input data.
            # Rebuild it instead of trusting model-generated wording.
            canonicalize_source_requirements(
                skill_set=skill_set,
                validated_requirements=requirements,
            )

            validate_generated_skill_set(
                skill_set=skill_set,
                validated_requirements=requirements,
                known_requirement_ids=known_ids,
            )

            logger.info(
                "Generated %d valid skills on attempt %d.",
                len(skill_set.skills),
                attempt,
            )

            return skill_set

        except Exception as exc:

            validation_error = str(exc)[:2000]

            logger.warning(
                "Skill generation attempt %d/%d failed: %s",
                attempt,
                max_retries,
                validation_error,
            )

            if attempt == max_retries:
                raise

    raise RuntimeError(
        "Skill generation failed after all attempts."
    )
