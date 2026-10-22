"""Adapter for standardizing requirement inputs from various upstream sources."""

import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requirements import RequirementAnalysis
from app.models.skill_api import ValidatedRequirementInput

NUMERIC_PATTERN = re.compile(
    r"(?:[\$€£])?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:days?|hours?|weeks?|months?|years?|percent|%|USD|EUR|GBP|dollars?))?",
    re.IGNORECASE,
)


def extract_numbers_and_units(text_content: str) -> list[str]:
    """Extract numeric values, currencies, percentages, and units from text."""
    matches = NUMERIC_PATTERN.findall(text_content)
    cleaned = [m.strip() for m in matches if m.strip()]
    return list(dict.fromkeys(cleaned))


def adapt_requirements(raw_input: Any) -> list[ValidatedRequirementInput]:
    """Adapt requirements from diverse inputs into a validated, normalized list."""
    if isinstance(raw_input, list):
        items = raw_input
    elif isinstance(raw_input, dict):
        items = raw_input.get("requirements", [])
    elif isinstance(raw_input, RequirementAnalysis):
        # Convert teammate's RequirementAnalysis into structured ValidatedRequirementInput
        result = []
        for index, req_text in enumerate(raw_input.requirements, start=1):
            if not req_text or not req_text.strip():
                continue
            req_id = f"REQ-{index:03d}"
            nums = extract_numbers_and_units(req_text)
            result.append(
                ValidatedRequirementInput(
                    requirement_id=req_id,
                    text=req_text.strip(),
                    category=(
                        raw_input.identified_domains[0]
                        if raw_input.identified_domains
                        else None
                    ),
                    numeric_values=nums,
                    status="validated",
                )
            )
        if not result:
            raise ValueError("RequirementAnalysis contained no valid requirements.")
        return result
    else:
        raise ValueError(f"Unsupported requirements input type: {type(raw_input).__name__}")

    if not items:
        raise ValueError("Input must contain a non-empty 'requirements' list.")

    adapted: list[ValidatedRequirementInput] = []
    seen_ids: set[str] = set()

    for item in items:
        if isinstance(item, ValidatedRequirementInput):
            model = item
        elif isinstance(item, dict):
            req_id = item.get("requirement_id")
            text_val = item.get("text") or item.get("description")
            if not req_id or not str(req_id).strip():
                raise ValueError("Every requirement must provide a valid requirement_id.")
            if not text_val or not str(text_val).strip():
                raise ValueError(f"Requirement {req_id!r} has empty text.")

            status = item.get("status", "validated")
            if status in ("rejected", "invalid", "incomplete"):
                raise ValueError(
                    f"Requirement {req_id!r} has unapproved status: {status!r}."
                )

            nums = item.get("numeric_values") or extract_numbers_and_units(text_val)
            model = ValidatedRequirementInput(
                requirement_id=str(req_id).strip(),
                text=str(text_val).strip(),
                category=item.get("category") or item.get("topic"),
                conditions=item.get("conditions", []),
                numeric_values=nums,
                source_document=item.get("source_document"),
                source_version_id=item.get("source_version_id"),
                status=status,
                metadata=item.get("metadata", {}),
            )
        else:
            raise ValueError(f"Expected dictionary or ValidatedRequirementInput, got {type(item).__name__}")

        if model.requirement_id in seen_ids:
            raise ValueError(f"Duplicate requirement ID: {model.requirement_id}")

        seen_ids.add(model.requirement_id)
        adapted.append(model)

    return adapted


async def load_requirements_from_session(
    session: AsyncSession,
    session_id: str,
) -> tuple[list[ValidatedRequirementInput], str | None, str | None]:
    """Query conversational requirement gathering tables for requirements belonging to session_id.

    Returns:
        tuple of (requirements_list, domain, original_description)
    """

    # 1. Fetch session metadata from requirement_sessions
    sess_query = text(
        "SELECT session_id, original_description, domain, status "
        "FROM requirement_sessions WHERE session_id = :sid"
    )
    sess_res = await session.execute(sess_query, {"sid": session_id})
    sess_row = sess_res.first()

    domain = sess_row.domain if sess_row else None
    original_description = sess_row.original_description if sess_row else None

    # 2. Query requirements table
    req_query = text(
        "SELECT requirement_id, session_id, topic, description, status "
        "FROM requirements WHERE session_id = :sid ORDER BY created_at ASC"
    )
    req_res = await session.execute(req_query, {"sid": session_id})
    rows = req_res.all()

    items = []
    if rows:
        for r in rows:
            req_id = str(r.requirement_id).strip()
            text_val = str(r.description).strip()
            if not req_id or not text_val:
                continue
            items.append({
                "requirement_id": req_id,
                "text": text_val,
                "category": r.topic or domain,
                "status": r.status or "validated",
                "source_version_id": session_id,
            })
    else:
        # Fallback: check requirement_versions table for requirements_json
        ver_query = text(
            "SELECT requirements_json FROM requirement_versions "
            "WHERE session_id = :sid ORDER BY version_number DESC LIMIT 1"
        )
        ver_res = await session.execute(ver_query, {"sid": session_id})
        ver_row = ver_res.first()
        if ver_row and ver_row.requirements_json:
            parsed = json.loads(ver_row.requirements_json)
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict) and "requirements" in parsed:
                items = parsed["requirements"]

    if not items:
        raise ValueError(
            f"No validated requirements found in database for session_id '{session_id}'."
        )

    adapted = adapt_requirements(items)
    return adapted, domain, original_description


async def load_single_requirement(
    session: AsyncSession,
    requirement_id: str,
) -> tuple[list[ValidatedRequirementInput], str | None, str | None]:
    """Load one approved requirement using its ID."""

    query = text(
        """
        SELECT
            r.requirement_id,
            r.session_id,
            r.topic,
            r.description,
            r.status,
            s.domain,
            s.original_description
        FROM requirements AS r
        JOIN requirement_sessions AS s
            ON s.session_id = r.session_id
        WHERE r.requirement_id = :requirement_id
        """
    )

    result = await session.execute(
        query,
        {"requirement_id": requirement_id},
    )
    row = result.first()

    if row is None:
        raise ValueError(
            f"Requirement '{requirement_id}' was not found."
        )

    if row.status not in {"validated", "confirmed"}:
        raise ValueError(
            f"Requirement '{requirement_id}' is not approved for generation. "
            f"Current status: '{row.status}'."
        )

    requirement = ValidatedRequirementInput(
        requirement_id=row.requirement_id,
        text=row.description,
        session_id=row.session_id,
        category=row.topic or row.domain,
        numeric_values=extract_numbers_and_units(row.description),
        status=row.status,
    )

    return (
        [requirement],
        row.domain,
        row.original_description,
    )