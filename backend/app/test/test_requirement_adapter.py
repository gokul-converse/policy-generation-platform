"""Unit tests for the requirement adapter module."""

import pytest
from app.models.requirements import RequirementAnalysis
from app.models.skill_api import ValidatedRequirementInput
from app.services.requirement_adapter import adapt_requirements, extract_numbers_and_units


def test_extract_numbers_and_units():
    text = "Employees receive 20 days of leave, $500 allowance, and 15% discount after 6 months."
    nums = extract_numbers_and_units(text)
    assert "20 days" in nums
    assert "$500" in nums
    assert "15%" in nums
    assert "6 months" in nums


def test_adapt_from_dict_list():
    raw = {
        "requirements": [
            {
                "requirement_id": "REQ-001",
                "text": "Employees get 20 days of leave per year.",
                "category": "leave",
            },
            {
                "requirement_id": "REQ-002",
                "text": "Requests require 5 days notice.",
            },
        ]
    }
    adapted = adapt_requirements(raw)
    assert len(adapted) == 2
    assert adapted[0].requirement_id == "REQ-001"
    assert adapted[0].text == "Employees get 20 days of leave per year."
    assert "20 days" in adapted[0].numeric_values
    assert adapted[0].category == "leave"
    assert adapted[1].requirement_id == "REQ-002"
    assert "5 days" in adapted[1].numeric_values


def test_adapt_from_requirement_analysis():
    analysis = RequirementAnalysis(
        original_text="Employees receive 25 days of vacation. Requests require 2 weeks notice.",
        requirements=[
            "Employees receive 25 days of vacation.",
            "Requests require 2 weeks notice.",
        ],
        identified_domains=["HR"],
        missing_information=[],
        ambiguities=[],
    )
    adapted = adapt_requirements(analysis)
    assert len(adapted) == 2
    assert adapted[0].requirement_id == "REQ-001"
    assert adapted[0].text == "Employees receive 25 days of vacation."
    assert "25 days" in adapted[0].numeric_values
    assert adapted[0].category == "HR"
    assert adapted[1].requirement_id == "REQ-002"
    assert "2 weeks" in adapted[1].numeric_values


def test_reject_duplicate_ids():
    raw = {
        "requirements": [
            {"requirement_id": "REQ-001", "text": "Requirement A"},
            {"requirement_id": "REQ-001", "text": "Requirement B"},
        ]
    }
    with pytest.raises(ValueError, match="Duplicate requirement ID"):
        adapt_requirements(raw)


def test_reject_unapproved_status():
    raw = {
        "requirements": [
            {
                "requirement_id": "REQ-001",
                "text": "Requirement A",
                "status": "rejected",
            }
        ]
    }
    with pytest.raises(ValueError, match="unapproved status"):
        adapt_requirements(raw)


def test_reject_empty_requirements():
    with pytest.raises(ValueError, match="non-empty"):
        adapt_requirements({"requirements": []})
