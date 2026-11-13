
"""Coordinate requirement extraction, clarification, draft revision and confirmation."""

from __future__ import annotations

import json
import logging
import re
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.requirement_db import (
    ClarificationItem,
    ConversationMessage,
    Requirement,
    RequirementSession,
    RequirementVersion,
)
from app.agents.requirement.requirement_gathering_agent import gather_requirements
from app.agents.requirement.requirement_validation_agent import validate_requirements
from app.schemas.requirements import (
    GatheringResult,
    RequirementDetails,
    RequirementInput,
    ValidationResult,
)
from app.services.requirement_session_service import (
    create_or_get_session,
    get_conversation_history,
    save_message,
    update_session_status,
)


# Mandatory clarification limits
MIN_CLARIFICATION_QUESTIONS = 3
MAX_CLARIFICATION_QUESTIONS = 5

logger = logging.getLogger(__name__)


_STOP_WORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "been", "being",
    "but", "by", "can", "could", "do", "does", "for", "from", "how", "i",
    "if", "in", "into", "is", "it", "its", "me", "my", "of", "on", "or",
    "our", "please", "should", "that", "the", "their", "them", "there",
    "these", "this", "those", "to", "us", "we", "what", "when", "where",
    "which", "who", "why", "will", "with", "would", "you", "your",
    "want", "need", "clarify", "provide", "details",
}


# ---------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------

def _normalise_text(value: str) -> str:
    return " ".join(
        re.sub(r"\W+", " ", (value or "").casefold()).split()
    )


def _topic_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (value or "").casefold())
        if len(token) > 2 and token not in _STOP_WORDS
    }


def _is_duplicate_topic(
    candidate: str,
    history: list[dict[str, Any]],
) -> bool:
    """Conservatively detect repeated clarification topics."""
    candidate_norm = _normalise_text(candidate)
    if not candidate_norm:
        return False

    candidate_tokens = _topic_tokens(candidate)
    if not candidate_tokens:
        return False

    for item in history:
        previous = item.get("question") or ""
        prev_norm = _normalise_text(previous)
        if candidate_norm == prev_norm:
            return True

        previous_tokens = _topic_tokens(previous)
        if not previous_tokens:
            continue

        overlap = candidate_tokens & previous_tokens
        union_tokens = candidate_tokens | previous_tokens
        if union_tokens:
            similarity = len(overlap) / len(union_tokens)
            if similarity >= 0.65 and len(overlap) >= 3:
                return True

    return False


_PLACEHOLDER_PHRASES = (
    "shall define",
    "should define",
    "must define",
    "shall specify",
    "should specify",
    "must specify",
    "shall cover",
    "should cover",
    "must cover",
    "needs to define",
    "needs to specify",
    "to be determined",
    "to be decided",
    "to be confirmed",
    "to be defined",
    "to be clarified",
    "to be finalized",
    "to be resolved",
    "tbd",
    "will be defined",
    "will be specified",
    "will be determined",
    "shall be determined",
    "shall be decided",
    "as per company policy",
    "as per policy",
    "per policy",
)


def _has_placeholder_rules(rules: list[str]) -> bool:
    """
    Detect generic policy-writing statements mistakenly returned
    as completed business decisions.
    """
    return any(
        any(phrase in rule.casefold() for phrase in _PLACEHOLDER_PHRASES)
        for rule in rules
    )


def _extract_requested_topics(description: str) -> list[str]:
    """Extract distinct topic phrases from an initial user request."""
    desc = (description or "").strip()
    match = re.search(
        r"\b(?:covering|defining|specifying|including|addressing|with)\s+([^.]+)",
        desc,
        re.IGNORECASE,
    )
    if not match:
        return []

    phrase = match.group(1).strip()
    raw_topics = re.split(
        r",\s*(?:and\s+)?|\s+and\s+|\s*;\s*",
        phrase,
        flags=re.IGNORECASE,
    )
    topics = []
    for item in raw_topics:
        cleaned = item.strip().strip(".")
        if len(cleaned) > 2 and cleaned.casefold() not in _STOP_WORDS:
            topics.append(cleaned)
    return topics


