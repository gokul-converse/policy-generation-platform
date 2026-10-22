
"""Tests for generated skill schemas."""

import pytest
from app.models.skills import GeneratedSkill, GeneratedSkillSet
from pydantic import ValidationError


def test_valid_skill():
    skill = GeneratedSkill(
        name="leave-policy",
        description="Guidance for generating leave policies.",
        instructions="Use only the supplied leave requirements.",
        requirement_ids=["REQ-001"],
    )

    assert skill.name == "leave-policy"
    assert skill.requirement_ids == ["REQ-001"]


def test_invalid_skill_name():
    with pytest.raises(ValidationError):
        GeneratedSkill(
            name="Leave Policy",
            description="Leave policy guidance.",
            instructions="Use supplied requirements.",
            requirement_ids=["REQ-001"],
        )


def test_blank_requirement_id():
    with pytest.raises(ValidationError):
        GeneratedSkill(
            name="leave-policy",
            description="Leave policy guidance.",
            instructions="Use supplied requirements.",
            requirement_ids=[" "],
        )


def test_empty_skill_set():
    with pytest.raises(ValidationError):
        GeneratedSkillSet(skills=[])
