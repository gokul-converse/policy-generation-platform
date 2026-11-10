"""Pydantic schemas for skill generation and semantic validation."""

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
    """Represents one skill generated from validated requirements."""

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
        description="Short description of what the skill does.",
    )

    instructions: str = Field(
        min_length=1,
        max_length=30000,
        description="Reusable, actionable instructions for downstream agents.",
    )

    requirement_ids: list[str] = Field(
        min_length=1,
        description="IDs of validated requirements covered by this skill.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Enforce lowercase kebab-case naming."""

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError(
                "Skill name must use lowercase letters, numbers, "
                "and single hyphens."
            )

        return value

    @field_validator("description", "instructions")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        """Reject empty or whitespace-only text."""

        if not value.strip():
            raise ValueError("This field cannot be blank.")

        return value

    @field_validator("requirement_ids")
    @classmethod
    def validate_requirement_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        """Reject blank or duplicate requirement IDs."""

        cleaned = [value.strip() for value in values]

        if any(not value for value in cleaned):
            raise ValueError("Requirement IDs cannot be blank.")

        if len(cleaned) != len(set(cleaned)):
            raise ValueError(
                "Duplicate requirement IDs are not allowed."
            )

        return cleaned


class GeneratedSkillSet(BaseModel):
    """Collection of skills generated for one requirement request."""

    model_config = ConfigDict(extra="forbid")

    skills: list[GeneratedSkill] = Field(
        min_length=1,
        description="Draft skills generated from validated requirements.",
    )

    @model_validator(mode="after")
    def validate_unique_skill_names(self) -> "GeneratedSkillSet":
        """Prevent duplicate skill names within one generated set."""

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
    """Represents one semantic issue identified in a generated skill."""

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
    """Structured result returned by the Skill Validation Agent."""

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
        """Ensure PASS cannot contain unresolved validation findings."""

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