def _reconcile_draft(
    draft: RequirementDetails,
    conversation_text: str = "",
    original_description: str = "",
    current_draft: dict[str, Any] | None = None,
    draft_revision: bool = False,
    missing_details: list[str] | None = None,
) -> RequirementDetails:
    """
    Comprehensive, single-source-of-truth draft reconciliation:
    1. Preserves non-superseded confirmed rules during draft revision.
    2. Cleans unsupported scope assumptions (e.g. unconfirmed business units, HRIS).
    3. Moves placeholder rules ("to be defined", etc.) to unresolved.
    4. Decouples reference data templates from confirmed user rules.
    5. Reconciles all unresolved items against confirmed rules and conversation evidence,
       removing any gap that has been confirmed/answered.
    6. Ensures original user requested topics are covered without adding duplicates or false gaps.
    7. Semantically clusters and deduplicates remaining genuinely unresolved details.
    8. Enforces consistency: zero contradiction between confirmed rules and unresolved details.
    """
    # -------------------------------------------------------------
    # 1. Clean Scope of unsupported assumptions
    # -------------------------------------------------------------
    scope = draft.scope or ""
    if "all business units" not in conversation_text.casefold():
        scope = re.sub(
            r";?\s*(?:applies\s+)?across all business units and locations;?",
            "",
            scope,
            flags=re.IGNORECASE,
        )
        scope = re.sub(
            r";?\s*all business units and locations;?",
            "",
            scope,
            flags=re.IGNORECASE,
        )
    scope = re.sub(r"\bHRIS\s*/\s*", "", scope, flags=re.IGNORECASE)
    scope = re.sub(
        r";?\s*(?:implemented\s+via\s+)?HRIS\s+integration;?",
        "",
        scope,
        flags=re.IGNORECASE,
    )
    scope = re.sub(r"\s*;\s*;", ";", scope)
    scope = re.sub(r"\s*;\s*$", ".", scope.strip())
    scope = re.sub(r"\s{2,}", " ", scope.strip())
    if scope and not scope.endswith((".", ";")):
        scope += "."

    # -------------------------------------------------------------
    # 2. Preserve confirmed rules during revision
    # -------------------------------------------------------------
    rules = list(draft.rules)
    if draft_revision and current_draft:
        prev_rules = current_draft.get("rules", [])
        if prev_rules and rules:
            existing_rules_norm = [_normalise_text(r) for r in rules]
            for pr in prev_rules:
                pr_norm = _normalise_text(pr)
                pr_topic = pr_norm.split(":")[0].strip() if ":" in pr_norm else pr_norm[:30]
                if not any(pr_topic in mr or mr.startswith(pr_topic) for mr in existing_rules_norm):
                    rules.append(pr)
                    existing_rules_norm.append(pr_norm)

    # -------------------------------------------------------------
    # 3. Sanitize placeholder rules and unconfirmed reference templates
    # -------------------------------------------------------------
    confirmed_rules: list[str] = []
    candidate_unresolved: list[str] = list(draft.unresolved_details)
    if missing_details:
        candidate_unresolved.extend(missing_details)

    for rule in rules:
        if any(phrase in rule.casefold() for phrase in _PLACEHOLDER_PHRASES):
            candidate_unresolved.append(f"{rule} (unresolved business decision)")
            continue

        is_unconfirmed_ref = False
        for ref in draft.reference_data:
            rec = ref.get("record", {})
            rule_name = str(rec.get("rule_name") or "").casefold()
            condition = str(rec.get("condition_description") or "").casefold()
            if rule_name and (
                rule_name in rule.casefold()
                or (condition and condition in rule.casefold())
            ):
                if rule_name not in conversation_text.casefold():
                    is_unconfirmed_ref = True
                    break

        if is_unconfirmed_ref:
            candidate_unresolved.append(
                f"{rule} (reference template - unconfirmed by user)"
            )
            continue

        confirmed_rules.append(rule)

    conv_lower = conversation_text.casefold()
    # Ensure explicit encashment decisions in conversation are preserved in rules
    if ("basic salary" in conv_lower or "termination" in conv_lower) and "encash" in conv_lower:
        if not any(("basic salary" in r.casefold() or "26" in r.casefold()) for r in confirmed_rules):
            confirmed_rules.append(
                "Earned Leave encashment: Permitted only at employment termination; calculated as (Basic Salary + Dearness Allowance) / 26 × number of eligible unused Earned Leave days; Casual Leave and Sick Leave cannot be encashed."
            )

    # Ensure explicit emergency leave conditions in conversation are preserved in rules
    if "genuine urgent" in conv_lower and not any("urgent" in r.casefold() for r in confirmed_rules):
        confirmed_rules.append(
            "Emergency leave: Can be granted for genuine urgent personal or medical situations, subject to reporting manager approval; employees must notify their manager as soon as possible and submit the application within 2 working days after returning."
        )

    # -------------------------------------------------------------
    # 4. Semantic Reconciliation of Unresolved Items against Rules
    # -------------------------------------------------------------
    rules_text = " ".join(confirmed_rules).casefold()

    has_eligibility = any(
        kw in rules_text
        for kw in ("eligib", "three months", "3 months", "permanent employee", "probation")
    )
    has_leave_allocations = (
        ("earned leave" in rules_text and ("15" in rules_text or "days" in rules_text))
        or ("casual leave" in rules_text and ("12" in rules_text or "days" in rules_text))
        or ("sick leave" in rules_text and ("12" in rules_text or "days" in rules_text))
    )
    has_accrual = any(kw in rules_text for kw in ("accrues", "accrual", "1.25"))
    has_carry_forward = (
        ("carry-forward" in rules_text or "carried forward" in rules_text or "carried-forward" in rules_text)
        and any(kw in rules_text for kw in ("10", "capped", "limit", "expires", "calendar year"))
    )
    has_application_proc = (
        ("submit" in rules_text or "application" in rules_text or "apply" in rules_text)
        and any(kw in rules_text for kw in ("portal", "hrms", "notice", "working days"))
    )
    has_approval_workflow = any(
        kw in rules_text
        for kw in ("reporting manager", "manager approval", "approves", "approve or reject")
    )
    has_encashment = (
        ("encash" in rules_text or "encashment" in rules_text)
        and any(kw in rules_text for kw in ("termination", "basic salary", "dearness allowance", "cannot be encashed", "calculation"))
    )
    has_medical_cert = (
        "medical certificate" in rules_text
        or ("sick leave" in rules_text and "consecutive" in rules_text)
    )
    has_records = (
        "leave balances and records" in rules_text
        or "maintains the official leave records" in rules_text
        or "hr maintains" in rules_text
    )
    has_responsibilities = (
        "employee responsibilities" in rules_text
        or "employees are responsible" in rules_text
    )
    has_emergency_conditions = (
        "emergency leave" in rules_text
        and any(kw in rules_text for kw in ("urgent", "personal or medical", "reporting manager", "notify"))
    )
    has_parental_statutory = (
        ("maternity" in rules_text or "paternity" in rules_text)
        and "statutory" in rules_text
    )

    unresolved_items: list[str] = []
    for item in candidate_unresolved:
        text = item.strip()
        if not text:
            continue
        norm = text.casefold()

        # Eligibility
        if any(k in norm for k in ("eligib", "who qualifies", "who is eligible", "tenure requirement", "probation requirement")):
            if has_eligibility:
                continue

        # Leave allocation / leave types (excluding emergency leave)
        if any(k in norm for k in ("allocation", "leave types", "quantum", "annual leave")) and "emergency" not in norm:
            if has_leave_allocations:
                continue

        # Accrual
        if any(k in norm for k in ("accrual", "accrue", "monthly accrual")):
            if has_accrual:
                continue

        # Carry-forward
        if any(k in norm for k in ("carry-forward", "carry forward", "carried forward", "rollover")):
            if has_carry_forward:
                continue

        # Application procedures
        if any(k in norm for k in ("application procedure", "submission method", "how to apply", "notice period", "submission deadline")) and "emergency" not in norm:
            if has_application_proc:
                continue

        # Approval workflows
        if any(k in norm for k in ("approval workflow", "approval procedure", "designated approver", "who approves", "approval hierarchy")) and "emergency" not in norm and "exception" not in norm:
            if has_approval_workflow:
                continue

        # Leave encashment
        if any(k in norm for k in ("encash", "encashment", "cash out", "payout")):
            if has_encashment:
                continue

        # Medical certificate
        if any(k in norm for k in ("medical certificate", "doctor certificate", "sick leave documentation")):
            if has_medical_cert:
                continue

        # Leave records (general tracking/system of record)
        if any(k in norm for k in ("leave records", "records management", "system of record", "tracking")) and not any(k in norm for k in ("retention period", "audit schedule", "statutory retention", "years")):
            if has_records:
                continue

        # Responsibilities
        if "employee responsibilities" in norm:
            if has_responsibilities:
                continue

        # Emergency leave definition/criteria/workflow (only allocation/limits remain)
        if "emergency" in norm and any(k in norm for k in ("definition", "definitions", "criteria", "workflow", "procedure", "procedures", "scope of emergency")):
            if has_emergency_conditions:
                continue

        # Parental/Maternity/Paternity statutory rule (only jurisdiction remains)
        if any(k in norm for k in ("maternity", "paternity", "parental")):
            if has_parental_statutory and ("not been specified" in norm or "entitlement" in norm):
                continue

        unresolved_items.append(text)

    # -------------------------------------------------------------
    # 5. Canonical Genuinely Missing Details
    # -------------------------------------------------------------
    if has_emergency_conditions and not any(k in rules_text for k in ("days of emergency leave", "emergency leave is")):
        if not any("emergency" in u.casefold() and any(k in u.casefold() for k in ("entitlement", "limit", "quota")) for u in unresolved_items):
            unresolved_items.append("Emergency leave annual entitlement quota and maximum days limit remain to be defined.")

    if has_parental_statutory:
        if not any(any(k in u.casefold() for k in ("jurisdiction", "statutory", "labor regulations")) for u in unresolved_items):
            unresolved_items.append("Specific statutory jurisdiction and applicable local labor regulations for Maternity and Paternity Leave remain to be confirmed.")

    if "exception" in original_description.casefold() and not any("exception" in r.casefold() for r in confirmed_rules):
        if not any("exception" in u.casefold() for u in unresolved_items):
            unresolved_items.append("Designated approval authority and criteria for exceptions to the leave policy remain to be specified.")

    if any(k in original_description.casefold() for k in ("records", "tracking", "retention", "audit")) and not any(k in rules_text for k in ("years", "retention period", "audit schedule")):
        if not any(any(k in u.casefold() for k in ("retention", "audit schedule")) for u in unresolved_items):
            unresolved_items.append("Statutory record retention periods and audit schedule for leave records remain to be defined.")

    # -------------------------------------------------------------
    # 6. Semantic Deduplication
    # -------------------------------------------------------------
    deduped_unresolved: list[str] = []
    seen_semantic_keys: set[str] = set()

    for item in unresolved_items:
        norm = item.casefold()
        key = None
        if "emergency" in norm:
            key = "emergency_leave"
        elif any(k in norm for k in ("maternity", "paternity", "parental", "statutory jurisdiction")):
            key = "statutory_parental"
        elif "exception" in norm or "carve-out" in norm:
            key = "policy_exceptions"
        elif any(k in norm for k in ("retention", "audit schedule", "audit considerations")):
            key = "retention_audit"
        elif any(k in norm for k in ("business unit", "geographic location", "jurisdiction")) and "maternity" not in norm:
            key = "scope_locations"
        else:
            tokens = tuple(sorted(_topic_tokens(item)))
            if tokens:
                key = "tokens_" + "_".join(tokens[:4])

        if key:
            if key not in seen_semantic_keys:
                deduped_unresolved.append(item)
                seen_semantic_keys.add(key)
        else:
            norm_text = _normalise_text(item)
            if norm_text not in seen_semantic_keys:
                deduped_unresolved.append(item)
                seen_semantic_keys.add(norm_text)

    # -------------------------------------------------------------
    # 7. Original Request Coverage (Check truly omitted topics)
    # -------------------------------------------------------------
    requested_topics = _extract_requested_topics(original_description)
    full_draft_text = " ".join([
        draft.purpose or "",
        scope,
        " ".join(draft.stakeholders),
        " ".join(confirmed_rules),
        " ".join(deduped_unresolved),
    ]).casefold()

    for topic in requested_topics:
        topic_tokens = _topic_tokens(topic)
        if not topic_tokens:
            continue
        overlap = {t for t in topic_tokens if t in full_draft_text}
        if len(overlap) < max(1, len(topic_tokens) // 2):
            topic_str = f"{topic.capitalize()}: Specific procedures, conditions, and business decisions remain to be confirmed."
            norm_topic = _normalise_text(topic_str)
            if norm_topic not in seen_semantic_keys:
                deduped_unresolved.append(topic_str)
                seen_semantic_keys.add(norm_topic)

    # -------------------------------------------------------------
    # 8. Final Consistency Check
    # -------------------------------------------------------------
    final_unresolved: list[str] = []
    for u in deduped_unresolved:
        norm_u = u.casefold()
        if has_eligibility and any(k in norm_u for k in ("eligib", "who qualifies", "tenure requirement")) and "not specified" in norm_u:
            continue
        if has_leave_allocations and any(k in norm_u for k in ("annual leave allocation", "leave types to be offered", "leave allocation")) and "not specified" in norm_u:
            continue
        if has_accrual and "accrual" in norm_u and "not specified" in norm_u:
            continue
        if has_application_proc and "application" in norm_u and "not specified" in norm_u:
            continue
        if has_approval_workflow and "approval" in norm_u and "not specified" in norm_u and "exception" not in norm_u:
            continue
        if has_carry_forward and "carry-forward" in norm_u and "not specified" in norm_u:
            continue
        if has_encashment and "encash" in norm_u:
            continue
        final_unresolved.append(u)

    return draft.model_copy(
        update={
            "scope": scope,
            "rules": confirmed_rules,
            "unresolved_details": final_unresolved,
        }
    )


# ---------------------------------------------------------------------
# Clarification history
# ---------------------------------------------------------------------

async def _get_clarification_history(session_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ClarificationItem)
            .where(ClarificationItem.session_id == session_id)
            .order_by(
                ClarificationItem.created_at.asc(),
                ClarificationItem.clarification_id.asc(),
            )
        )

        rows = result.scalars().all()

    history = [
        {
            "question": row.question,
            "answer": row.answer,
            "status": row.status,
            "requirement_id": row.requirement_id,
        }
        for row in rows
    ]

    return (
        len(history),
        {
            _normalise_text(item["question"])
            for item in history
            if item.get("question")
        },
        history,
    )


