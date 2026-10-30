"""Adapter for standardizing requirement inputs from upstream sources."""

import json
import re
from typing import Any

from app.models.skill_api import ValidatedRequirementInput
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

NUMERIC_PATTERN = re.compile(
    r"""
    (?<![\w.])
    (?:[$€£]\s*)?
    -?
    \d+(?:,\d{3})*(?:\.\d+)?
    \s*
    (?:
        % |
        percent |
        days? |
        hours? |
        weeks? |
        months? |
        years? |
        USD |
        EUR |
        GBP |
        dollars?
    )?
    (?!\w)
    """,
    re.IGNORECASE | re.VERBOSE,
)

APPROVED_STATUSES = {"validated", "confirmed"}
REJECTED_STATUSES = {"rejected", "invalid", "incomplete"}


def extract_numbers_and_units(text_content: str) -> list[str]:
    """Extract numeric values, currencies, percentages, and units."""
    matches = NUMERIC_PATTERN.findall(text_content)
    cleaned = [match.strip() for match in matches if match.strip()]
    return list(dict.fromkeys(cleaned))


def adapt_requirements(
    raw_input: Any,
) -> list[ValidatedRequirementInput]:
    """Adapt supported requirement inputs into validated models."""

    if isinstance(raw_input, list):
        items = raw_input

    elif isinstance(raw_input, dict):
        items = raw_input.get("requirements", [])

    else:
        raise ValueError(
            "Unsupported requirements input type: "
            f"{type(raw_input).__name__}"
        )

    if not isinstance(items, list) or not items:
        raise ValueError(
            "Input must contain a non-empty 'requirements' list."
        )

    adapted: list[ValidatedRequirementInput] = []
    seen_ids: set[str] = set()

    for item in items:
        if isinstance(item, ValidatedRequirementInput):
            model = item

        elif isinstance(item, dict):
            req_id = item.get("requirement_id")
            text_value = item.get("text") or item.get("description")

            if not isinstance(req_id, str) or not req_id.strip():
                raise ValueError(
                    "Every requirement must provide a valid requirement_id."
                )

            if not isinstance(text_value, str) or not text_value.strip():
                raise ValueError(
                    f"Requirement {req_id!r} has empty text."
                )

            status = item.get("status", "validated")

            if status in REJECTED_STATUSES:
                raise ValueError(
                    f"Requirement {req_id!r} has unapproved status: "
                    f"{status!r}."
                )

            numeric_values = (
                item.get("numeric_values")
                or extract_numbers_and_units(text_value)
            )

            model = ValidatedRequirementInput(
                requirement_id=req_id.strip(),
                text=text_value.strip(),
                category=item.get("category") or item.get("topic"),
                conditions=item.get("conditions", []),
                numeric_values=numeric_values,
                source_document=item.get("source_document"),
                source_version_id=item.get("source_version_id"),
                status=status,
                metadata=item.get("metadata", {}),
            )

        else:
            raise ValueError(
                "Expected a dictionary or ValidatedRequirementInput, "
                f"got {type(item).__name__}."
            )

        normalized_id = model.requirement_id.strip()

        if not normalized_id:
            raise ValueError("Requirement ID cannot be blank.")

        if normalized_id in seen_ids:
            raise ValueError(f"Duplicate requirement ID: {normalized_id}")

        seen_ids.add(normalized_id)
        adapted.append(model)

    return adapted


