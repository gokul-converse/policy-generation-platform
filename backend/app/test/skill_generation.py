
"""Unit tests for generated skill validation."""

import pytest

from app.agents.policy_generation.skill_generation import (
    validate_generated_skill_set,
)
from app.models.skills import GeneratedSkill, GeneratedSkillSet


REQUIREMENTS = {
    "requirements": [
        {
            "requirement_id": "REQ-001",
            "text": "Employees receive 20 days of annual leave.",
        }
    ]
}

KNOWN_IDS = {"REQ-001"}


def create_valid_skill_set() -> GeneratedSkillSet:
    """Return a valid skill with the required Markdown structure."""

    return GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="annual-leave-policy",
                description="Defines annual leave entitlement.",
                instructions=(
                    "# Annual Leave Policy\n\n"
                    "## Purpose\n"
                    "Define the supplied annual leave entitlement.\n\n"
                    "## Instructions\n"
                    "- Preserve the specified entitlement.\n"
                    "- Do not invent additional policy rules.\n\n"
                    "## Source Requirements\n"
                    "- REQ-001: Employees receive 20 days of annual leave."
                ),
                requirement_ids=["REQ-001"],
            )
        ]
    )


def test_valid_skill_is_accepted():
    """Accept a skill with valid metadata and Markdown."""

    skill_set = create_valid_skill_set()

    validate_generated_skill_set(
        skill_set,
        REQUIREMENTS,
        KNOWN_IDS,
    )


def test_unknown_requirement_id_is_rejected():
    """Reject fabricated requirement IDs."""

    skill_set = create_valid_skill_set()
    skill_set.skills[0].requirement_ids = ["REQ-999"]

    with pytest.raises(ValueError, match="unknown requirement IDs"):
        validate_generated_skill_set(
            skill_set,
            REQUIREMENTS,
            KNOWN_IDS,
        )


def test_missing_required_heading_is_rejected():
    """Reject skill bodies that omit a required section."""

    skill_set = create_valid_skill_set()
    skill_set.skills[0].instructions = (
        "# Annual Leave Policy\n\n"
        "## Purpose\n"
        "Define the supplied entitlement.\n\n"
        "## Instructions\n"
        "- Preserve the specified entitlement."
    )

    with pytest.raises(ValueError, match="missing required heading"):
        validate_generated_skill_set(
            skill_set,
            REQUIREMENTS,
            KNOWN_IDS,
        )


def test_original_requirement_text_must_be_preserved():
    """Reject a skill that changes the original requirement text."""

    skill_set = create_valid_skill_set()
    skill_set.skills[0].instructions = (
        "# Annual Leave Policy\n\n"
        "## Purpose\n"
        "Define annual leave.\n\n"
        "## Instructions\n"
        "- Preserve the entitlement.\n\n"
        "## Source Requirements\n"
        "- REQ-001: Employees receive 25 days of annual leave."
    )

    with pytest.raises(ValueError, match="original text"):
        validate_generated_skill_set(
            skill_set,
            REQUIREMENTS,
            KNOWN_IDS,
        )


def test_invalid_skill_name_is_rejected():
    """Reject skill names that do not use lowercase kebab-case."""

    skill_set = create_valid_skill_set()
    skill_set.skills[0].name = "Annual Leave Policy"

    with pytest.raises(ValueError, match="lowercase kebab-case"):
        validate_generated_skill_set(
            skill_set,
            REQUIREMENTS,
            KNOWN_IDS,
        )


def test_yaml_frontmatter_is_not_allowed_in_markdown_body():
    """Prevent duplicate frontmatter inside the instructions field."""

    skill_set = create_valid_skill_set()
    skill_set.skills[0].instructions = (
        "---\n"
        "name: annual-leave-policy\n"
        "---\n\n"
        + skill_set.skills[0].instructions
    )

    with pytest.raises(ValueError, match="must not include YAML frontmatter"):
        validate_generated_skill_set(
            skill_set,
            REQUIREMENTS,
            KNOWN_IDS,
        )
