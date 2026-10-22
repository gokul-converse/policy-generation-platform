"""Generate reusable draft skills from validated requirements."""

import json
import re
from typing import Any

from agent_framework import Agent
from app.clients.foundry_client import get_foundry_client
from app.common.logger import get_logger
from app.models.skills import GeneratedSkillSet

logger = get_logger(__name__)


SKILL_GENERATOR_INSTRUCTIONS = """
You are a Skill Generation Agent.

Your task is to generate reusable Agent Skills from validated requirements.
Every generated skill will be saved as a SKILL.md file.

## 1. Requirement fidelity

1. Generate skills only from the supplied requirements.
2. Group related requirements into reusable skills.
3. Do not invent business rules, deadlines, limits, eligibility criteria,
   exceptions, or approval processes.
4. Preserve every supplied number, condition, and exception exactly.
5. Do not silently resolve conflicting or ambiguous requirements.
6. Do not add unrelated skills.
7. Generate draft skills only; never claim that a skill is approved.

## 2. Skill metadata

For every skill:

1. Use lowercase kebab-case for the name.
2. Limit the name to 64 characters.
3. Provide a concise description explaining the skill's purpose and when
   it should be used.
4. Include only requirement IDs explicitly supplied in the input.
5. Never invent, rename, modify, or omit IDs for requirements covered
   by the skill.
6. Include the original requirement text in the source requirements
   section of the Markdown body.

## 3. Mandatory Markdown body format

The `instructions` field MUST contain a Markdown body with these headings
in this order:

# <Human-readable Skill Title>

## Purpose
Explain what the skill does using only the supplied requirements.

## Instructions
Provide clear, reusable, actionable instructions for policy generation.
Preserve the meaning and all specified facts and conditions.
Do not introduce unsupported policy rules.
If information is missing or ambiguous, instruct the policy generator
to identify the gap instead of making an assumption.

## Source Requirements
List each source requirement covered by this skill using this format:

- <requirement_id>: <original requirement text>

The original requirement text must be preserved faithfully.

## 4. Markdown formatting rules

1. Use valid Markdown.
2. Use the exact heading names and order specified above.
3. Do not put YAML frontmatter in the `instructions` field.
4. Do not include opening or closing YAML `---` delimiters in the body.
5. Do not wrap the Markdown body in code fences.
6. Do not add commentary before or after the Markdown body.
7. Do not omit a required section.
8. Do not create extra policy details simply to make a skill look complete.

## 5. Structured output contract

Return structured output matching GeneratedSkillSet.

Each generated skill must provide:
- name
- description
- instructions
- requirement_ids

The `instructions` field contains the complete Markdown body described
above. The application will create YAML frontmatter from the metadata
and combine it with this body to produce SKILL.md.

Return only the requested structured skill data.
"""


REQUIRED_HEADINGS = [
    "# ",
    "## Purpose",
    "## Instructions",
    "## Source Requirements",
]


def validate_requirement_input(
    validated_requirements: dict[str, Any],
) -> set[str]:
    """Validate the temporary input contract and collect valid IDs."""

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
            raise ValueError("Every requirement needs a valid requirement_id.")

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