async def load_requirements_from_session(
    session: AsyncSession,
    session_id: str,
) -> tuple[list[ValidatedRequirementInput], str | None, str | None]:
    """Load requirements for a session.

    Returns:
        A tuple containing requirements, domain, and original description.
    """
    session_query = text(
        """
        SELECT session_id, original_description, domain, status
        FROM requirement_sessions
        WHERE session_id = :sid
        """
    )

    session_result = await session.execute(
        session_query,
        {"sid": session_id},
    )
    session_row = session_result.first()

    if session_row is None:
        raise ValueError(
            f"Requirement session {session_id!r} was not found."
        )

    if session_row.status != "confirmed":
        raise ValueError(
            f"Requirement session {session_id!r} is not confirmed."
        )

    domain = session_row.domain
    original_description = session_row.original_description

    requirements_query = text(
        """
        SELECT requirement_id, session_id, topic, description, status
        FROM requirements
        WHERE session_id = :sid
        ORDER BY created_at ASC
        """
    )

    requirements_result = await session.execute(
        requirements_query,
        {"sid": session_id},
    )
    rows = requirements_result.all()

    items: list[dict[str, Any]] = []

    for row in rows:
        requirement_id = str(row.requirement_id or "").strip()
        description = str(row.description or "").strip()

        if not requirement_id or not description:
            continue

        items.append(
            {
                "requirement_id": requirement_id,
                "text": description,
                "category": row.topic or domain,
                "status": row.status or "validated",
            }
        )

    if not items:
        # Fallback to the latest saved requirement snapshot.
        version_query = text(
            """
            SELECT requirements_json
            FROM requirement_versions
            WHERE session_id = :sid
            ORDER BY version_number DESC
            LIMIT 1
            """
        )

        version_result = await session.execute(
            version_query,
            {"sid": session_id},
        )
        version_row = version_result.first()

        if version_row and version_row.requirements_json:
            try:
                parsed = json.loads(version_row.requirements_json)
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError(
                    "The saved requirement snapshot contains invalid JSON."
                ) from exc

            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict):
                items = parsed.get("requirements", [])

    if not items:
        raise ValueError(
            "No requirements found for session "
            f"{session_id!r}."
        )

    adapted = adapt_requirements(items)

    # Do not silently return unapproved requirements.
    unapproved = [
        requirement.requirement_id
        for requirement in adapted
        if requirement.status not in APPROVED_STATUSES
    ]

    if unapproved:
        raise ValueError(
            "Session contains requirements that are not approved: "
            f"{unapproved}"
        )

    return adapted, domain, original_description



async def load_single_requirement(
    session: AsyncSession,
    requirement_id: str,
    session_id: str,
) -> tuple[
    list[ValidatedRequirementInput],
    str | None,
    str | None,
]:
    """Load one approved requirement from its specified session."""

    requirement_id = requirement_id.strip() if requirement_id else ""
    session_id = session_id.strip() if session_id else ""

    if not requirement_id:
        raise ValueError("A valid requirement_id is required.")

    if not session_id:
        raise ValueError("A valid session_id is required.")

    query = text(
        """
        SELECT
            r.requirement_id,
            r.session_id,
            r.topic,
            r.description,
            r.status AS requirement_status,
            s.domain,
            s.original_description,
            s.status AS session_status
        FROM requirements AS r
        JOIN requirement_sessions AS s
            ON s.session_id = r.session_id
        WHERE r.requirement_id = :requirement_id
          AND r.session_id = :session_id
        """
    )

    result = await session.execute(
        query,
        {
            "requirement_id": requirement_id,
            "session_id": session_id,
        },
    )
    row = result.first()

    if row is None:
        raise ValueError(
            "The requirement was not found in the specified session."
        )

    if row.session_status != "confirmed":
        raise ValueError(
            f"Session {session_id!r} is not confirmed. "
            f"Current status: {row.session_status!r}."
        )

    if row.requirement_status not in APPROVED_STATUSES:
        raise ValueError(
            f"Requirement {requirement_id!r} is not approved for "
            f"generation. Current status: {row.requirement_status!r}."
        )

    if not row.description or not row.description.strip():
        raise ValueError(
            f"Requirement {requirement_id!r} has no description."
        )

    requirement = ValidatedRequirementInput(
        requirement_id=str(row.requirement_id),
        text=row.description.strip(),
        category=row.topic,
        numeric_values=extract_numbers_and_units(row.description),
        status=row.requirement_status,
        metadata={"session_id": str(row.session_id)},
    )

    return [requirement], row.domain, row.original_description
