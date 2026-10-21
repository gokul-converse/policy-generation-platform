
"""Validated models for dynamically generated domain instructions."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DomainInstruction(BaseModel):
    """Instructions generated for one policy domain."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(
        min_length=1,
        description="A meaningful domain identified from the supplied requirements.",
    )

    instructions: str = Field(
        min_length=1,
        description="Domain-specific drafting guidance grounded in the requirements.",
    )

    unresolved_questions: list[str] = Field(
        default_factory=list,
        description="Questions that cannot be answered from the supplied requirements.",
    )

    @field_validator("domain", "instructions")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """Reject blank domain names and instructions."""

        value = value.strip()

        if not value:
            raise ValueError("Domain and instructions cannot be blank.")

        return value

    @field_validator("unresolved_questions")
    @classmethod
    def clean_questions(cls, values: list[str]) -> list[str]:
        """Remove empty and duplicate questions."""

        cleaned = []

        for value in values:
            if not isinstance(value, str):
                raise ValueError("Every unresolved question must be a string.")

            value = value.strip()

            if value:
                cleaned.append(value)

        return list(dict.fromkeys(cleaned))


class DomainInstructionSet(BaseModel):
    """Validated instructions for the discovered policy domains."""

    model_config = ConfigDict(extra="forbid")

    domains: list[DomainInstruction] = Field(
        min_length=1,
        description="Instructions for each relevant discovered domain.",
    )

    @field_validator("domains")
    @classmethod
    def validate_domains(
        cls,
        values: list[DomainInstruction],
    ) -> list[DomainInstruction]:
        """Reject duplicate domain names."""

        names = [item.domain.casefold() for item in values]

        if len(names) != len(set(names)):
            raise ValueError("Duplicate domain names are not allowed.")

        return values
