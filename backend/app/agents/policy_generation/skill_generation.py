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
from app.prompts.skills import SKILL_GENERATOR_INSTRUCTIONS
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


def create_skill_design_provider() -> SkillsProvider | None:
    """Load generic skill-design guidance when available.

    Prefer a generic skill-creator skill. The existing company-policy skill
    remains a compatibility fallback for projects that have not added one.
    If neither exists, generation can proceed using the system prompt alone.
    """
    backend_root = Path(settings.BACKEND_ROOT).resolve()
    skills_root = backend_root / "skills"

    preferred_names = (
        "company-policy-generator",
    )

    for skill_name in preferred_names:
        skill_dir = skills_root / skill_name
        skill_file = skill_dir / "SKILL.md"

        if not skill_file.is_file():
            continue

        if skill_name == "company-policy-generator":
            logger.warning(
                "Generic skill-creator guidance was not found; "
                "using company-policy-generator as a compatibility fallback."
            )

        return SkillsProvider.from_paths(
            skill_paths=[skill_dir],
            disable_load_skill_approval=True,
            disable_read_skill_resource_approval=True,
        )

    logger.info(
        "No built-in skill-design provider found; using prompt-only generation."
    )
    return None


# Backward-compatible alias for existing callers.
create_company_policy_generator_provider = create_skill_design_provider


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



def canonicalize_source_requirements(
    skill_set: GeneratedSkillSet,
    validated_requirements: dict[str, Any],
) -> None:
    """
    Rebuild each skill's Source Requirements section from authoritative input.

    The LLM creates skill guidance, but Python owns exact source-text copying.
    This avoids retrying when a model paraphrases source requirement text.
    """
    requirement_text_by_id = {
        item["requirement_id"]: item["text"]
        for item in validated_requirements["requirements"]
    }

    for skill in skill_set.skills:
        # Let the validator report invalid/duplicate/unknown IDs clearly.
        if (
            not skill.requirement_ids
            or len(skill.requirement_ids) != len(set(skill.requirement_ids))
            or any(rid not in requirement_text_by_id for rid in skill.requirement_ids)
        ):
            continue

        original_lines = skill.instructions.splitlines()
        kept_lines: list[str] = []
        inside_source_section = False

        # Remove existing Source Requirements section(s), retaining any later
        # non-source sections so the final validator can assess their order.
        for line in original_lines:
            stripped = line.strip()

            if stripped == "## Source Requirements":
                inside_source_section = True
                continue

            if inside_source_section:
                # Source Requirements is a level-2 section. Resume if another
                # level-2 heading appears after it.
                if stripped.startswith("## "):
                    inside_source_section = False
                    kept_lines.append(line)
                else:
                    continue
            else:
                kept_lines.append(line)

        while kept_lines and not kept_lines[-1].strip():
            kept_lines.pop()

        source_lines = ["", "## Source Requirements"]
        source_lines.extend(
            f"- {requirement_id}: {requirement_text_by_id[requirement_id]}"
            for requirement_id in skill.requirement_ids
        )

        skill.instructions = "\n".join(kept_lines + source_lines).strip() + "\n"


REPAIR_CHECKLIST = """
Correct the validation error in the previous output.

Mandatory rules:
1. Each skill must have a descriptive H1 title as its first non-empty line.
2. Include exactly one of each heading, in this order:
   ## Purpose
   ## Instructions
   ## Source Requirements
3. Replace every placeholder with complete, requirement-supported content.
4. Never output [INSERT], [TODO], [PLACEHOLDER], or template instructions.
5. Preserve valid skill names, descriptions, requirement IDs, and exact
   source requirement text.
6. Cover every input requirement. Do not invent policy rules.
7. Return only output matching the required schema.

Fix the reported error and preserve all content that already passes validation.
"""


def _build_prompt(
    requirements_json: str,
    validation_error: str | None = None,
    previous_output_json: str | None = None,
) -> str:
    """Build a compact generation or repair prompt."""

    if validation_error:
        previous_output_block = (
            f"Your previous output was:\n{previous_output_json}\n"
            if previous_output_json
            else ""
        )

        return (
            "Repair the structured skill output. The validation failure "
            f"was:\n{validation_error}\n"
            f"{previous_output_block}"
            f"{REPAIR_CHECKLIST}\n"
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
    skill_provider = create_skill_design_provider()
    agent = Agent(
        client=llm_client,
        name="SkillGeneratorAgent",
        instructions=SKILL_GENERATOR_INSTRUCTIONS,
        context_providers=[skill_provider] if skill_provider is not None else [],
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
    previous_output_json: str | None = None

    for attempt in range(1, max_retries + 1):
        prompt = _build_prompt(
            requirements_json=requirements_json,
            validation_error=validation_error,
            previous_output_json=previous_output_json,
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

            # Keep the raw attempt available for the next repair prompt,
            # even if this attempt goes on to fail validation below.
            previous_output_json = skill_set.model_dump_json()

            # Source text is deterministic data, not LLM-authored content.
            # Rebuild it before validation so exact traceability is reliable
            # for any skill domain, not just company-policy skills.
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