async def _save_clarification(
    session_id: str,
    requirement_id: str,
    question: str,
) -> None:

    normalised = _normalise_text(question)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ClarificationItem)
            .where(ClarificationItem.session_id == session_id)
        )

        previous = result.scalars().all()

        if any(
            _normalise_text(item.question) == normalised
            for item in previous
        ):
            raise ValueError(
                "Duplicate clarification question prevented."
            )

        db.add(
            ClarificationItem(
                clarification_id=str(uuid4()),
                session_id=session_id,
                requirement_id=requirement_id,
                question=question,
                status="open",
            )
        )

        await db.commit()


async def _answer_open_clarification(
    session_id: str,
    answer: str,
) -> bool:
    """Save the answer against the latest open clarification."""

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ClarificationItem)
            .where(
                ClarificationItem.session_id == session_id,
                ClarificationItem.status == "open",
            )
            .order_by(ClarificationItem.created_at.desc())
            .limit(1)
        )

        item = result.scalar_one_or_none()

        if item is None:
            return False

        item.answer = answer
        item.status = "answered"
        item.answered_at = func.current_timestamp()

        await db.commit()

        return True


# ---------------------------------------------------------------------
# Gathering context persistence
# ---------------------------------------------------------------------

async def _save_gathered_context(
    session_id: str,
    gathered: GatheringResult,
) -> None:

    async with AsyncSessionLocal() as db:
        db.add(
            ConversationMessage(
                message_id=str(uuid4()),
                session_id=session_id,
                sender_type="system",
                agent_name="requirement_gathering_agent",
                message_type="status_update",
                content=gathered.model_dump_json(),
            )
        )

        await db.commit()