def validate_generated_skill_set(
    skill_set: GeneratedSkillSet,
    validated_requirements: dict[str, Any],
    known_requirement_ids: set[str],
) -> None:
    """Validate skill metadata, requirement references, and Markdown body."""

    requirement_text_by_id = {
        requirement["requirement_id"]: requirement["text"]
        for requirement in validated_requirements["requirements"]
    }

    names = [skill.name for skill in skill_set.skills]

    if len(names) != len(set(names)):
        raise ValueError("Generated skill names must be unique.")

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

        if not skill.requirement_ids:
            raise ValueError(
                f"Skill {skill.name!r} must reference source requirements."
            )

        unknown_ids = set(skill.requirement_ids) - known_requirement_ids

        if unknown_ids:
            raise ValueError(
                f"Skill {skill.name!r} contains unknown requirement IDs: "
                f"{sorted(unknown_ids)}"
            )

        if len(skill.requirement_ids) != len(set(skill.requirement_ids)):
            raise ValueError(
                f"Skill {skill.name!r} contains duplicate requirement IDs."
            )

        body = skill.instructions.strip()

        # Reject placeholder tokens
        for placeholder in ["[TODO", "[TBD", "[INSERT", "[PLACEHOLDER"]:
            if placeholder in body.upper():
                raise ValueError(
                    f"Skill {skill.name!r} contains placeholder text ({placeholder})."
                )

        if body.startswith("---"):
            raise ValueError(
                f"Skill {skill.name!r} must not include YAML frontmatter "
                "inside instructions."
            )

        # Validate the required Markdown heading order.
        heading_positions = []

        for heading in REQUIRED_HEADINGS:
            position = body.find(heading)

            if position == -1:
                raise ValueError(
                    f"Skill {skill.name!r} is missing required heading "
                    f"{heading!r}."
                )

            heading_positions.append(position)

        if heading_positions != sorted(heading_positions):
            raise ValueError(
                f"Skill {skill.name!r} has headings in the wrong order."
            )

        # Require every referenced source requirement to appear in the body
        # with its original text. This is a basic traceability check.
        for requirement_id in skill.requirement_ids:
            original_text = requirement_text_by_id[requirement_id]
            expected_line = f"- {requirement_id}: {original_text}"

            if expected_line not in body:
                raise ValueError(
                    f"Skill {skill.name!r} must include the original text "
                    f"for requirement {requirement_id!r} under "
                    "Source Requirements."
                )


async def generate_skills(
    validated_requirements: dict[str, Any] | list[Any],
    client: Any = None,
    max_retries: int = 2,
) -> GeneratedSkillSet:
    """Generate and validate draft skills from validated requirements with automatic retries."""

    logger.info("Starting skill generation agent.")

    # Normalize to dict format if passed as a list or Pydantic model
    if isinstance(validated_requirements, list):
        req_list = [
            r if isinstance(r, dict) else (r.model_dump() if hasattr(r, "model_dump") else dict(r))
            for r in validated_requirements
        ]
        norm_requirements = {"requirements": req_list}
    elif isinstance(validated_requirements, dict):
        norm_requirements = validated_requirements
    elif hasattr(validated_requirements, "model_dump"):
        norm_requirements = validated_requirements.model_dump()
    else:
        raise ValueError("Unsupported validated_requirements type.")

    known_requirement_ids = validate_requirement_input(norm_requirements)
    logger.info(
        "Validated %d requirements for skill generation.",
        len(known_requirement_ids),
    )

    llm_client = client or get_foundry_client()

    agent = Agent(
        client=llm_client,
        name="SkillGeneratorAgent",
        instructions=SKILL_GENERATOR_INSTRUCTIONS,
        default_options={
            "response_format": GeneratedSkillSet,
        },
    )

    prompt_msg = (
        "Generate reusable draft skills for these validated requirements. "
        "Follow the required Markdown body structure exactly. "
        "Use only the supplied requirement IDs and preserve their original "
        "text in the Source Requirements section.\n\n"
        + json.dumps(norm_requirements, indent=2, ensure_ascii=False)
    )

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            result = await agent.run(prompt_msg)

            if getattr(result, "value", None) is not None:
                skill_set = GeneratedSkillSet.model_validate(result.value)
            else:
                skill_set = GeneratedSkillSet.model_validate_json(result.text)

            validate_generated_skill_set(
                skill_set=skill_set,
                validated_requirements=norm_requirements,
                known_requirement_ids=known_requirement_ids,
            )

            logger.info(
                "Skill generation agent produced %d validated skills on attempt %d.",
                len(skill_set.skills),
                attempt,
            )
            return skill_set
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Skill generation attempt %d/%d failed validation: %s",
                attempt,
                max_retries,
                exc,
            )
            if attempt == max_retries:
                raise last_error
            prompt_msg = (
                f"Previous skill generation attempt failed with error:\n{exc}\n\n"
                "Please fix this issue and generate reusable draft skills:\n\n"
                + json.dumps(norm_requirements, indent=2, ensure_ascii=False)
            )

    raise last_error or RuntimeError("Skill generation failed after retries.")
