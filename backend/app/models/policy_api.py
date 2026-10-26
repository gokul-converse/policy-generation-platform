"""Pydantic data models for policy generation, validation, review, and UI output."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from app.models.skill_api import ValidatedRequirementInput
from pydantic import BaseModel, ConfigDict, Field


class PolicySectionModel(BaseModel):
    """Represents a discrete, editable section of a policy document."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    section_id: str = Field(
        min_length=1,
        description="Stable section identifier (e.g. SEC-001 or purpose).",
    )
    title: str = Field(
        min_length=1,
        description="Human-readable section title.",
    )
    content: str = Field(
        min_length=1,
        description="Substantive policy content.",
    )
    requirement_ids: list[str] = Field(
        default_factory=list,
        description="Source requirement IDs mapped to this section.",
    )


class ValidationFinding(BaseModel):
    """An individual validation observation or quality finding."""

    model_config = ConfigDict(extra="forbid")

    rule_name: str = Field(
        description="Name of the validation check performed."
    )
    status: Literal[
        "PASS",
        "FAIL",
        "NEEDS_CLARIFICATION",
        "NOT_APPLICABLE",
    ] = Field(description="Outcome of this validation check.")
    message: str = Field(
        description="Concise description of the finding."
    )
    details: list[str] = Field(
        default_factory=list,
        description="Detailed items, diffs, or diagnostic messages.",
    )


class PolicyValidationReport(BaseModel):
    """Comprehensive validation report for a policy draft."""

    model_config = ConfigDict(extra="forbid")

    overall_status: Literal[
        "PASS",
        "FAIL",
        "NEEDS_CLARIFICATION",
    ] = Field(description="Aggregate validation determination.")
    coverage_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Proportion of source requirements fully addressed (0.0 to 1.0)."
        ),
    )
    missing_requirements: list[str] = Field(
        default_factory=list,
        description="Requirement IDs not addressed in the policy draft.",
    )
    findings: list[ValidationFinding] = Field(
        default_factory=list,
        description="Collection of specific rule evaluation findings.",
    )
    clarification_items: list[str] = Field(
        default_factory=list,
        description=(
            "Ambiguities or unresolved questions requiring human guidance."
        ),
    )



class PolicyGenerationRequest(BaseModel):
    """Request to generate a policy from one confirmed requirement."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(
        min_length=1,
        description="ID of the confirmed requirement-gathering session.",
    )
    requirement_id: str = Field(
        min_length=1,
        description="ID of the specific confirmed requirement to generate the policy from.",
    )

    selected_skill_ids: list[UUID] = Field(
        default_factory=list,
        description="IDs of saved skills to apply, if explicitly selected.",
    )
    skill_command: str | None = Field(
        default=None,
        description="Optional slash command identifying a skill to apply or modify.",
    )

    title: str | None = Field(
        default=None,
        description="Optional policy title; generated when omitted.",
    )
    description: str | None = Field(
        default=None,
        description="Optional policy description.",
    )
    domain: str | None = Field(
        default=None,
        description="Optional policy domain, such as HR or Finance.",
    )
    source_requirement_version_id: str | None = Field(
        default=None,
        description="Optional source requirement version identifier.",
    )



class PolicyModificationRequest(BaseModel):
    """Request to edit or revise a policy section or policy content."""

    model_config = ConfigDict(extra="forbid")

    section_id: str | None = Field(
        default=None,
        description=(
            "Section to revise. When omitted, the service must explicitly "
            "handle a whole-policy modification."
        ),
    )
    instructions: str = Field(
        min_length=1,
        description="User instructions detailing requested changes.",
    )
    updated_content: str | None = Field(
        default=None,
        description="Direct text replacement for a selected section, if provided.",
    )


class PolicyVersionSummary(BaseModel):
    """Summary of a version record for a policy."""

    version_id: UUID
    policy_id: UUID
    version: int
    status: str
    validation_status: str
    change_summary: str | None = None
    created_at: datetime


class PolicyResponse(BaseModel):
    """Structured policy representation for the UI and client consumers."""

    model_config = ConfigDict(extra="forbid")

    policy_id: UUID
    version: int
    title: str
    description: str | None = None
    domain: str
    status: str
    sections: list[PolicySectionModel]
    applied_skill_ids: list[str] = Field(default_factory=list)
    source_requirement_version_id: str | None = None
    validation_status: str
    validation_report: PolicyValidationReport | None = None
    change_summary: str | None = None
    policy_text_path: str | None = Field(
        default=None,
        description="Relative path to the generated data/policy.txt document.",
    )
    created_at: datetime
