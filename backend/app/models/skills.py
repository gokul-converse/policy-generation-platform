"""
Pydantic models for skill generation and semantic validation.

These models define the structured input/output contracts used by:
    1. Skill Generation Agent
    2. Skill Validation Agent

The models also enforce basic structural rules before generated
content is accepted by the application.
"""

import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class GeneratedSkill(BaseModel):
    """
    Represents one reusable skill generated from a validated requirement.

    A skill contains:
        - name: Unique kebab-case identifier.
        - description: Short explanation of the capability.
        - instructions: Reusable instructions for downstream agents.
        - requirement_ids: Source requirement IDs associated with the skill.

    The application currently enforces one requirement ID per skill.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=1,
        max_length=64,
        description="Unique skill name in lowercase kebab-case.",
    )

    description: str = Field(
        min_length=1,
        max_length=1024,
        description="Short description of the skill's business capability.",
    )

    instructions: str = Field(
        min_length=1,
        max_length=30000,
        description="Reusable and actionable skill instructions.",
    )

    requirement_ids: list[str] = Field(
        min_length=1,
        description="Validated requirement IDs associated with this skill.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """
        Ensure the skill name follows lowercase kebab-case.

        Valid examples:
            employee-leave-management
            remote-work-eligibility

        Invalid examples:
            EmployeeLeave
            employee_leave
            employee--leave
        """

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError(
                "Skill name must use lowercase letters, numbers, "
                "and single hyphens."
            )

        return value

    @field_validator("description", "instructions")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        """Reject empty or whitespace-only text fields."""

        if not value.strip():
            raise ValueError("This field cannot be blank.")

        return value

    @field_validator("requirement_ids")
    @classmethod
    def validate_requirement_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        """
        Normalize requirement IDs and reject duplicates.

        This validates the IDs within one skill.
        Cross-skill mapping is checked by the skill generation service.
        """

        cleaned_values = [value.strip() for value in values]

        if any(not value for value in cleaned_values):
            raise ValueError("Requirement IDs cannot be blank.")

        if len(cleaned_values) != len(set(cleaned_values)):
            raise ValueError(
                "Duplicate requirement IDs are not allowed."
            )

        return cleaned_values


class GeneratedSkillSet(BaseModel):
    """
    Represents the complete collection of skills generated for a request.

    This is the structured output contract of the Skill Generation Agent.
    """

    model_config = ConfigDict(extra="forbid")

    skills: list[GeneratedSkill] = Field(
        min_length=1,
        description="Draft skills generated from validated requirements.",
    )

    @model_validator(mode="after")
    def validate_unique_skill_names(self) -> "GeneratedSkillSet":
        """Ensure that skill names are unique within the generated set."""

        names = [
            skill.name.casefold()
            for skill in self.skills
        ]

        if len(names) != len(set(names)):
            raise ValueError(
                "Skill names must be unique within a generated set."
            )

        return self


# ============================================================
# Skill Semantic Validation Models
# ============================================================


class SkillValidationFinding(BaseModel):
    """
    Represents one issue found during semantic skill validation.

    Each finding must identify:
        - The related source requirement.
        - The type of issue.
        - A description of the issue.
        - Evidence supporting the finding.
        - An optional correction suggestion.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    requirement_id: str = Field(
        min_length=1,
        description="Authoritative requirement associated with the finding.",
    )

    finding_type: Literal[
        "UNSUPPORTED",
        "ALTERED",
        "MISSING",
        "OVERLAP",
        "CONFLICT",
        "AMBIGUOUS",
    ] = Field(
        description="Classification of the semantic validation finding."
    )

    description: str = Field(
        min_length=1,
        description="Explanation of the identified issue.",
    )

    evidence: str = Field(
        min_length=1,
        description=(
            "Evidence from the original requirement or generated skill "
            "supporting the finding."
        ),
    )

    suggested_correction: str | None = Field(
        default=None,
        description=(
            "Suggested correction without introducing unsupported "
            "business rules."
        ),
    )


class SkillValidationResult(BaseModel):
    """
    Structured output returned by the Skill Validation Agent.

    Supported statuses:

        PASS:
            No semantic issues were found.

        FAIL:
            Generated skills contain unsupported, altered, missing,
            conflicting, or non-compliant content.

        NEEDS_CLARIFICATION:
            The authoritative requirements do not provide enough
            information to determine correctness.
    """

    model_config = ConfigDict(extra="forbid")

    overall_status: Literal[
        "PASS",
        "FAIL",
        "NEEDS_CLARIFICATION",
    ] = Field(
        description="Overall semantic validation result."
    )

    findings: list[SkillValidationFinding] = Field(
        default_factory=list,
        description="Semantic validation findings.",
    )

    @model_validator(mode="after")
    def validate_result_consistency(self) -> "SkillValidationResult":
        """
        Ensure that the validation status agrees with its findings.

        PASS:
            Must not contain findings.

        FAIL / NEEDS_CLARIFICATION:
            Must contain at least one finding.
        """

        if self.overall_status == "PASS" and self.findings:
            raise ValueError(
                "A PASS validation result cannot contain findings."
            )

        if (
            self.overall_status in {"FAIL", "NEEDS_CLARIFICATION"}
            and not self.findings
        ):
            raise ValueError(
                f"{self.overall_status} requires at least one finding."
            )

        return self
