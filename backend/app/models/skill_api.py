"""API and data contract schemas for skill generation, management, and slash-command flow."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ValidatedRequirementInput(BaseModel):
    """Simplified requirement item containing requirement_id, text, and session_id."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    requirement_id: str = Field(
        min_length=1,
        max_length=100,
        description="Requirement identifier from conversational gathering (e.g., REQ-001).",
    )
    text: str = Field(
        min_length=1,
        description="Requirement text.",
    )
    session_id: str | None = Field(
        default=None,
        description="Associated session ID from teammate's requirement gathering table.",
    )
    category: str | None = Field(
        default=None,
        description="Optional category or domain tag.",
    )
    numeric_values: list[str] = Field(
        default_factory=list,
        description="Numeric values and units automatically extracted or preserved.",
    )
    status: str = Field(
        default="validated",
        description="Status flag.",
    )


class SkillGenerationRequest(BaseModel):
    """Request model for skill generation."""

    model_config = ConfigDict(extra="ignore")

    session_id: str | None = Field(
        default=None,
        description="Session ID from conversational requirement gathering to auto-load requirement_id and text from teammate's table.",
    )
    requirements: list[ValidatedRequirementInput] | None = Field(
        default=None,
        description="Optional list of requirements with requirement_id and text (not required if session_id is provided).",
    )
    source_requirement_version_id: str | None = Field(
        default=None,
        description="Optional identifier of the validated requirement snapshot.",
    )


class GeneratedSkillResponse(BaseModel):
    """Summary of a generated and persisted skill."""

    skill_id: UUID
    name: str
    description: str | None = None
    version_id: UUID
    version: int
    status: str
    source_requirement_version_id: str | None = None


class SkillGenerationResponse(BaseModel):
    """API response model for skill generation."""

    skills: list[GeneratedSkillResponse]


class SkillVersionDetail(BaseModel):
    """Full detail of a specific skill version."""

    version_id: UUID
    skill_id: UUID
    version: int
    file_path: str
    status: str
    created_at: datetime
    source_requirement_version_id: str | None = None
    content: str | None = None


class SkillDetailResponse(BaseModel):
    """Complete detail of a skill including all versions."""

    skill_id: UUID
    name: str
    description: str | None = None
    created_at: datetime
    versions: list[SkillVersionDetail]


class SlashCommandItem(BaseModel):
    """Item for the Claude-like forward-slash (/) autocomplete menu."""

    model_config = ConfigDict(extra="ignore")

    command: str = Field(description="The slash command trigger, e.g. /company-policy-generator")
    name: str = Field(description="Unique skill name")
    description: str = Field(description="Concise description of the skill")
    skill_id: UUID | None = Field(default=None, description="Database ID if registered")
    source: str = Field(default="builtin", description="builtin or generated")
