
from pydantic import BaseModel, Field


class PolicySection(BaseModel):
    id: str
    title: str
    content: str


class PolicyDraft(BaseModel):
    title: str
    sections: list[PolicySection] = Field(default_factory=list)
