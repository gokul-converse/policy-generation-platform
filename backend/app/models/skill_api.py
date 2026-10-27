"""API and data contract schemas for skill generation and management."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

APPROVED_REQUIREMENT_STATUSES = {"validated", "confirmed"}


class ValidatedRequirementInput(BaseModel):
    """Normalized requirement item used by the generation pipeline."""

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    requirement_id: str = Field(
        min_length=1,
        max_length=100,
        description="Requirement identifier from requirement gathering.",
    )

    text: str = Field(
        min_length=1,
        description="Original requirement text.",
    )

    session_id: str | None = Field(
        default=None,
        description="Associated requirement-gathering session ID.",
    )

    category: str | None = Field(
        default=None,
        description="Optional category or domain tag.",
    )

    numeric_values: list[str] = Field(
        default_factory=list,
        description="Numeric values and units extracted from the requirement.",
    )

    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions or constraints associated with the requirement.",
    )

    source_document: str | None = None
    source_version_id: str | None = None

    status: str = Field(
        default="validated",
        description="Requirement approval status.",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional source requirement metadata.",
    )

    @field_validator("requirement_id", "text")
    @classmethod
    def validate_non_blank_values(cls, value: str) -> str:
        """Reject empty or whitespace-only values."""
        if not value.strip():
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("session_id", "category", "source_document", "source_version_id")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        """Strip optional string values and convert blanks to None."""
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        """Normalize the status spelling."""
        normalized = value.strip().casefold()
        if not normalized:
            raise ValueError("Requirement status cannot be blank.")
        return normalized






class SkillGenerationRequest(BaseModel):
    """Generate skills from one requirement within a specific session."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    session_id: str = Field(
        ...,
        min_length=1,
        description="ID of the confirmed requirement session.",
        examples=["SES-001"],
    )

    requirement_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID of the specific requirement within that session.",
        examples=["REQ-001"],
    )

    source_requirement_version_id: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Optional ID of the source requirement-version snapshot "
            "used for traceability."
        ),
    )

    @field_validator(
        "session_id",
        "requirement_id",
        "source_requirement_version_id",
    )
    @classmethod
    def validate_identifiers(
        cls,
        value: str | None,
    ) -> str | None:
        """Reject blank identifiers and normalize whitespace."""

        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Identifier cannot be blank.")

        return value





class GeneratedSkillResponse(BaseModel):
    """Summary of a generated and persisted skill."""

    skill_id: UUID
    name: str
    description: str | None = None
    version_id: UUID
    version: int = Field(ge=1)
    status: str
    source_requirement_version_id: str | None = None




class SkillGenerationResponse(BaseModel):
    """API response model for skill generation."""

    skills: list[GeneratedSkillResponse]


class SkillVersionDetail(BaseModel):
    """Full detail of a specific skill version."""

    version_id: UUID
    skill_id: UUID
    version: int = Field(ge=1)
    file_path: str
    status: str
    created_at: datetime
    source_requirement_version_id: str | None = None
    content: str | None = None


class SkillDetailResponse(BaseModel):
    """Complete detail of a skill, including all versions."""

    skill_id: UUID
    name: str
    description: str | None = None
    created_at: datetime
    versions: list[SkillVersionDetail]


class SlashCommandItem(BaseModel):
    """Item displayed in the slash-command autocomplete menu."""

    model_config = ConfigDict(extra="ignore")

    command: str = Field(
        description="Slash-command trigger, e.g. /company-policy-generator."
    )

    name: str = Field(description="Skill name.")

    description: str = Field(
        description="Concise description of the skill."
    )

    skill_id: UUID | None = Field(
        default=None,
        description="Database ID for generated skills.",
    )

    source: Literal["builtin", "generated"] = Field(
        default="builtin",
        description="Whether the skill is built-in or generated.",
    )
