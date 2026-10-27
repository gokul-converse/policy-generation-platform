"""Tests for skill quality control, numeric preservation, and agent retries."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.agents.policy_generation.skill_generation import (
    generate_skills,
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


def test_numeric_preservation_failure():
    """Reject skill where source requirement number is dropped or altered."""
    skill_set = GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="annual-leave-policy",
                description="Annual leave policy",
                instructions=(
                    "# Annual Leave Policy\n\n"
                    "## Purpose\n"
                    "Define annual leave.\n\n"
                    "## Instructions\n"
                    "Employees receive thirty days of annual leave.\n\n"
                    "## Source Requirements\n"
                    "- REQ-001: Employees receive thirty days of annual leave."
                ),
                requirement_ids=["REQ-001"],
            )
        ]
    )

    with pytest.raises(ValueError, match="must preserve the original text"):
        validate_generated_skill_set(
            skill_set,
            REQUIREMENTS,
            {"REQ-001"},
        )


def test_placeholder_rejection():
    """Reject skill containing placeholder text like [TODO] or [TBD]."""
    skill_set = GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="annual-leave-policy",
                description="Annual leave policy",
                instructions=(
                    "# Annual Leave Policy\n\n"
                    "## Purpose\n"
                    "Define annual leave.\n\n"
                    "## Instructions\n"
                    "[TODO] Specify employee eligibility and 20 days entitlement.\n\n"
                    "## Source Requirements\n"
                    "- REQ-001: Employees receive 20 days of annual leave."
                ),
                requirement_ids=["REQ-001"],
            )
        ]
    )

    with pytest.raises(ValueError, match="contains placeholder"):
        validate_generated_skill_set(
            skill_set,
            REQUIREMENTS,
            {"REQ-001"},
        )


@pytest.mark.asyncio
async def test_generate_skills_retries_on_initial_failure():
    """Ensure generate_skills retries when the first attempt produces invalid output."""

    # First attempt: invalid output (missing heading)
    invalid_skill = GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="leave-skill",
                description="Leave skill",
                instructions="# Title\n\nMissing required headings.",
                requirement_ids=["REQ-001"],
            )
        ]
    )

    # Second attempt: valid output
    valid_skill = GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="leave-skill",
                description="Leave skill",
                instructions=(
                    "# Leave Skill\n\n"
                    "## Purpose\n"
                    "Define leave rules.\n\n"
                    "## Instructions\n"
                    "Grant 20 days of leave.\n\n"
                    "## Source Requirements\n"
                    "- REQ-001: Employees receive 20 days of annual leave."
                ),
                requirement_ids=["REQ-001"],
            )
        ]
    )

    mock_agent_instance = MagicMock()
    # First call returns invalid, second call returns valid
    mock_agent_instance.run = AsyncMock(
        side_effect=[
            MagicMock(value=invalid_skill.model_dump(), text=None),
            MagicMock(value=valid_skill.model_dump(), text=None),
        ]
    )

    mock_client = MagicMock()

    # Monkeypatch Agent constructor to return our mock agent instance
    import agent_framework
    original_agent = agent_framework.Agent

    def mock_agent_ctor(*args, **kwargs):
        return mock_agent_instance

    import app.agents.policy_generation.skill_generation as sg_module
    sg_module.Agent = mock_agent_ctor

    try:
        result = await generate_skills(
            REQUIREMENTS,
            client=mock_client,
            max_retries=2,
        )
        assert len(result.skills) == 1
        assert result.skills[0].name == "leave-skill"
        assert mock_agent_instance.run.call_count == 2
    finally:
        sg_module.Agent = original_agent
