"""Tests for deterministic policy validation layer."""

from app.models.policy_api import PolicySectionModel
from app.models.skill_api import ValidatedRequirementInput
from app.services.validation_service import validate_policy_draft


def test_validation_passes_valid_policy():
    """Policy with all requirements addressed and numbers preserved should PASS."""

    requirements = [
        ValidatedRequirementInput(
            requirement_id="REQ-001",
            text="Employees receive 20 days of annual leave per year.",
            numeric_values=["20 days"],
        ),
        ValidatedRequirementInput(
            requirement_id="REQ-002",
            text="Leave requests must be submitted at least 5 days in advance.",
            numeric_values=["5 days"],
        ),
    ]

    sections = [
        PolicySectionModel(
            section_id="purpose",
            title="Purpose and Scope",
            content="This policy establishes guidelines for annual leave.",
            requirement_ids=[],
        ),
        PolicySectionModel(
            section_id="entitlement",
            title="Annual Leave Entitlement",
            content="Employees receive 20 days of annual leave per year.",
            requirement_ids=["REQ-001"],
        ),
        PolicySectionModel(
            section_id="requests",
            title="Request Procedures",
            content="Leave requests must be submitted at least 5 days in advance.",
            requirement_ids=["REQ-002"],
        ),
    ]

    report = validate_policy_draft(sections, requirements)
    assert report.overall_status == "PASS"
    assert report.coverage_score == 1.0
    assert len(report.missing_requirements) == 0


def test_validation_fails_unknown_source_id():
    """Referencing an unauthorized/hallucinated requirement ID must trigger FAIL."""

    requirements = [
        ValidatedRequirementInput(
            requirement_id="REQ-001",
            text="Core rule text.",
        )
    ]

    sections = [
        PolicySectionModel(
            section_id="rules",
            title="Rules",
            content="Core rule applies to all staff.",
            requirement_ids=["REQ-001", "REQ-999-HALLUCINATED"],
        )
    ]

    report = validate_policy_draft(sections, requirements)
    assert report.overall_status == "FAIL"
    source_id_finding = next(f for f in report.findings if f.rule_name == "source_id_validity")
    assert source_id_finding.status == "FAIL"
    assert any("REQ-999-HALLUCINATED" in d for d in source_id_finding.details)


def test_validation_fails_altered_numbers():
    """Altered or missing numbers must trigger FAIL."""

    requirements = [
        ValidatedRequirementInput(
            requirement_id="REQ-001",
            text="Expense threshold is $500 maximum.",
            numeric_values=["$500"],
        )
    ]

    sections = [
        PolicySectionModel(
            section_id="expenses",
            title="Expense Limit",
            content="Expense threshold is one thousand dollars maximum.",
            requirement_ids=["REQ-001"],
        )
    ]

    report = validate_policy_draft(sections, requirements)
    assert report.overall_status == "FAIL"
    num_finding = next(f for f in report.findings if f.rule_name == "numeric_preservation")
    assert num_finding.status == "FAIL"


def test_validation_fails_placeholders():
    """Detection of [TODO] or [TBD] must trigger FAIL."""

    requirements = [
        ValidatedRequirementInput(
            requirement_id="REQ-001",
            text="Policy requirement text.",
        )
    ]

    sections = [
        PolicySectionModel(
            section_id="sec-1",
            title="Section One",
            content="Policy requirement text. [TODO: Specify manager approval details]",
            requirement_ids=["REQ-001"],
        )
    ]

    report = validate_policy_draft(sections, requirements)
    assert report.overall_status == "FAIL"
    ph_finding = next(f for f in report.findings if f.rule_name == "placeholder_detection")
    assert ph_finding.status == "FAIL"


def test_validation_needs_clarification_on_unresolved_items():
    """Unresolved questions must produce NEEDS_CLARIFICATION status."""

    requirements = [
        ValidatedRequirementInput(
            requirement_id="REQ-001",
            text="General leave rule.",
        )
    ]

    sections = [
        PolicySectionModel(
            section_id="sec-1",
            title="Leave Rule",
            content="General leave rule is implemented.",
            requirement_ids=["REQ-001"],
        )
    ]

    unresolved = ["Is probationary leave entitlement prorated?"]

    report = validate_policy_draft(sections, requirements, unresolved_items=unresolved)
    assert report.overall_status == "NEEDS_CLARIFICATION"
    assert report.clarification_items == unresolved
