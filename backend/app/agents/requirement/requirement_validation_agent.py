"""Validate and consolidate a requirement using the full conversation."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from agent_framework import Message
from pydantic import ValidationError

from app.agents.requirement.prompts.validation_prompt import VALIDATION_PROMPT
from app.clients.foundry_client import get_foundry_client
from app.schemas.requirements import (
    GatheringResult,
    RequirementDetails,
    ValidationResult,
)

logger = logging.getLogger(__name__)


def _extract_json_block(text: str) -> str:
    """Extract clean JSON object from model response, stripping markdown code fences."""
    raw = (text or "").strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return raw[first_brace : last_brace + 1].strip()
    return raw


def _normalise(value: str) -> str:
    return " ".join((value or "").casefold().split())


def _merge_missing_draft_fields(
    draft: RequirementDetails,
    gathered: RequirementDetails,
    current_draft: dict[str, Any] | None,
    draft_revision: bool,
) -> RequirementDetails:
    """
    Fill metadata fields omitted by the model without overwriting non-empty model output.
    During draft revision, preserves confirmed rules that were not superseded.
    """
    updates: dict[str, Any] = {}

    previous = (
        RequirementDetails.model_validate(current_draft)
        if draft_revision and current_draft
        else gathered
    )

    for field in ("policy_name", "purpose", "scope"):
        if not getattr(draft, field) and getattr(previous, field):
            updates[field] = getattr(previous, field)

    if not draft.domain or draft.domain.casefold() == "general":
        if previous.domain and previous.domain.casefold() != "general":
            updates["domain"] = previous.domain

    if not draft.stakeholders and previous.stakeholders:
        updates["stakeholders"] = previous.stakeholders

    # Preserve reference provenance from the original gathering snapshot if omitted
    if not draft.reference_data and gathered.reference_data:
        updates["reference_data"] = gathered.reference_data

    # During draft revision, preserve non-superseded rules from previous draft
    if draft_revision and current_draft:
        prev_rules = current_draft.get("rules", [])
        if prev_rules and draft.rules:
            merged_rules = list(draft.rules)
            for pr in prev_rules:
                pr_norm = _normalise(pr)
                pr_topic = pr_norm.split(":")[0].strip()
                # If this rule's topic is not covered in the revised rules, preserve it
                if not any(pr_topic in _normalise(r) for r in merged_rules):
                    merged_rules.append(pr)
            if merged_rules != list(draft.rules):
                updates["rules"] = merged_rules

    return draft.model_copy(update=updates) if updates else draft


async def validate_requirements(
    gathered: GatheringResult,
    conversation_history: str = "",
    questions_asked: int = 0,
    minimum_questions: int = 3,
    maximum_questions: int = 5,
    current_draft: dict[str, Any] | None = None,
    draft_revision: bool = False,
    rejected_questions: list[str] | None = None,
    force_clarification: bool = False,
    force_draft: bool = False,
    original_user_request: str = "",
    latest_user_message: str = "",
) -> ValidationResult:
    """Call the Validation Agent with complete, explicit workflow state."""
    client = get_foundry_client()

    payload = {
        "original_user_request": original_user_request,
        "latest_user_message": latest_user_message,
        "gathered_context": gathered.model_dump(mode="json"),
        "conversation_history": conversation_history,
        "questions_asked": questions_asked,
        "minimum_questions": minimum_questions,
        "maximum_questions": maximum_questions,
        "latest_user_review_draft": current_draft,
        "draft_revision": draft_revision,
        "rejected_questions": rejected_questions or [],
        "force_clarification": force_clarification,
        "force_draft": force_draft,
    }

    prompt = (
        f"{VALIDATION_PROMPT}\n\n"
        "VALIDATION INPUT JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Return exactly one JSON object matching ValidationResult."
    )
    response = await client.get_response(
        messages=[Message(role="user", contents=[prompt])]
    )

    clean_json = _extract_json_block(response.text)

    try:
        result = ValidationResult.model_validate_json(clean_json)
    except (ValidationError, ValueError) as exc:
        raise ValueError(
            "Validation Agent returned invalid JSON or an incompatible schema: "
            f"{exc}. Response: {response.text[:2500]}"
        ) from exc

    if result.draft is not None:
        draft = _merge_missing_draft_fields(
            result.draft,
            gathered.requirements,
            current_draft,
            draft_revision,
        )
        result = result.model_copy(update={"draft": draft})

    return result
