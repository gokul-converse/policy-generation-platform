
"""Unit tests for the requirement-analysis model."""

import pytest
from app.models.requirements import RequirementAnalysis
from pydantic import ValidationError


def test_valid_analysis_is_accepted():
    analysis = RequirementAnalysis(
        original_text="Employees receive 20 days of annual leave.",
        requirements=["Employees receive 20 days of annual leave."],
        identified_domains=["Annual Leave"],
    )

    assert len(analysis.requirements) == 1
    assert analysis.identified_domains == ["Annual Leave"]


def test_blank_original_text_is_rejected():
    with pytest.raises(ValidationError):
        RequirementAnalysis(
            original_text=" ",
            requirements=["Employees receive annual leave."],
        )


def test_empty_requirements_are_rejected():
    with pytest.raises(ValidationError):
        RequirementAnalysis(
            original_text="Employees receive annual leave.",
            requirements=[],
        )


def test_blank_list_entries_are_removed():
    analysis = RequirementAnalysis(
        original_text="Employees receive annual leave.",
        requirements=[
            "Employees receive annual leave.",
            " ",
            "Employees receive annual leave.",
        ],
        identified_domains=["Annual Leave", " "],
    )

    assert analysis.requirements == [
        "Employees receive annual leave."
    ]
    assert analysis.identified_domains == ["Annual Leave"]


def test_original_text_is_preserved():
    original = "  Employees receive 20 days of annual leave.  "

    analysis = RequirementAnalysis(
        original_text=original,
        requirements=["Employees receive 20 days of annual leave."],
    )

    assert analysis.original_text == original


def test_unexpected_fields_are_rejected():
    with pytest.raises(ValidationError):
        RequirementAnalysis(
            original_text="Employees receive annual leave.",
            requirements=["Employees receive annual leave."],
            unexpected_field="not allowed",
        )
