
"""Unit tests for the skill-generation agent."""

import pytest

from app.agents.policy_generation.skill_generation import (
    validate_requirement_input,
)


def test_valid_requirements():
    data = {
        "requirements": [
            {
                "requirement_id": "REQ-001",
                "text": "Employees receive 20 days of annual leave.",
            }
        ]
    }

    assert validate_requirement_input(data) == {"REQ-001"}


def test_empty_requirements():
    with pytest.raises(ValueError, match="non-empty"):
        validate_requirement_input({"requirements": []})


def test_missing_requirement_id():
    data = {
        "requirements": [
            {"text": "Employees receive annual leave."}
        ]
    }

    with pytest.raises(ValueError, match="requirement_id"):
        validate_requirement_input(data)


def test_duplicate_requirement_ids():
    data = {
        "requirements": [
            {"requirement_id": "REQ-001", "text": "Rule one."},
            {"requirement_id": "REQ-001", "text": "Rule two."},
        ]
    }

    with pytest.raises(ValueError, match="Duplicate"):
        validate_requirement_input(data)
