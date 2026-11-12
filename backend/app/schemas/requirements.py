
"""Pydantic contracts shared by requirement extraction and validation."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RequirementInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: str | None = None
    message: str = Field(min_length=1)
    event: Literal["start", "answer", "confirm", "cancel"] = "start"


class RequirementDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Requested artifact or requirement name.
    policy_name: str | None = None
    domain: str = "general"
    purpose: str | None = None
    scope: str | None = None

    # Keep these simple and compatible with existing consumers.
    stakeholders: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)

    # Supporting references and unresolved business decisions.
    reference_data: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_details: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_structured_lists(cls, value):
        """Convert structured LLM output into the expected string lists."""

        if not isinstance(value, dict):
            return value

        value = value.copy()

        # Convert stakeholder objects into readable strings.
        stakeholders = value.get("stakeholders", [])

        if isinstance(stakeholders, list):
            normalized = []

            for item in stakeholders:
                if isinstance(item, str):
                    normalized.append(item)

                elif isinstance(item, dict):
                    name = item.get("name")
                    role = item.get("role")

                    if name and role:
                        normalized.append(f"{name}: {role}")
                    elif name:
                        normalized.append(str(name))
                    elif role:
                        normalized.append(str(role))

            value["stakeholders"] = normalized

        # Convert rule objects into readable strings.
        rules = value.get("rules", [])

        if isinstance(rules, list):
            normalized = []

            for item in rules:
                if isinstance(item, str):
                    normalized.append(item)

                elif isinstance(item, dict):
                    topic = item.get("topic")
                    decision = item.get("decision")
                    notes = item.get("notes")

                    if topic and decision:
                        rule = f"{topic}: {decision}"
                    elif decision:
                        rule = str(decision)
                    elif topic:
                        rule = str(topic)
                    else:
                        continue

                    if notes and str(notes).strip():
                        rule += f" ({str(notes).strip()})"

                    normalized.append(rule)

            value["rules"] = normalized

        return value

    @model_validator(mode="after")
    def normalize_values(self):
        """Clean text fields and remove duplicate list entries."""

        for field_name in ("policy_name", "domain", "purpose", "scope"):
            value = getattr(self, field_name)

            if isinstance(value, str):
                value = value.strip()

                if field_name == "domain":
                    setattr(self, field_name, value or "general")
                else:
                    setattr(self, field_name, value or None)

        for field_name in ("stakeholders", "rules", "unresolved_details"):
            values = getattr(self, field_name)
            cleaned = []
            seen = set()

            for item in values:
                if not isinstance(item, str):
                    continue

                item = item.strip()
                key = " ".join(item.casefold().split())

                if item and key not in seen:
                    cleaned.append(item)
                    seen.add(key)

            setattr(self, field_name, cleaned)

        return self


class GatheringResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requirements: RequirementDetails
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    reference_data: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Literal["needs_clarification", "ready_for_confirmation"]
    missing_details: list[str] = Field(default_factory=list)
    question: str | None = None
    draft: RequirementDetails | None = None
    explanation: str = ""

    @model_validator(mode="after")
    def validate_result_shape(self):
        if self.status == "needs_clarification":
            if not self.question or not self.question.strip():
                raise ValueError(
                    "Clarification status requires a question."
                )

            if self.draft is not None:
                raise ValueError(
                    "Clarification status requires draft=null."
                )

            if not self.missing_details:
                raise ValueError(
                    "Clarification status requires missing_details."
                )

        else:
            if self.question is not None:
                raise ValueError(
                    "Draft status requires question=null."
                )

            if self.draft is None:
                raise ValueError(
                    "Draft status requires a complete draft."
                )

        return self
