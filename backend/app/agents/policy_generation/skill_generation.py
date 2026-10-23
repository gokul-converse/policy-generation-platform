"""Generate reusable draft skills from validated requirements."""

import json
import re
from pathlib import Path
from typing import Any

from agent_framework import Agent, SkillsProvider
from app.clients.foundry_client import get_foundry_client
from app.common.logger import get_logger
from app.config.settings import settings
from app.models.skills import GeneratedSkillSet
from pydantic import ValidationError

logger = get_logger(__name__)

REQUIRED_HEADINGS = [
    "## Purpose",
    "## Instructions",
    "## Source Requirements",
]

PLACEHOLDERS = [
    "[INSERT",
    "[TODO",
    "[PLACEHOLDER",
    "YOUR_COMPANY_NAME",
    "YOUR_ORGANIZATION",
]

SKILL_GENERATOR_INSTRUCTIONS = """
You generate reusable draft Agent Skills from validated requirements.

When creating or refining a reusable Agent Skill, consult the available
skill-creator skill for guidance on SKILL.md structure, YAML frontmatter,
actionable instructions, and progressive disclosure.

Treat confirmed requirements as the source of truth.

Preserve requirement IDs, numeric values, units, dates, currencies,
conditions, exceptions, and constraints exactly.

Do not invent business rules, organizational facts, approval processes,
deadlines, or unsupported requirements.

If required information is missing or contradictory, identify the issue
instead of making assumptions.

Generate only the minimum useful set of reusable skills. Related
requirements may be grouped into one skill when appropriate.

Each skill must have:
- A unique lowercase kebab-case name.
- A concise description explaining when the skill should be used.
- Actionable instructions suitable for an Agent.
- A descriptive Markdown H1 title.
- The required headings in the specified order.
- A Source Requirements section containing the exact original requirement
  text, using one bullet per referenced requirement:
  - REQUIREMENT_ID: original requirement text

Every input requirement must be represented by at least one generated skill.
Every skill must reference only requirement IDs supplied in the input.

Do not include YAML frontmatter inside the instructions field.
The application creates the SKILL.md frontmatter when saving the skill.

Return output matching the GeneratedSkillSet schema.
"""


def create_skill_creator_provider() -> SkillsProvider:
    """Load the trusted built-in skill-creator guidance."""

    backend_root = Path(settings.BACKEND_ROOT).resolve()
    skill_creator_dir = backend_root / "skills" / "skill-creator"
    skill_creator_file = skill_creator_dir / "SKILL.md"

    if not skill_creator_file.is_file():
        raise FileNotFoundError(
            f"Required skill-creator file was not found: "
            f"{skill_creator_file}"
        )

    return SkillsProvider.from_paths(
        skill_paths=[skill_creator_dir],
        disable_load_skill_approval=True,
        disable_read_skill_resource_approval=True,
    )


def _normalize_requirements(
    validated_requirements: dict[str, Any] | list[Any] | Any,
) -> dict[str, Any]:
    """Normalize supported inputs and retain required requirement fields."""

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
    """Validate the normalized requirements and collect their IDs."""

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

        if requirement_id in known_ids:
            raise ValueError(
                f"Duplicate requirement ID: {requirement_id}"
            )

        known_ids.add(requirement_id)

    return known_ids


