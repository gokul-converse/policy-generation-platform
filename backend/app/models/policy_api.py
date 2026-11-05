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
    """Generate a policy from confirmed requirements."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    session_id: str = Field(min_length=1)
    requirement_id: str = Field(min_length=1)

    source_requirement_version_id: str | None = None

    skill_command: str | None = None


class PolicyModificationRequest(BaseModel):
    """Modify an existing policy section."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    section_id: str = Field(min_length=1)
    instructions: str = Field(min_length=1)


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
    """Complete database-backed policy response for the frontend."""

    model_config = ConfigDict(extra="forbid")

    policy_id: UUID
    version: int

    title: str
    description: str | None = None
    domain: str

    # Overall policy lifecycle.
    policy_status: PolicyStatus

    # Individual version lifecycle.
    status: PolicyVersionStatus

    # Structured content for editable frontend sections.
    sections: list[PolicySectionModel]

    # Complete readable policy document from the database.
    policy_text: str

    # Skill references used for this version.
    applied_skill_ids: list[str] = Field(default_factory=list)

    source_requirement_version_id: str | None = None

    validation_status: ValidationStatus
    validation_report: PolicyValidationReport | None = None

    change_summary: str | None = None
    created_at: datetime
