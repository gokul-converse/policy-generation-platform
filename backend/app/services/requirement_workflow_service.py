
"""Coordinate generic requirement gathering, validation, and confirmation."""

import json
import re
import logging
from time import perf_counter
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
from app.agents.requirement.requirement_gathering_agent import (
    gather_requirements,
)
from app.agents.requirement.requirement_validation_agent import (
    validate_requirements,
)
from app.schemas.requirements import (
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


MIN_CLARIFICATION_QUESTIONS = 3
MAX_CLARIFICATION_QUESTIONS = 5

logger = logging.getLogger(__name__)


def _normalize_question(question: str) -> str:
    """Normalize question text for generic duplicate detection."""
    return re.sub(r"\W+", " ", question.casefold()).strip()


async def _get_clarification_history(
    session_id: str,
) -> tuple[int, list[str], list[dict]]:
    """Return previous clarification questions and their answers."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ClarificationItem)
            .where(ClarificationItem.session_id == session_id)
            .order_by(
                ClarificationItem.created_at.asc(),
                ClarificationItem.clarification_id.asc(),
            )
        )
        items = result.scalars().all()

        history = [
            {
                "question": item.question,
                "answer": item.answer,
                "status": item.status,
                "requirement_id": item.requirement_id,
            }
            for item in items
        ]

    questions = [
        item["question"]
        for item in history
        if item["question"] and item["question"].strip()
    ]

    return (
        len(questions),
        [_normalize_question(question) for question in questions],
        history,
    )


def _build_review_draft(
    requirements: RequirementDetails,
    missing_details: list[str],
) -> RequirementDetails:
    """Build a draft without hiding unresolved details."""
    draft = requirements.model_copy(deep=True)
    existing = list(draft.unresolved_details)
    seen = {item.casefold() for item in existing}

    for detail in missing_details:
        detail = detail.strip()
        if detail and detail.casefold() not in seen:
            existing.append(detail)
            seen.add(detail.casefold())

    draft.unresolved_details = existing
    return draft


def _get_requirement_metadata(
    details: RequirementDetails | dict,
) -> tuple[str, str]:
    """Return a meaningful topic and a readable, non-JSON description."""
    data = (
        details.model_dump()
        if isinstance(details, RequirementDetails)
        else details
    )

    policy_name = data.get("policy_name")
    purpose = data.get("purpose")
    scope = data.get("scope")

    policy_name = policy_name.strip() if isinstance(policy_name, str) else ""
    purpose = purpose.strip() if isinstance(purpose, str) else ""
    scope = scope.strip() if isinstance(scope, str) else ""

    # Prefer the explicit policy name; otherwise derive a readable topic
    # from the purpose instead of saving the generic word "Requirement".
    if policy_name:
        topic = policy_name[:150]
    elif purpose:
        topic = purpose.split(".")[0].strip()[:150] or "Untitled Requirement"
    else:
        topic = "Untitled Requirement"

    # Keep this field human-readable. The complete structured snapshot belongs
    # in RequirementVersion.requirements_json.
    description = purpose or scope or f"Requirements for {topic}."
    return topic, description


async def _upsert_requirement(
    session_id: str,
    details: RequirementDetails,
    status: str,
) -> str:
    """Create or update the session's single requirement record."""
    allowed_statuses = {
        "extracted",
        "needs_clarification",
        "validated",
    }
    if status not in allowed_statuses:
        raise ValueError(f"Unsupported pre-confirmation status: {status}")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Requirement)
            .where(Requirement.session_id == session_id)
            .order_by(Requirement.requirement_id.asc())
            .limit(1)
        )
        requirement = result.scalar_one_or_none()

        topic, description = _get_requirement_metadata(details)

        if requirement is None:
            requirement = Requirement(
                requirement_id=str(uuid4()),
                session_id=session_id,
                topic=topic,
                description=description,
                status=status,
            )
            db.add(requirement)
        else:
            requirement.topic = topic
            requirement.description = description
            requirement.status = status

        await db.commit()
        await db.refresh(requirement)
        return requirement.requirement_id


