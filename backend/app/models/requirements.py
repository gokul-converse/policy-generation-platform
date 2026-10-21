
"""Validated data models for policy requirement analysis."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RequirementAnalysis(BaseModel):
    """Structured analysis of the original policy requirements."""

    model_config = ConfigDict(extra="forbid")

    original_text: str = Field(
        min_length=1,
        description="The exact policy description supplied by the user.",
    )

    requirements: list[str] = Field(
        min_length=1,
        description="Explicit business requirements extracted from the input.",
    )

    identified_domains: list[str] = Field(
        default_factory=list,
        description="Policy domains discovered from the actual requirements.",
    )

    missing_information: list[str] = Field(
        default_factory=list,
        description="Important details that are not supplied by the user.",
    )

    ambiguities: list[str] = Field(
        default_factory=list,
        description="Requirements with multiple materially different interpretations.",
    )

    @field_validator(
        "original_text",
        mode="before",
    )
    @classmethod
    def validate_original_text(cls, value: str) -> str:
        """Reject missing or blank input without altering its content."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("Original policy requirements cannot be blank.")

        # Preserve the user's original text exactly.
        return value

    @field_validator(
        "requirements",
        "identified_domains",
        "missing_information",
        "ambiguities",
    )
    @classmethod
    def clean_text_lists(cls, values: list[str]) -> list[str]:
        """Remove blank entries and normalize surrounding whitespace."""

        if not isinstance(values, list):
            raise ValueError("Expected a list of strings.")

        cleaned = []

        for value in values:
            if not isinstance(value, str):
                raise ValueError("Every list entry must be a string.")

            value = value.strip()

            if value:
                cleaned.append(value)

        return list(dict.fromkeys(cleaned))

    @field_validator("requirements")
    @classmethod
    def require_at_least_one_requirement(
        cls,
        values: list[str],
    ) -> list[str]:
        """Ensure analysis contains at least one usable requirement."""

        if not values:
            raise ValueError(
                "The analyzer must return at least one requirement."
            )

        return values