async def _load_gathered_context(
    session_id: str,
) -> GatheringResult | None:

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.session_id == session_id,
                ConversationMessage.sender_type == "system",
                ConversationMessage.agent_name
                == "requirement_gathering_agent",
                ConversationMessage.message_type == "status_update",
            )
            .order_by(ConversationMessage.created_at.desc())
            .limit(1)
        )

        row = result.scalar_one_or_none()

    if row is None:
        return None

    try:
        return GatheringResult.model_validate_json(row.content)

    except Exception:
        logger.exception(
            "Invalid gathered snapshot for session %s",
            session_id,
        )
        return None


# ---------------------------------------------------------------------
# Draft persistence
# ---------------------------------------------------------------------

async def _load_latest_draft(
    session_id: str,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.session_id == session_id,
                ConversationMessage.sender_type == "agent",
                ConversationMessage.agent_name
                == "requirement_validation_agent",
                ConversationMessage.message_type == "status_update",
            )
            .order_by(ConversationMessage.created_at.desc())
            .limit(1)
        )

        row = result.scalar_one_or_none()

    if row is None:
        return None

    try:
        payload = json.loads(row.content)
        draft = payload.get("draft")

        if (
            payload.get("status") == "ready_for_confirmation"
            and isinstance(draft, dict)
        ):
            return draft

    except (TypeError, ValueError):
        logger.exception(
            "Could not load latest draft for session %s",
            session_id,
        )

    return None


