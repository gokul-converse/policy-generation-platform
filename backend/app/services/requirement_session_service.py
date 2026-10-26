
"""Session and conversation persistence for requirement gathering."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.requirement_db import (
    ConversationMessage,
    RequirementSession,
)


async def create_or_get_session(
    description: str,
    session_id: str | None = None,
) -> RequirementSession:
    """Create a new session or retrieve an existing session."""

    async with AsyncSessionLocal() as db:
        if session_id:
            session = await db.get(RequirementSession, session_id)

            if session is None:
                raise ValueError(f"Session not found: {session_id}")

            if session.status in ("confirmed", "cancelled"):
                raise ValueError(
                    f"Cannot continue a {session.status} session."
                )

            return session

        session = RequirementSession(
            session_id=str(uuid4()),
            original_description=description,
            domain="general",
            status="gathering",
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session


async def save_message(
    session_id: str,
    sender_type: str,
    content: str,
    message_type: str = "message",
    agent_name: str | None = None,
) -> None:
    """Save one user, agent, or system message."""

    async with AsyncSessionLocal() as db:
        session = await db.get(RequirementSession, session_id)

        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        message = ConversationMessage(
            message_id=str(uuid4()),
            session_id=session_id,
            sender_type=sender_type,
            agent_name=agent_name,
            message_type=message_type,
            content=content,
        )

        db.add(message)
        session.updated_at = datetime.now(timezone.utc).isoformat()

        await db.commit()


async def get_conversation_history(session_id: str) -> str:
    """Return the session's conversation as readable text."""

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(
                ConversationMessage.created_at,
                ConversationMessage.message_id,
            )
        )

        messages = result.scalars().all()

        return "\n".join(
            f"{message.sender_type}: {message.content}"
            for message in messages
        )


async def update_session_status(
    session_id: str,
    status: str,
    domain: str | None = None,
) -> None:
    """Update session status and optionally its policy domain."""

    allowed_statuses = {
        "gathering",
        "awaiting_clarification",
        "validating",
        "ready_for_confirmation",
        "confirmed",
        "cancelled",
    }

    if status not in allowed_statuses:
        raise ValueError(f"Invalid session status: {status}")

    async with AsyncSessionLocal() as db:
        session = await db.get(RequirementSession, session_id)

        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        if session.status in ("confirmed", "cancelled"):
            raise ValueError(
                f"Cannot update a {session.status} session."
            )

        session.status = status

        if domain is not None:
            allowed_domains = {
                "hr",
                "finance",
                "it_security",
                "general",
            }

            if domain not in allowed_domains:
                raise ValueError(f"Invalid policy domain: {domain}")

            session.domain = domain

        session.updated_at = datetime.now(timezone.utc).isoformat()

        await db.commit()
