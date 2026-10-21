
"""Pydantic schemas for skill generation."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeneratedSkill(BaseModel):
    """Represents one skill generated from validated requirements."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

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
        description="Reusable instructions for generating policies.",
    )

    requirement_ids: list[str] = Field(
        min_length=1,
        description="IDs of validated requirements covered by this skill.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Enforce the Agent Skills naming convention."""

        import re

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
        cls, values: list[str]
    ) -> list[str]:
        """Reject blank or duplicate requirement IDs."""

        cleaned = [value.strip() for value in values]

        if any(not value for value in cleaned):
            raise ValueError("Requirement IDs cannot be blank.")

        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate requirement IDs are not allowed.")

        return cleaned


class GeneratedSkillSet(BaseModel):
    """Collection of skills generated for one requirement request."""

    model_config = ConfigDict(extra="forbid")

    skills: list[GeneratedSkill] = Field(
        min_length=1,
        description="Draft skills generated from validated requirements.",
    )