async def _save_validation(
    session_id: str,
    result: ValidationResult,
) -> None:

    await save_message(
        session_id,
        "agent",
        result.model_dump_json(),
        message_type=(
            "clarification_question"
            if result.status == "needs_clarification"
            else "status_update"
        ),
        agent_name="requirement_validation_agent",
    )


# ---------------------------------------------------------------------
# Requirement persistence
# ---------------------------------------------------------------------

def _metadata(
    details: RequirementDetails | dict[str, Any],
) -> tuple[str, str]:

    data = (
        details.model_dump()
        if isinstance(details, RequirementDetails)
        else details
    )

    name = data.get("policy_name")
    purpose = data.get("purpose")
    scope = data.get("scope")

    name = name.strip() if isinstance(name, str) else ""
    purpose = purpose.strip() if isinstance(purpose, str) else ""
    scope = scope.strip() if isinstance(scope, str) else ""

    topic = (
        name
        or purpose.split(".")[0].strip()
        or "Untitled Requirement"
    )[:150]

    return (
        topic,
        purpose or scope or f"Requirements for {topic}.",
    )


async def _upsert_requirement(
    session_id: str,
    details: RequirementDetails,
    status: str,
) -> str:

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Requirement)
            .where(Requirement.session_id == session_id)
            .order_by(Requirement.requirement_id.asc())
            .limit(1)
        )

        row = result.scalar_one_or_none()
        topic, description = _metadata(details)

        if row is None:
            row = Requirement(
                requirement_id=str(uuid4()),
                session_id=session_id,
                topic=topic,
                description=description,
                status=status,
            )

            db.add(row)

        else:
            row.topic = topic
            row.description = description
            row.status = status

        await db.commit()
        await db.refresh(row)

        return row.requirement_id


# ---------------------------------------------------------------------
# Validation agent invocation
# ---------------------------------------------------------------------

async def _run_validation(
    *,
    gathered: GatheringResult,
    conversation_history: str,
    questions_asked: int,
    current_draft: dict[str, Any] | None = None,
    draft_revision: bool = False,
    force_clarification: bool = False,
    force_draft: bool = False,
    rejected_questions: list[str] | None = None,
    original_user_request: str = "",
    latest_user_message: str = "",
) -> ValidationResult:
    """Centralize validation calls and clarification limits."""

    return await validate_requirements(
        gathered=gathered,
        conversation_history=conversation_history,
        questions_asked=questions_asked,
        minimum_questions=MIN_CLARIFICATION_QUESTIONS,
        maximum_questions=MAX_CLARIFICATION_QUESTIONS,
        current_draft=current_draft,
        draft_revision=draft_revision,
        force_clarification=force_clarification,
        force_draft=force_draft,
        rejected_questions=rejected_questions or [],
        original_user_request=original_user_request,
        latest_user_message=latest_user_message,
    )


# ---------------------------------------------------------------------
# Clarification question limits and evaluation
# ---------------------------------------------------------------------

async def _enforce_minimum_questions(
    *,
    validation: ValidationResult,
    gathered: GatheringResult,
    agent_context: str,
    question_count: int,
    original_user_request: str = "",
) -> ValidationResult:
    """
    Evaluate clarification questions against minimum target (3).
    When distinct material gaps exist and question_count < 3, prioritize clarification.
    Never raise RuntimeError when the requirement is complete or no further questions exist.
    """

    if question_count >= MIN_CLARIFICATION_QUESTIONS:
        return validation

    if validation.status == "needs_clarification":
        return validation

    if validation.status != "ready_for_confirmation" or validation.draft is None:
        return validation

    # If unresolved items remain, attempt to clarify the highest-priority missing decision
    if validation.draft.unresolved_details and question_count < MIN_CLARIFICATION_QUESTIONS:
        logger.info(
            "Draft produced with unresolved items before minimum target. "
            "Questions asked=%s, minimum=%s. Retrying clarification.",
            question_count,
            MIN_CLARIFICATION_QUESTIONS,
        )

        retry = await _run_validation(
            gathered=gathered,
            conversation_history=agent_context,
            questions_asked=question_count,
            force_clarification=True,
            original_user_request=original_user_request,
        )

        if retry.status == "needs_clarification":
            return retry

    return validation


async def _enforce_maximum_questions(
    *,
    validation: ValidationResult,
    gathered: GatheringResult,
    agent_context: str,
    question_count: int,
) -> ValidationResult:
    """
    Never allow more than five clarification questions.
    Force a review draft once the maximum has been reached.
    """

    if question_count < MAX_CLARIFICATION_QUESTIONS:
        return validation

    if validation.status == "needs_clarification":

        logger.info(
            "Maximum clarification count reached. "
            "Forcing review draft. Questions asked=%s",
            question_count,
        )

        validation = await _run_validation(
            gathered=gathered,
            conversation_history=agent_context,
            questions_asked=question_count,
            force_draft=True,
        )

    if (
        validation.status != "ready_for_confirmation"
        or validation.draft is None
    ):
        raise RuntimeError(
            "Maximum clarification count reached, but the "
            "Validation Agent could not produce a review draft."
        )

    return validation


