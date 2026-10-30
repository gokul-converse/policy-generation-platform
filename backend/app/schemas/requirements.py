
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RequirementInput(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)
    event: Literal["start", "answer", "confirm", "cancel"] = "start"


class RequirementDetails(BaseModel):
    policy_name: str | None = None
    domain: str = Field(default="general", min_length=1)
    purpose: str | None = None
    scope: str | None = None
    stakeholders: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    unresolved_details: list[str] = Field(default_factory=list)

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return "general"
        return value


class GatheringResult(BaseModel):
    requirements: RequirementDetails
    evidence: list[str] = Field(default_factory=list)
    summary: str = ""


class ValidationResult(BaseModel):
    status: Literal["needs_clarification", "ready_for_confirmation"]
    missing_details: list[str] = Field(default_factory=list)
    question: str | None = None
    draft: RequirementDetails | None = None
    explanation: str = ""