async def _save_clarification(
    session_id: str,
    requirement_id: str,
    question: str,
) -> None:
    """Save a new question linked to the existing requirement."""
    normalized = _normalize_question(question)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ClarificationItem).where(
                ClarificationItem.session_id == session_id
            )
        )
        previous_items = result.scalars().all()

        if any(
            _normalize_question(item.question) == normalized
            for item in previous_items
        ):
            raise ValueError("Duplicate clarification question prevented.")

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


async def process_requirement_message(
    request: RequirementInput,
) -> dict:
    """Process a start, answer, confirm, or cancel event."""
    message = request.message.strip()

    if not message:
        raise ValueError("Message cannot be empty.")

    if request.event == "start":
        if request.session_id:
            raise ValueError(
                "A new start event must not contain a session_id."
            )
        session = await create_or_get_session(message)
    else:
        if not request.session_id:
            raise ValueError("session_id is required for this event.")
        session = await create_or_get_session(
            description=message,
            session_id=request.session_id,
        )

    session_id = session.session_id

    if request.event == "cancel":
        await save_message(
            session_id,
            "user",
            message,
            message_type="message",
        )
        await update_session_status(session_id, "cancelled")
        return {
            "event": "conversation_cancelled",
            "session_id": session_id,
            "message": "Requirement gathering was cancelled.",
        }

    if request.event == "confirm":
        return await _confirm_requirement(session_id, message)

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

    if request.event == "answer":
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
            clarification = result.scalar_one_or_none()

            if clarification is not None:
                clarification.answer = message
                clarification.status = "answered"
                clarification.answered_at = func.current_timestamp()
                await db.commit()

    question_count, normalized_questions, clarification_history = (
        await _get_clarification_history(session_id)
    )

    conversation = await get_conversation_history(session_id)

    # Explicitly provide structured history, not just raw chat messages.
    agent_context = (
        f"{conversation}\n\n"
        "STRUCTURED CLARIFICATION HISTORY:\n"
        f"{json.dumps(clarification_history, ensure_ascii=False, indent=2)}\n\n"
        f"Questions already asked: {question_count}\n"
        f"Maximum allowed questions: {MAX_CLARIFICATION_QUESTIONS}\n"
        "Use the complete history. Do not repeat previously asked topics. "
        "If a previous topic remains unresolved, record it in the draft "
        "instead of asking about that topic again."
    )

    await update_session_status(session_id, "gathering")

    gathering_started = perf_counter()
    gathered = await gather_requirements(
        description=session.original_description,
        conversation_history=agent_context,
    )
    logger.info(
        "requirement_gathering_agent took %.2f seconds for session %s",
        perf_counter() - gathering_started,
        session_id,
    )

    requirement_id = await _upsert_requirement(
        session_id=session_id,
        details=gathered.requirements,
        status="needs_clarification",
    )

    await update_session_status(
        session_id,
        "validating",
        domain=gathered.requirements.domain,
    )

    validation_started = perf_counter()
    validation = await validate_requirements(
        gathered=gathered,
        conversation_history=agent_context,
    )
    logger.info(
        "requirement_validation_agent took %.2f seconds for session %s",
        perf_counter() - validation_started,
        session_id,
    )

    question_count, normalized_questions, clarification_history = (
        await _get_clarification_history(session_id)
    )

    proposed_question = (validation.question or "").strip()
    duplicate_question = (
        bool(proposed_question)
        and _normalize_question(proposed_question) in normalized_questions
    )
    limit_reached = question_count >= MAX_CLARIFICATION_QUESTIONS

    # The backend enforces the hard cap even if the model ignores the prompt.
    # Exact duplicate text also falls back to a review draft.
    if validation.status == "needs_clarification" and (
        duplicate_question or limit_reached
    ):
        unresolved = list(validation.missing_details)

        if duplicate_question:
            unresolved.append(
                "A previously asked question was proposed again. "
                "Review the remaining uncertainty in the draft."
            )

        if limit_reached:
            unresolved.append(
                "The clarification limit was reached; remaining details "
                "are listed for review."
            )

        validation = ValidationResult(
            status="ready_for_confirmation",
            missing_details=unresolved,
            question=None,
            draft=_build_review_draft(
                gathered.requirements,
                unresolved,
            ),
            explanation=(
                "The maximum clarification count was reached."
                if limit_reached
                else
                "A duplicate question was prevented. "
                "The draft contains unresolved details for review."
            ),
        )

    await save_message(
        session_id,
        "agent",
        validation.model_dump_json(),
        message_type=(
            "clarification_question"
            if validation.status == "needs_clarification"
            else "status_update"
        ),
        agent_name="requirement_validation_agent",
    )

    if validation.status == "needs_clarification":
        question = (validation.question or "").strip()

        if not question:
            raise ValueError(
                "Validation requires clarification but returned no question."
            )

        current_count, current_normalized_questions, _ = (
            await _get_clarification_history(session_id)
        )

        if current_count >= MAX_CLARIFICATION_QUESTIONS:
            raise ValueError("Clarification question limit reached.")

        if _normalize_question(question) in current_normalized_questions:
            raise ValueError("Duplicate clarification question prevented.")

        await _save_clarification(
            session_id=session_id,
            requirement_id=requirement_id,
            question=question,
        )

        await update_session_status(
            session_id,
            "awaiting_clarification",
        )

        return {
            "event": "clarification_question",
            "session_id": session_id,
            "requirement_id": requirement_id,
            "question": question,
            "question_number": current_count + 1,
            "minimum_questions": MIN_CLARIFICATION_QUESTIONS,
            "maximum_questions": MAX_CLARIFICATION_QUESTIONS,
            "missing_details": validation.missing_details,
        }

    if validation.draft is None:
        raise ValueError(
            "Validation returned no draft for confirmation."
        )

    await _upsert_requirement(
        session_id=session_id,
        details=validation.draft,
        status="validated",
    )

    await update_session_status(
        session_id,
        "ready_for_confirmation",
        domain=validation.draft.domain,
    )

    return {
        "event": "requirement_draft",
        "session_id": session_id,
        "requirement_id": requirement_id,
        "draft": validation.draft.model_dump(),
        "explanation": validation.explanation,
        "questions_asked": question_count,
        "minimum_questions": MIN_CLARIFICATION_QUESTIONS,
        "maximum_questions": MAX_CLARIFICATION_QUESTIONS,
        "unresolved_details": validation.draft.unresolved_details,
        "requires_confirmation": True,
    }