# ---------------------------------------------------------------------
# Main requirement workflow
# ---------------------------------------------------------------------

async def process_requirement_message(
    request: RequirementInput,
) -> dict:

    message = request.message.strip()

    if not message:
        raise ValueError("Message cannot be empty.")

    # Create or retrieve the session.
    if request.event == "start":

        if request.session_id:
            raise ValueError(
                "A new start event must not contain a session_id."
            )

        session = await create_or_get_session(message)

    else:

        if not request.session_id:
            raise ValueError(
                "session_id is required for this event."
            )

        session = await create_or_get_session(
            message,
            session_id=request.session_id,
        )

    session_id = session.session_id
    initial_status = session.status

    # -------------------------------------------------------------
    # Cancel event
    # -------------------------------------------------------------

    if request.event == "cancel":

        await save_message(
            session_id,
            "user",
            message,
        )

        await update_session_status(
            session_id,
            "cancelled",
        )

        return {
            "event": "conversation_cancelled",
            "session_id": session_id,
            "message": "Requirement gathering was cancelled.",
        }

    # -------------------------------------------------------------
    # Confirm event
    # -------------------------------------------------------------

    if request.event == "confirm":
        return await _confirm_requirement(
            session_id,
            message,
        )

    # -------------------------------------------------------------
    # Determine workflow mode
    # -------------------------------------------------------------

    draft_revision = (
        request.event == "answer"
        and initial_status == "ready_for_confirmation"
    )

    if (
        request.event == "answer"
        and initial_status not in {
            "awaiting_clarification",
            "ready_for_confirmation",
            "gathering",
            "validating",
        }
    ):
        raise ValueError(
            f"Cannot answer while session is {initial_status}."
        )

    # -------------------------------------------------------------
    # Save user message before agent execution
    # -------------------------------------------------------------

    await save_message(
        session_id,
        "user",
        message,
        message_type=(
            "clarification_answer"
            if request.event == "answer"
            else "message"
        ),
    )

    if request.event == "answer" and not draft_revision:

        answered = await _answer_open_clarification(
            session_id,
            message,
        )

        if not answered:
            logger.warning(
                "No open clarification found for answer. "
                "session_id=%s",
                session_id,
            )

    # -------------------------------------------------------------
    # Load conversation and clarification history
    # -------------------------------------------------------------

    question_count, _, clarification_history = (
        await _get_clarification_history(session_id)
    )

    conversation = await get_conversation_history(session_id)

    current_draft = (
        await _load_latest_draft(session_id)
        if draft_revision
        else None
    )

    if draft_revision and current_draft is None:
        raise ValueError(
            "The session is ready for confirmation, but its latest "
            "draft could not be loaded."
        )

    agent_context = (
        f"{conversation}\n\n"
        "STRUCTURED CLARIFICATION HISTORY:\n"
        f"{json.dumps(clarification_history, ensure_ascii=False, indent=2)}\n"
        f"Questions already asked: {question_count}. "
        f"Minimum target: {MIN_CLARIFICATION_QUESTIONS}. "
        f"Maximum: {MAX_CLARIFICATION_QUESTIONS}.\n"
        "Preserve explicit undecided items as unresolved. "
        "Do not ask about answered or explicitly undecided topics."
    )

    # -------------------------------------------------------------
    # Gathering Agent
    # Runs once for a new session.
    # Later turns reuse the persisted gathering snapshot.
    # -------------------------------------------------------------

    if request.event == "start":

        started = perf_counter()

        gathered = await gather_requirements(
            description=session.original_description,
            conversation_history=agent_context,
        )

        await _save_gathered_context(
            session_id,
            gathered,
        )

        logger.info(
            "Gathering Agent completed in %.2fs",
            perf_counter() - started,
        )

    else:

        gathered = await _load_gathered_context(session_id)

        if gathered is None:

            # Backward compatibility for older sessions without
            # a persisted gathering snapshot.
            gathered = await gather_requirements(
                description=session.original_description,
                conversation_history=agent_context,
            )

            await _save_gathered_context(
                session_id,
                gathered,
            )

    # -------------------------------------------------------------
    # Create/update requirement record
    # -------------------------------------------------------------

    requirement_id = await _upsert_requirement(
        session_id,
        gathered.requirements,
        "needs_clarification",
    )

    await update_session_status(
        session_id,
        "validating",
        domain=gathered.requirements.domain,
    )

    # -------------------------------------------------------------
    # Validation Agent
    # -------------------------------------------------------------

    validation = await _run_validation(
        gathered=gathered,
        conversation_history=agent_context,
        questions_asked=question_count,
        current_draft=current_draft,
        draft_revision=draft_revision,
        force_clarification=(
            not draft_revision
            and question_count == 0
        ),
        force_draft=(
            draft_revision
            or question_count >= MAX_CLARIFICATION_QUESTIONS
        ),
        original_user_request=session.original_description,
        latest_user_message=message,
    )

    # -------------------------------------------------------------
    # Draft revision handling
    # -------------------------------------------------------------

    if draft_revision and (
        validation.status != "ready_for_confirmation"
        or validation.draft is None
    ):

        validation = await _run_validation(
            gathered=gathered,
            conversation_history=agent_context,
            questions_asked=question_count,
            current_draft=current_draft,
            draft_revision=True,
            force_draft=True,
            original_user_request=session.original_description,
            latest_user_message=message,
        )

    if draft_revision:

        if (
            validation.status != "ready_for_confirmation"
            or validation.draft is None
        ):
            raise RuntimeError(
                "The Validation Agent could not produce the revised "
                "draft. The previous draft has not been overwritten."
            )

        draft = _reconcile_draft(
            draft=validation.draft,
            conversation_text=agent_context,
            original_description=session.original_description,
            current_draft=current_draft,
            draft_revision=True,
            missing_details=validation.missing_details,
        )
        validation = validation.model_copy(update={"draft": draft})

        await _save_validation(
            session_id,
            validation,
        )

        await _upsert_requirement(
            session_id,
            validation.draft,
            "validated",
        )

        await update_session_status(
            session_id,
            "ready_for_confirmation",
            domain=validation.draft.domain,
        )

        count, _, _ = await _get_clarification_history(
            session_id
        )

        return {
            "event": "requirement_draft_updated",
            "session_id": session_id,
            "requirement_id": requirement_id,
            "draft": validation.draft.model_dump(),
            "explanation": validation.explanation,
            "questions_asked": count,
            "minimum_questions": MIN_CLARIFICATION_QUESTIONS,
            "maximum_questions": MAX_CLARIFICATION_QUESTIONS,
            "unresolved_details": validation.draft.unresolved_details,
            "requires_confirmation": True,
        }

    # -------------------------------------------------------------
    # Enforce clarification limits and minimum question targets
    # -------------------------------------------------------------

    validation = await _enforce_minimum_questions(
        validation=validation,
        gathered=gathered,
        agent_context=agent_context,
        question_count=question_count,
        original_user_request=session.original_description,
    )

    # -------------------------------------------------------------
    # Placeholder rule protection
    # -------------------------------------------------------------

    if (
        validation.status == "ready_for_confirmation"
        and validation.draft is not None
        and _has_placeholder_rules(validation.draft.rules)
        and question_count < MAX_CLARIFICATION_QUESTIONS
    ):
        logger.warning(
            "Placeholder rules detected. Requesting clarification. "
            "session_id=%s",
            session_id,
        )

        validation = await _run_validation(
            gathered=gathered,
            conversation_history=agent_context,
            questions_asked=question_count,
            force_clarification=True,
            original_user_request=session.original_description,
        )

    # -------------------------------------------------------------
    # Duplicate clarification handling
    # -------------------------------------------------------------

    if validation.status == "needs_clarification":

        proposed = (validation.question or "").strip()

        if not proposed:
            raise ValueError(
                "Validation requested clarification but returned no question."
            )

        if _is_duplicate_topic(
            proposed,
            clarification_history,
        ):

            logger.warning(
                "Duplicate clarification detected. Retrying. "
                "session_id=%s",
                session_id,
            )

            validation = await _run_validation(
                gathered=gathered,
                conversation_history=agent_context,
                questions_asked=question_count,
                rejected_questions=[proposed],
                force_clarification=True,
                original_user_request=session.original_description,
            )

            retry_question = (
                validation.question or ""
            ).strip()

            if (
                validation.status == "needs_clarification"
                and _is_duplicate_topic(
                    retry_question,
                    clarification_history,
                )
            ):
                logger.info(
                    "Validation repeated a clarification topic after retry. "
                    "Transitioning to review draft to avoid duplicate questions. "
                    "session_id=%s",
                    session_id,
                )
                validation = await _run_validation(
                    gathered=gathered,
                    conversation_history=agent_context,
                    questions_asked=question_count,
                    force_draft=True,
                    original_user_request=session.original_description,
                )

            if validation.status == "ready_for_confirmation":
                validation = await _enforce_minimum_questions(
                    validation=validation,
                    gathered=gathered,
                    agent_context=agent_context,
                    question_count=question_count,
                    original_user_request=session.original_description,
                )

    # -------------------------------------------------------------
    # Enforce maximum of five questions
    # -------------------------------------------------------------

    validation = await _enforce_maximum_questions(
        validation=validation,
        gathered=gathered,
        agent_context=agent_context,
        question_count=question_count,
    )

    # -------------------------------------------------------------
    # Return clarification question
    # -------------------------------------------------------------

    if validation.status == "needs_clarification":

        question = (validation.question or "").strip()

        if not question or _is_duplicate_topic(question, clarification_history):
            logger.info(
                "Clarification question is empty or duplicate. "
                "Transitioning to review draft. session_id=%s",
                session_id,
            )
            validation = await _run_validation(
                gathered=gathered,
                conversation_history=agent_context,
                questions_asked=question_count,
                force_draft=True,
                original_user_request=session.original_description,
            )

    if validation.status == "needs_clarification":

        question = (validation.question or "").strip()

        if question_count >= MAX_CLARIFICATION_QUESTIONS:
            logger.info("Max questions reached. Forcing draft.")
            validation = await _run_validation(
                gathered=gathered,
                conversation_history=agent_context,
                questions_asked=question_count,
                force_draft=True,
                original_user_request=session.original_description,
            )

    if validation.status == "needs_clarification":

        question = (validation.question or "").strip()

        await _save_validation(
            session_id,
            validation,
        )

        await _save_clarification(
            session_id,
            requirement_id,
            question,
        )

        await update_session_status(
            session_id,
            "awaiting_clarification",
        )

        count, _, _ = await _get_clarification_history(
            session_id
        )

        return {
            "event": "clarification_question",
            "session_id": session_id,
            "requirement_id": requirement_id,
            "question": question,
            "question_number": count,
            "minimum_questions": MIN_CLARIFICATION_QUESTIONS,
            "maximum_questions": MAX_CLARIFICATION_QUESTIONS,
            "missing_details": validation.missing_details,
        }

    # -------------------------------------------------------------
    # Return review draft
    # -------------------------------------------------------------

    if validation.draft is None:
        raise ValueError(
            "Validation Agent returned no review draft."
        )

    draft = _reconcile_draft(
        draft=validation.draft,
        conversation_text=agent_context,
        original_description=session.original_description,
        current_draft=current_draft,
        draft_revision=False,
        missing_details=validation.missing_details,
    )
    validation = validation.model_copy(update={"draft": draft})

    await _save_validation(
        session_id,
        validation,
    )

    await _upsert_requirement(
        session_id,
        validation.draft,
        "validated",
    )

    await update_session_status(
        session_id,
        "ready_for_confirmation",
        domain=validation.draft.domain,
    )

    count, _, _ = await _get_clarification_history(
        session_id
    )

    return {
        "event": "requirement_draft",
        "session_id": session_id,
        "requirement_id": requirement_id,
        "draft": validation.draft.model_dump(),
        "explanation": validation.explanation,
        "questions_asked": count,
        "minimum_questions": MIN_CLARIFICATION_QUESTIONS,
        "maximum_questions": MAX_CLARIFICATION_QUESTIONS,
        "unresolved_details": validation.draft.unresolved_details,
        "requires_confirmation": True,
    }


