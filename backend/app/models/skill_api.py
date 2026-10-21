
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ValidatedRequirementInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    requirement_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1)


class SkillGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirements: list[ValidatedRequirementInput] = Field(min_length=1)


class GeneratedSkillResponse(BaseModel):
    skill_id: UUID
    name: str
    version_id: UUID
    version: int
    status: str


class SkillGenerationResponse(BaseModel):
    skills: list[GeneratedSkillResponse]
