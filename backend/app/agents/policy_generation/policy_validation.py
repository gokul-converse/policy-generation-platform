"""Semantic validation agent for generated and modified enterprise policies."""

import json
from typing import Any, Literal

from agent_framework import Agent
from app.clients.foundry_client import get_foundry_client
from app.models.policy_api import (
    PolicySectionModel,
    ValidationFinding,
)
from app.models.skill_api import ValidatedRequirementInput
from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Structured output
# ============================================================================

class PolicySemanticValidationOutput(BaseModel):
    """Structured semantic validation result."""

    model_config = ConfigDict(extra="forbid")

    overall_status: Literal[
        "PASS",
        "FAIL",
        "NEEDS_CLARIFICATION",
    ] = Field(
        description="Overall semantic validation result."
    )

    findings: list[ValidationFinding] = Field(
        default_factory=list,
        description="Semantic validation findings."
    )

    missing_requirements: list[str] = Field(
        default_factory=list,
        description="Requirement IDs whose meaning is not adequately addressed."
    )

    clarification_items: list[str] = Field(
        default_factory=list,
        description="Unresolved semantic questions requiring human decisions."
    )


# ============================================================================
# Agent instructions
# ============================================================================

POLICY_VALIDATION_INSTRUCTIONS = """
You are an independent Enterprise Policy Semantic Validation Agent.

Your responsibility is to validate policy content against authoritative,
validated requirements. You must not generate, rewrite, or modify policy text.

The supplied validated requirements are the authoritative source of truth.

## 1. Requirement compliance

For every requirement:

- Check whether the actual policy meaning satisfies the requirement.
- Do not trust requirement_ids alone as proof of compliance.
- Identify requirements that are missing, partially addressed, or contradicted.
- Verify that conditions, scope, eligibility, exceptions, responsibilities,
  restrictions, and obligations are preserved.
- Check numeric values, dates, units, periods, percentages, and thresholds.

## 2. Unsupported additions

Identify policy rules that are not supported by the supplied requirements.

Examples include:

- Invented approval authorities.
- Additional eligibility conditions.
- New penalties or disciplinary actions.
- Invented deadlines or notice periods.
- New financial limits or entitlements.
- Unsupported exceptions or restrictions.
- Additional legal or compliance obligations.

Do not classify ordinary explanatory wording as an unsupported rule unless
it changes or introduces a business obligation.

## 3. Semantic conflicts

Identify contradictions between:

- Different policy sections.
- Policy content and authoritative requirements.
- Eligibility conditions and exceptions.
- Responsibilities and approval authorities.
- Numeric values or time periods.

## 4. Modification validation

When modification context is supplied, compare:

- Original section.
- User modification instruction.
- Revised section.
- Authoritative requirements.
- Remaining policy sections.

Verify that:

- The requested change was actually applied.
- The revised meaning matches the user's instruction.
- The change does not conflict with authoritative requirements.
- Unrelated content has not been unnecessarily changed.
- Existing conditions, exceptions, and requirement mappings remain valid.
- No unsupported rule has been introduced.

Do not assume a requested change is valid merely because the user requested it.
If it conflicts with authoritative requirements, report FAIL.

## 5. Status determination

PASS:
All relevant requirements are semantically satisfied and no material
unsupported additions or contradictions are identified.

FAIL:
There is a material contradiction, unsupported policy rule, missing
mandatory requirement, incorrect value, or non-compliant modification.

NEEDS_CLARIFICATION:
The available requirements do not contain enough information to determine
a policy decision safely. Do not invent the missing decision.

## 6. Output rules

- Return only the requested structured output.
- Every finding must explain the issue clearly.
- Include evidence from the policy or requirement in finding details.
- Use rule_name values that identify the check, such as:
  requirement_semantic_compliance,
  unsupported_policy_addition,
  semantic_conflict,
  modification_instruction_compliance,
  requirement_condition_preservation.
- Use PASS findings when a relevant check succeeds.
- Use NEEDS_CLARIFICATION for unresolved decisions.
- Do not rewrite or suggest replacement policy text.
- Do not invent requirement IDs.
- Be conservative: distinguish a genuine violation from missing information.

Return output matching PolicySemanticValidationOutput.
"""


# ============================================================================
# Input normalization
# ============================================================================

def _normalize_items(items: list[Any] | None) -> list[dict[str, Any]]:
    """Convert Pydantic models and dictionaries into JSON-safe dictionaries."""

    normalized: list[dict[str, Any]] = []

    for item in items or []:
        if isinstance(item, dict):
            normalized.append(item)

        elif hasattr(item, "model_dump"):
            normalized.append(item.model_dump(mode="json"))

        else:
            normalized.append({"value": str(item)})

    return normalized


def _normalize_sections(
    sections: list[PolicySectionModel] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize policy sections for the validation prompt."""

    return _normalize_items(sections)


# ============================================================================
# Result parsing
# ============================================================================

def _parse_agent_result(result: Any) -> PolicySemanticValidationOutput:
    """Parse the structured response returned by Microsoft Agent Framework."""

    value = getattr(result, "value", None)

    if value is not None:
        return PolicySemanticValidationOutput.model_validate(value)

    result_text = getattr(result, "text", None)

    if not result_text:
        raise ValueError(
            "Policy validation agent returned no structured output."
        )

    return PolicySemanticValidationOutput.model_validate_json(result_text)


# ============================================================================
# Semantic validation
# ============================================================================

async def validate_policy_semantics(
    sections: list[PolicySectionModel] | list[dict[str, Any]],
    requirements: list[
        ValidatedRequirementInput | dict[str, Any]
    ],
    *,
    operation: Literal["generation", "modification"] = "generation",
    original_section: PolicySectionModel | dict[str, Any] | None = None,
    revised_section: PolicySectionModel | dict[str, Any] | None = None,
    modification_instruction: str | None = None,
    client: Any = None,
) -> PolicySemanticValidationOutput:
    """
    Validate policy semantics against authoritative requirements.

    This function only evaluates policy content. It never modifies policy data.
    """

    if not requirements:
        raise ValueError(
            "Authoritative validated requirements are required "
            "for semantic policy validation."
        )

    if not sections:
        raise ValueError(
            "At least one policy section is required for validation."
        )

    llm_client = client or get_foundry_client()

    prompt_data = {
        "operation": operation,
        "authoritative_requirements": _normalize_items(requirements),
        "policy_sections": _normalize_sections(sections),
        "modification_context": {
            "original_section": (
                original_section.model_dump(mode="json")
                if hasattr(original_section, "model_dump")
                else original_section
            ),
            "revised_section": (
                revised_section.model_dump(mode="json")
                if hasattr(revised_section, "model_dump")
                else revised_section
            ),
            "user_instruction": modification_instruction,
        } if operation == "modification" else None,
    }

    agent = Agent(
        client=llm_client,
        name="EnterprisePolicyValidationAgent",
        instructions=POLICY_VALIDATION_INSTRUCTIONS,
        default_options={
            "response_format": PolicySemanticValidationOutput,
        },
    )

    prompt = (
        "Independently validate the supplied policy. "
        "Treat the validated requirements as authoritative. "
        "Evaluate actual policy meaning, not just requirement ID mappings. "
        "Return a structured semantic validation report.\n\n"
        + json.dumps(
            prompt_data,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    result = await agent.run(prompt)

    return _parse_agent_result(result)