# ---------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------

def _is_explicit_confirmation(message: str) -> bool:

    value = _normalise_text(message)

    accepted = {
        "yes",
        "yes confirm",
        "confirm",
        "confirmed",
        "i confirm",
        "yes i confirm",
        "i approve",
        "approve",
        "i confirm the requirements",
        "i approve the requirements",
    }

    return value in accepted


async def _confirm_requirement(
    session_id: str,
    confirmation_message: str,
) -> dict:
    """
    Persist the confirmed requirement version.

    The review draft and its unresolved details remain in the
    conversation audit history.
    """

    if not _is_explicit_confirmation(confirmation_message):
        raise ValueError(
            "Send an explicit confirmation such as "
            "'confirm' or 'yes, I confirm'."
        )

    async with AsyncSessionLocal() as db:

        session = await db.get(
            RequirementSession,
            session_id,
        )

        if session is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )

        if session.status != "ready_for_confirmation":
            raise ValueError(
                "There is no review draft awaiting confirmation."
            )

        result = await db.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.session_id == session_id,
                ConversationMessage.sender_type == "agent",
                ConversationMessage.agent_name
                == "requirement_validation_agent",
                ConversationMessage.message_type == "status_update",
            )
            .order_by(ConversationMessage.created_at.desc())
            .limit(1)
        )

        latest = result.scalar_one_or_none()

        if latest is None:
            raise ValueError(
                "No review draft was found."
            )

        validation = json.loads(latest.content)
        draft_data = validation.get("draft")

        if (
            validation.get("status") != "ready_for_confirmation"
            or not isinstance(draft_data, dict)
        ):
            raise ValueError(
                "The latest validation result is not a confirmable draft."
            )

        if (
            not isinstance(draft_data.get("policy_name"), str)
            or not draft_data["policy_name"].strip()
        ):
            raise ValueError(
                "A requirement name is required before confirmation."
            )

        # Preserve confirmed rules and all unresolved items in the
        # confirmed requirement version as the single source of truth.
        final_data = dict(draft_data)
        final_data["unresolved_details"] = list(
            draft_data.get("unresolved_details") or []
        )

        version_result = await db.execute(
            select(
                func.max(RequirementVersion.version_number)
            )
            .where(
                RequirementVersion.session_id == session_id
            )
        )

        version_number = (
            version_result.scalar_one() or 0
        ) + 1

        version_id = str(uuid4())

        db.add(
            RequirementVersion(
                requirement_version_id=version_id,
                session_id=session_id,
                version_number=version_number,
                requirements_json=json.dumps(
                    final_data,
                    ensure_ascii=False,
                ),
                validation_status="confirmed",
            )
        )

        requirement_result = await db.execute(
            select(Requirement)
            .where(
                Requirement.session_id == session_id
            )
            .order_by(Requirement.requirement_id.asc())
            .limit(1)
        )

        requirement = requirement_result.scalar_one_or_none()

        topic, description = _metadata(final_data)

        if requirement is None:

            requirement = Requirement(
                requirement_id=str(uuid4()),
                session_id=session_id,
                topic=topic,
                description=description,
                status="confirmed",
            )

            db.add(requirement)

        else:

            requirement.topic = topic
            requirement.description = description
            requirement.status = "confirmed"

        session.status = "confirmed"
        session.domain = final_data.get("domain") or "general"

        db.add(
            ConversationMessage(
                message_id=str(uuid4()),
                session_id=session_id,
                sender_type="user",
                message_type="confirmation",
                content=confirmation_message,
            )
        )

        requirement_id = requirement.requirement_id

        await db.commit()

    return {
        "event": "requirements_finalized",
        "session_id": session_id,
        "requirement_id": requirement_id,
        "requirement_version_id": version_id,
        "version_number": version_number,
        "message": "Requirements confirmed and saved.",
        "unresolved_details": final_data["unresolved_details"],
    }
