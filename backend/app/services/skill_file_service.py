"""Utilities for building SKILL.md content."""

import yaml


def build_skill_markdown(generated_skill) -> str:
    """
    Build complete SKILL.md content from a generated skill.

    The returned Markdown contains YAML frontmatter followed
    by the skill instructions. The repository will store it
    in the database.
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