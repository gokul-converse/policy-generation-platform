
"""Utilities for building and modifying SKILL.md content."""

import re

import yaml

SOURCE_REQUIREMENTS_HEADING = "## Source Requirements"

FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)",
    re.DOTALL,
)


def build_skill_markdown(generated_skill) -> str:
    """
    Build the initial SKILL.md during skill generation.

    This function retains the existing initial-generation behaviour.
    """

    name = generated_skill.name.strip()
    description = generated_skill.description.strip()
    instructions = generated_skill.instructions.strip()

    if not name:
        raise ValueError("Skill name cannot be empty.")

    if not description:
        raise ValueError("Skill description cannot be empty.")

    if not instructions:
        raise ValueError("Skill instructions cannot be empty.")

    frontmatter = {
        "name": name,
        "description": description,
        "metadata": {
            "requirement_ids": generated_skill.requirement_ids,
        },
    }

    yaml_content = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
    ).strip()

    return (
        f"---\n"
        f"{yaml_content}\n"
        f"---\n\n"
        f"{instructions}\n"
    )


def split_skill_markdown(content: str) -> tuple[str, str, str]:
    """
    Separate existing SKILL.md into:

    1. Original YAML frontmatter.
    2. Skill instruction body.
    3. Source Requirements section.

    The original YAML frontmatter is preserved as text.
    """

    if not content or not content.strip():
        raise ValueError("Skill content cannot be empty.")

    match = FRONTMATTER_PATTERN.match(content)

    if not match:
        raise ValueError(
            "Invalid SKILL.md: YAML frontmatter is missing or malformed."
        )

    original_frontmatter = match.group(1)

    # Validate YAML without modifying it.
    metadata = yaml.safe_load(original_frontmatter)

    if not isinstance(metadata, dict):
        raise ValueError(
            "Skill YAML frontmatter must contain a mapping."
        )

    body = content[match.end():].strip()

    if not body:
        raise ValueError("Skill body cannot be empty.")

    heading_position = body.find(SOURCE_REQUIREMENTS_HEADING)

    if heading_position == -1:
        raise ValueError(
            "Source Requirements section was not found in SKILL.md."
        )

    instructions = body[:heading_position].strip()
    source_requirements = body[heading_position:].strip()

    if not instructions:
        raise ValueError("Skill instructions cannot be empty.")

    if not source_requirements:
        raise ValueError("Source Requirements cannot be empty.")

    return (
        original_frontmatter,
        instructions,
        source_requirements,
    )



def validate_source_requirements(source_requirements: str) -> str:
    """
    Validate the Source Requirements Markdown section.

    Supports:
    - One requirement per Markdown bullet.
    - Single-line requirement content.
    - Multiline JSON or text continuation within a bullet.

    This function validates structure only. It does not
    approve or verify business requirement changes.
    """

    if not source_requirements or not source_requirements.strip():
        raise ValueError("Source Requirements cannot be empty.")

    source_requirements = source_requirements.strip()
    lines = source_requirements.splitlines()

    if lines[0].strip() != SOURCE_REQUIREMENTS_HEADING:
        raise ValueError(
            "Source Requirements must begin with "
            f"{SOURCE_REQUIREMENTS_HEADING!r}."
        )

    requirement_count = 0
    current_requirement = None

    for line_number, raw_line in enumerate(lines[1:], start=2):
        line = raw_line.strip()

        # Ignore empty lines.
        if not line:
            continue

        # A new requirement must start with a Markdown bullet.
        if line.startswith("- "):

            # Validate the previous requirement before starting
            # the next one.
            if current_requirement is not None:
                if ":" not in current_requirement[2:]:
                    raise ValueError(
                        "Invalid Source Requirement format: "
                        f"{current_requirement}"
                    )

            current_requirement = line
            requirement_count += 1

            # Requirement ID must be present before the colon.
            requirement_id = line[2:].split(":", 1)[0].strip()

            if not requirement_id:
                raise ValueError(
                    f"Missing requirement ID at line {line_number}."
                )

            if ":" not in line[2:]:
                raise ValueError(
                    "Invalid Source Requirement format: "
                    f"{line}"
                )

        else:
            # Continuation lines belong to the previous bullet.
            # This supports multiline JSON and requirement text.
            if current_requirement is None:
                raise ValueError(
                    "Each Source Requirement must use Markdown "
                    "bullet format. "
                    f"Unexpected content at line {line_number}: {line}"
                )

    # Validate the final requirement.
    if current_requirement is not None:
        if ":" not in current_requirement[2:]:
            raise ValueError(
                "Invalid Source Requirement format: "
                f"{current_requirement}"
            )

    if requirement_count == 0:
        raise ValueError(
            "Source Requirements must contain at least one requirement."
        )

    return source_requirements


def rebuild_skill_markdown(
    existing_content: str,
    revised_instructions: str | None = None,
    revised_source_requirements: str | None = None,
) -> str:
    """
    Reconstruct a modified SKILL.md.

    YAML metadata:
        Preserved exactly as it was.

    Instructions:
        Replaced only when revised instructions are supplied.

    Source Requirements:
        Replaced only when revised Source Requirements are supplied.

    No requirement database update is performed here.
    """

    (
        original_frontmatter,
        existing_instructions,
        existing_source_requirements,
    ) = split_skill_markdown(existing_content)

    # Use revised instructions when available.
    instructions = (
        revised_instructions.strip()
        if revised_instructions is not None
        else existing_instructions
    )

    if not instructions:
        raise ValueError("Skill instructions cannot be empty.")

    if SOURCE_REQUIREMENTS_HEADING in instructions.splitlines():
        raise ValueError(
            "Instructions must not contain a Source Requirements section."
        )

    # Use revised Source Requirements when available.
    source_requirements = (
        revised_source_requirements
        if revised_source_requirements is not None
        else existing_source_requirements
    )

    source_requirements = validate_source_requirements(
        source_requirements
    )

    # Preserve original YAML metadata without updating requirement_ids.
    return (
        f"---\n"
        f"{original_frontmatter}\n"
        f"---\n\n"
        f"{instructions.strip()}\n\n"
        f"{source_requirements}\n"
    )