def validate_generated_skill_set(
    skill_set: GeneratedSkillSet,
    validated_requirements: dict[str, Any],
    known_requirement_ids: set[str],
) -> None:
    """Validate skill metadata, traceability, and Markdown structure."""

    requirement_text_by_id = {
        requirement["requirement_id"]: requirement["text"]
        for requirement in validated_requirements["requirements"]
    }

    names = [skill.name.casefold() for skill in skill_set.skills]

    if len(names) != len(set(names)):
        raise ValueError("Generated skill names must be unique.")

    covered_requirement_ids: set[str] = set()

    for skill in skill_set.skills:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill.name):
            raise ValueError(
                f"Skill name {skill.name!r} must use lowercase kebab-case."
            )

        if len(skill.name) > 64:
            raise ValueError(
                f"Skill name {skill.name!r} exceeds 64 characters."
            )

        if not skill.description.strip():
            raise ValueError(
                f"Skill {skill.name!r} has an empty description."
            )

        if not skill.instructions.strip():
            raise ValueError(
                f"Skill {skill.name!r} has empty instructions."
            )

        if not skill.requirement_ids:
            raise ValueError(
                f"Skill {skill.name!r} must reference source requirements."
            )

        if len(skill.requirement_ids) != len(set(skill.requirement_ids)):
            raise ValueError(
                f"Skill {skill.name!r} contains duplicate requirement IDs."
            )

        unknown_ids = set(skill.requirement_ids) - known_requirement_ids

        if unknown_ids:
            raise ValueError(
                f"Skill {skill.name!r} contains unknown requirement IDs: "
                f"{sorted(unknown_ids)}"
            )

        covered_requirement_ids.update(skill.requirement_ids)

        body = skill.instructions.strip()

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

        lines = body.splitlines()

        # Require a meaningful H1 title as the first non-empty line.
        first_line = next(
            (line.strip() for line in lines if line.strip()),
            "",
        )

        if not first_line.startswith("# ") or first_line == "#":
            raise ValueError(
                f"Skill {skill.name!r} must start with a descriptive H1 title."
            )

        # Require exactly one occurrence of each mandatory heading,
        # in the required order.
        heading_positions: list[int] = []

        for heading in REQUIRED_HEADINGS:
            matching_positions = [
                index
                for index, line in enumerate(lines)
                if line.strip() == heading
            ]

            if len(matching_positions) != 1:
                raise ValueError(
                    f"Skill {skill.name!r} must contain exactly one "
                    f"{heading!r} heading."
                )

            heading_positions.append(matching_positions[0])

        if heading_positions != sorted(heading_positions):
            raise ValueError(
                f"Skill {skill.name!r} has mandatory headings "
                "in the wrong order."
            )

        # Check that every referenced requirement's original text is
        # present as a bullet under the Source Requirements heading.
        source_heading_position = heading_positions[-1]
        source_lines = lines[source_heading_position + 1 :]

        for requirement_id in skill.requirement_ids:
            original_text = requirement_text_by_id[requirement_id]
            expected_line = f"- {requirement_id}: {original_text}"

            if expected_line not in source_lines:
                raise ValueError(
                    f"Skill {skill.name!r} must preserve the original "
                    f"text for requirement {requirement_id!r} in its "
                    "Source Requirements section."
                )

    uncovered_ids = known_requirement_ids - covered_requirement_ids

    if uncovered_ids:
        raise ValueError(
            "Generated skills do not cover all input requirements: "
            f"{sorted(uncovered_ids)}"
        )


def _build_prompt(
    requirements_json: str,
    validation_error: str | None = None,
) -> str:
    """Build a compact generation or repair prompt."""

    if validation_error:
        return (
            "Repair the structured skill output. Correct the following "
            "validation failures:\n"
            f"{validation_error}\n"
            "Return the complete corrected structured output. Preserve "
            "all requirement IDs and original requirement text exactly. "
            "Do not introduce unsupported requirements.\n"
            f"Requirements:\n{requirements_json}"
        )

    return (
        "Generate the minimum useful set of reusable draft skills for "
        "these validated requirements. Group related requirements when "
        "appropriate. Use the available skill-creator guidance. Every "
        "input requirement must be covered by at least one skill. Preserve "
        "source requirement text exactly and follow the required schema.\n"
        f"Requirements:\n{requirements_json}"
    )


async def generate_skills(
    validated_requirements: dict[str, Any] | list[Any],
    client: Any = None,
    max_retries: int = 2,
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
    skill_creator_provider = create_skill_creator_provider()

    agent = Agent(
        client=llm_client,
        name="SkillGeneratorAgent",
        instructions=SKILL_GENERATOR_INSTRUCTIONS,
        context_providers=[skill_creator_provider],
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

        except (ValidationError, ValueError) as exc:
            validation_error = str(exc)[:1500]

            logger.warning(
                "Skill output validation failed on attempt %d/%d: %s",
                attempt,
                max_retries,
                validation_error,
            )

            if attempt == max_retries:
                raise

    raise RuntimeError("Skill generation failed after all attempts.")
