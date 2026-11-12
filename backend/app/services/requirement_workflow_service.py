
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

    candidate_tokens = _topic_tokens(candidate)

    if not candidate_tokens:
        return False

    for item in history:
        previous = item.get("question") or ""

        if _normalise_text(candidate) == _normalise_text(previous):
            return True

        previous_tokens = _topic_tokens(previous)
        overlap = candidate_tokens & previous_tokens

        if len(overlap) >= 2:
            similarity = len(overlap) / max(
                1,
                min(len(candidate_tokens), len(previous_tokens)),
            )

            if similarity >= 0.65:
                return True

    return False


def _has_placeholder_rules(rules: list[str]) -> bool:
    """
    Detect generic policy-writing statements mistakenly returned
    as completed business decisions.
    """

    placeholder_phrases = (
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
    )

    return any(
        any(
            phrase in rule.casefold()
            for phrase in placeholder_phrases
        )
        for rule in rules
    )


def _merge_missing_details(
    draft: RequirementDetails,
    missing_details: list[str],
) -> RequirementDetails:
    """Preserve unresolved details returned by validation."""

    values = list(draft.unresolved_details)
    seen = {_normalise_text(item) for item in values}

    for item in missing_details:
        value = item.strip()
        key = _normalise_text(value)

        if value and key not in seen:
            values.append(value)
            seen.add(key)

    return draft.model_copy(
        update={"unresolved_details": values}
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
    )


# ---------------------------------------------------------------------
# Mandatory clarification enforcement
# ---------------------------------------------------------------------

async def _enforce_minimum_questions(
    *,
    validation: ValidationResult,
    gathered: GatheringResult,
    agent_context: str,
    question_count: int,
) -> ValidationResult:
    """
    Do not permit a review draft before three clarification questions.

    If the model returns a draft too early, request clarification.
    If it still cannot produce a question, fail safely instead of
    silently bypassing the configured minimum.
    """

    if question_count >= MIN_CLARIFICATION_QUESTIONS:
        return validation

    if validation.status == "needs_clarification":
        return validation

    if validation.status != "ready_for_confirmation":
        return validation

    logger.warning(
        "Draft returned before mandatory minimum. "
        "Questions asked=%s, minimum=%s",
        question_count,
        MIN_CLARIFICATION_QUESTIONS,
    )

    validation = await _run_validation(
        gathered=gathered,
        conversation_history=agent_context,
        questions_asked=question_count,
        force_clarification=True,
    )

    if validation.status != "needs_clarification":
        raise RuntimeError(
            "Minimum clarification requirement not satisfied. "
            f"At least {MIN_CLARIFICATION_QUESTIONS} clarification "
            "questions must be asked before producing a draft. "
            "The Validation Agent did not return another valid question."
        )

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
            "draft_revision"
            if draft_revision
            else "clarification_answer"
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
            and question_count < MIN_CLARIFICATION_QUESTIONS
        ),
        force_draft=(
            draft_revision
            or question_count >= MAX_CLARIFICATION_QUESTIONS
        ),
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

        validation = validation.model_copy(
            update={
                "draft": _merge_missing_details(
                    validation.draft,
                    validation.missing_details,
                )
            }
        )

        if _has_placeholder_rules(validation.draft.rules):
            raise RuntimeError(
                "The revised draft contains generic policy-writing "
                "statements instead of actual business decisions."
            )

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
    # Enforce mandatory minimum of three questions
    # -------------------------------------------------------------

    validation = await _enforce_minimum_questions(
        validation=validation,
        gathered=gathered,
        agent_context=agent_context,
        question_count=question_count,
    )

    # -------------------------------------------------------------
    # Placeholder rule protection
    # -------------------------------------------------------------

    if (
        validation.status == "ready_for_confirmation"
        and validation.draft is not None
        and _has_placeholder_rules(validation.draft.rules)
    ):

        if question_count >= MAX_CLARIFICATION_QUESTIONS:
            raise RuntimeError(
                "The Validation Agent returned placeholder rules "
                "after the maximum clarification count. "
                "The draft cannot be accepted as a valid specification."
            )

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
        )

        if validation.status != "needs_clarification":
            raise RuntimeError(
                "Validation returned an incomplete draft instead of "
                "a meaningful clarification question."
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
                raise RuntimeError(
                    "Validation repeated a covered clarification topic "
                    "after retry. No duplicate question was saved."
                )

            if validation.status == "ready_for_confirmation":
                validation = await _enforce_minimum_questions(
                    validation=validation,
                    gathered=gathered,
                    agent_context=agent_context,
                    question_count=question_count,
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

        if not question:
            raise ValueError(
                "Validation requested clarification but returned no question."
            )

        if _is_duplicate_topic(
            question,
            clarification_history,
        ):
            raise ValueError(
                "Validation repeated a covered clarification topic. "
                "The previous draft and conversation remain unchanged."
            )

        if question_count >= MAX_CLARIFICATION_QUESTIONS:
            raise RuntimeError(
                "Maximum clarification question limit exceeded."
            )

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

    if question_count < MIN_CLARIFICATION_QUESTIONS:
        raise RuntimeError(
            "Cannot create a review draft before the mandatory "
            f"{MIN_CLARIFICATION_QUESTIONS} clarification questions."
        )

    validation = validation.model_copy(
        update={
            "draft": _merge_missing_details(
                validation.draft,
                validation.missing_details,
            )
        }
    )

    if _has_placeholder_rules(validation.draft.rules):
        raise RuntimeError(
            "The review draft contains generic policy-writing "
            "statements instead of actual business decisions."
        )

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

        # Preserve the review draft and its unresolved items in the
        # validation message. The confirmed version follows the
        # existing downstream contract.
        final_data = dict(draft_data)
        final_data["unresolved_details"] = []

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
        "unresolved_details": [],
    }
