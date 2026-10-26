
from typing import Literal

from pydantic import BaseModel, Field


class RequirementInput(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)
    event: Literal["start", "answer", "confirm", "cancel"] = "start"


class RequirementDetails(BaseModel):
    policy_name: str | None = None
    domain: Literal["hr", "finance", "it_security", "general"] = "general"
    purpose: str | None = None
    scope: str | None = None
    stakeholders: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    unresolved_details: list[str] = Field(default_factory=list)


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
