"""Pydantic models for policy generation, validation, review, and UI output."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Simple lifecycle statuses
PolicyStatus = Literal["draft", "active", "archived"]
PolicyVersionStatus = Literal["draft", "active", "superseded"]
ValidationStatus = Literal[
    "pending",
    "pass",
    "fail",
    "needs_clarification",
]


class PolicySectionModel(BaseModel):
    """Represents a discrete, editable section of a policy."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    section_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    requirement_ids: list[str] = Field(default_factory=list)


class ValidationFinding(BaseModel):
    """An individual policy validation observation."""

    model_config = ConfigDict(extra="forbid")

    rule_name: str
    status: Literal[
        "PASS",
        "FAIL",
        "NEEDS_CLARIFICATION",
        "NOT_APPLICABLE",
    ]
    message: str
    details: list[str] = Field(default_factory=list)


class PolicyValidationReport(BaseModel):
    """Complete policy validation report."""

    model_config = ConfigDict(extra="forbid")

    overall_status: Literal[
        "PASS",
        "FAIL",
        "NEEDS_CLARIFICATION",
    ]

    coverage_score: float = Field(ge=0.0, le=1.0)

    missing_requirements: list[str] = Field(
        default_factory=list,
    )

    findings: list[ValidationFinding] = Field(
        default_factory=list,
    )

    clarification_items: list[str] = Field(
        default_factory=list,
    )



class PolicyGenerationRequest(BaseModel):
    """Generate a policy using an existing skill."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    skill_command: str = Field(min_length=1)




class PolicyModificationRequest(BaseModel):
    """Regenerate the complete policy from overall user feedback."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    feedback: str = Field(
        min_length=1,
        description=(
            "Overall feedback for the complete policy, "
            "not feedback for an individual section."
        ),
    )


class PolicyVersionSummary(BaseModel):
    """Summary of an individual policy version."""

    version_id: UUID
    policy_id: UUID
    version: int

    status: PolicyVersionStatus

    validation_status: ValidationStatus

    change_summary: str | None = None
    created_at: datetime



class PolicyResponse(BaseModel):
    """Complete  policy response """

    model_config = ConfigDict(extra="forbid")

    # Policy identity
    policy_id: UUID
    version: int

    # Policy metadata
    title: str
    description: str | None = None
    domain: str

    # Overall policy lifecycle
    policy_status: PolicyStatus

    # Individual version lifecycle
    status: PolicyVersionStatus

    # Structured policy content
    sections: list[PolicySectionModel]

    # Readable policy document
    policy_text: str

    # Skill lineage
    applied_skill_ids: list[str] = Field(
        default_factory=list,
    )

    applied_skill_version_ids: list[str] = Field(
        default_factory=list,
    )

    # Original source requirement lineage
    source_requirement_version_id: str | None = None

    # Validation results
    validation_status: ValidationStatus
    validation_report: PolicyValidationReport | None = None

    # Version information
    change_summary: str | None = None
    created_at: datetime