async def _confirm_requirement(
    session_id: str,
    confirmation_message: str,
) -> dict:
    """Persist a confirmed draft and create a version."""
    if confirmation_message.casefold().strip() not in {
        "yes",
        "confirm",
        "confirmed",
        "i confirm",
    }:
        raise ValueError(
            "Send an explicit confirmation message to finalize."
        )

    async with AsyncSessionLocal() as db:
        session = await db.get(RequirementSession, session_id)

        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        if session.status != "ready_for_confirmation":
            raise ValueError(
                "The session has no draft ready for confirmation."
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
        latest_message = result.scalar_one_or_none()

        if latest_message is None:
            raise ValueError("No requirement draft was found.")

        validation = json.loads(latest_message.content)
        draft = validation.get("draft")

        if (
            validation.get("status") != "ready_for_confirmation"
            or not isinstance(draft, dict)
        ):
            raise ValueError(
                "The latest validation result is not a draft."
            )

        policy_name = draft.get("policy_name")
        if not isinstance(policy_name, str) or not policy_name.strip():
            raise ValueError(
                "Cannot confirm requirements without a policy name. "
                "Please provide or generate a meaningful policy name first."
            )

        version_result = await db.execute(
            select(func.max(RequirementVersion.version_number))
            .where(RequirementVersion.session_id == session_id)
        )
        latest_version = version_result.scalar_one() or 0

        version_id = str(uuid4())

        db.add(
            RequirementVersion(
                requirement_version_id=version_id,
                session_id=session_id,
                version_number=latest_version + 1,
                requirements_json=json.dumps(
                    draft,
                    ensure_ascii=False,
                ),
                validation_status="confirmed",
            )
        )

        requirement_result = await db.execute(
            select(Requirement)
            .where(Requirement.session_id == session_id)
            .order_by(Requirement.requirement_id.asc())
            .limit(1)
        )
        requirement = requirement_result.scalar_one_or_none()

        topic, description = _get_requirement_metadata(draft)

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
        session.domain = draft.get("domain", "general")

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
        "version_number": latest_version + 1,
        "message": "Requirements confirmed and saved.",
    }
