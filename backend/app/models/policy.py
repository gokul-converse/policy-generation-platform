
"""Structured models for generated policy drafts."""

from pydantic import BaseModel, Field, field_validator


class PolicySection(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)

    @field_validator("title", "content")
    @classmethod
    def validate_nonblank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


class PolicyDraft(BaseModel):
    title: str = Field(min_length=1)
    domains: list[str] = Field(min_length=1)
    sections: list[PolicySection] = Field(min_length=1)
    unresolved_items: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Policy title cannot be blank.")
        return value

    @field_validator("domains")
    @classmethod
    def validate_domains(cls, values: list[str]) -> list[str]:
        cleaned = [
            domain.strip()
            for domain in values
            if isinstance(domain, str) and domain.strip()
        ]

        if not cleaned:
            raise ValueError(
                "At least one non-empty policy domain is required."
            )

        # Preserve order while removing duplicates.
        return list(dict.fromkeys(cleaned))
