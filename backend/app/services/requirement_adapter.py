"""Load confirmed requirement snapshots and adapt them for generation agents."""

import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_api import ValidatedRequirementInput


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
APPROVED_VERSION_STATUSES = {"valid", "validated", "confirmed"}


def extract_numbers_and_units(text_content: str) -> list[str]:
    """Extract unique numeric values, currencies, percentages, and units."""
    matches = NUMERIC_PATTERN.findall(text_content)
    cleaned = [match.strip() for match in matches if match.strip()]
    return list(dict.fromkeys(cleaned))


def _load_snapshot_items(
    snapshot_json: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse the confirmed snapshot into requirement objects."""
    try:
        payload = (
            json.loads(snapshot_json)
            if isinstance(snapshot_json, str)
            else snapshot_json
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(
            "The confirmed requirement snapshot contains invalid JSON."
        ) from exc

    if isinstance(payload, list):
        raw_items = payload
        shared_fields = {}

    elif isinstance(payload, dict) and isinstance(
        payload.get("requirements"), list
    ):
        raw_items = payload["requirements"]
        shared_fields = {
            key: value
            for key, value in payload.items()
            if key != "requirements"
        }

    elif isinstance(payload, dict):
        raw_items = [payload]
        shared_fields = {}

    else:
        raise ValueError(
            "The confirmed requirement snapshot must be a JSON object or list."
        )

    if not raw_items:
        raise ValueError(
            "The confirmed requirement snapshot contains no requirements."
        )

    if any(not isinstance(item, dict) for item in raw_items):
        raise ValueError(
            "Every requirement in the confirmed snapshot must be a JSON object."
        )

    return raw_items, shared_fields


def _map_snapshot_to_requirement_ids(
    *,
    snapshot_json: Any,
    requirement_rows: list[Any],
    session_id: str,
) -> dict[str, dict[str, Any]]:
    """Map snapshot requirement objects to database requirement IDs."""
    raw_items, shared_fields = _load_snapshot_items(snapshot_json)

    known_ids = {
        str(row["requirement_id"]).strip()
        for row in requirement_rows
        if row["requirement_id"] is not None
        and str(row["requirement_id"]).strip()
    }

    if not known_ids:
        raise ValueError(
            f"Session {session_id!r} has no valid requirement IDs."
        )

    mapped: dict[str, dict[str, Any]] = {}

    for raw_item in raw_items:
        item = dict(shared_fields)
        item.update(raw_item)

        raw_requirement_id = item.get("requirement_id")

        if raw_requirement_id is None or not str(
            raw_requirement_id
        ).strip():
            if len(known_ids) != 1 or len(raw_items) != 1:
                raise ValueError(
                    "The confirmed snapshot does not identify each requirement. "
                    "A requirement_id is required when the session contains "
                    "multiple requirements."
                )

            requirement_id = next(iter(known_ids))
        else:
            requirement_id = str(raw_requirement_id).strip()

        if requirement_id not in known_ids:
            raise ValueError(
                f"Snapshot requirement_id {requirement_id!r} does not exist "
                f"in session {session_id!r}."
            )

        if requirement_id in mapped:
            raise ValueError(
                f"The confirmed snapshot contains duplicate requirement_id "
                f"{requirement_id!r}."
            )

        nested_json = item.get("requirement_json")

        if nested_json is not None:
            if not isinstance(nested_json, dict):
                raise ValueError(
                    f"The requirement_json for {requirement_id!r} "
                    "must be an object."
                )

            requirement_data = dict(nested_json)
        else:
            requirement_data = item

        mapped[requirement_id] = requirement_data

    missing_ids = known_ids - set(mapped)

    if missing_ids:
        raise ValueError(
            "The confirmed snapshot is missing requirement IDs: "
            + ", ".join(sorted(missing_ids))
        )

    return mapped


async def _load_confirmed_snapshot(
    session: AsyncSession,
    session_id: str,
    source_requirement_version_id: str | None = None,
) -> tuple[str, Any]:
    """Load the requested confirmed snapshot or the latest confirmed snapshot."""
    version_id = (
        source_requirement_version_id.strip()
        if isinstance(source_requirement_version_id, str)
        and source_requirement_version_id.strip()
        else None
    )

    if version_id:
        query = text(
            """
            SELECT
                requirement_version_id,
                requirements_json,
                validation_status
            FROM requirement_versions
            WHERE requirement_version_id = :version_id
              AND session_id = :session_id
              AND LOWER(validation_status)
                  IN ('valid', 'validated', 'confirmed')
            """
        )

        parameters = {
            "version_id": version_id,
            "session_id": session_id,
        }

    else:
        query = text(
            """
            SELECT
                requirement_version_id,
                requirements_json,
                validation_status
            FROM requirement_versions
            WHERE session_id = :session_id
              AND LOWER(validation_status)
                  IN ('valid', 'validated', 'confirmed')
            ORDER BY version_number DESC, created_at DESC
            LIMIT 1
            """
        )

        parameters = {"session_id": session_id}

    result = await session.execute(query, parameters)
    version_row = result.mappings().first()

    if version_row is None:
        if version_id:
            raise ValueError(
                f"Requirement version {version_id!r} was not found as a "
                f"confirmed version for session {session_id!r}."
            )

        raise ValueError(
            f"No confirmed requirement snapshot exists for session "
            f"{session_id!r}. Generation requires a confirmed "
            "requirement_versions record."
        )

    requirements_json = version_row["requirements_json"]

    if not requirements_json:
        raise ValueError(
            f"Confirmed requirement version "
            f"{version_row['requirement_version_id']!r} "
            "has no requirements_json."
        )

    return (
        str(version_row["requirement_version_id"]),
        requirements_json,
    )


def _get_domain(requirement_json: dict[str, Any]) -> str | None:
    """Read domain only from the confirmed requirement JSON."""
    domain = requirement_json.get("domain")

    if isinstance(domain, str) and domain.strip():
        return domain.strip()

    return None


def _get_purpose(requirement_json: dict[str, Any]) -> str | None:
    """Read purpose only from the confirmed requirement JSON."""
    purpose = requirement_json.get("purpose")

    if isinstance(purpose, str) and purpose.strip():
        return purpose.strip()

    return None


def _build_requirement_input(
    *,
    requirement_id: str,
    requirement_json: dict[str, Any],
    topic: str | None,
    status: str,
    session_id: str,
    source_version_id: str,
) -> ValidatedRequirementInput:
    """Build agent input using the complete confirmed JSON."""
    requirement_text = json.dumps(
        requirement_json,
        ensure_ascii=False,
        indent=2,
    )

    metadata = {
        "session_id": session_id,
        "requirement_json": requirement_json,
        "source_requirement_version_id": source_version_id,
    }

    return ValidatedRequirementInput(
        requirement_id=requirement_id,
        text=requirement_text,
        category=topic,
        numeric_values=extract_numbers_and_units(requirement_text),
        status=status,
        source_version_id=source_version_id,
        metadata=metadata,
    )


def adapt_requirements(
    raw_input: Any,
) -> list[ValidatedRequirementInput]:
    """Adapt supplied requirement objects while preserving JSON metadata."""
    if isinstance(raw_input, list):
        items = raw_input

    elif isinstance(raw_input, dict):
        items = raw_input.get("requirements", [])

    else:
        raise ValueError(
            f"Unsupported requirements input type: "
            f"{type(raw_input).__name__}"
        )

    if not isinstance(items, list) or not items:
        raise ValueError(
            "Input must contain a non-empty 'requirements' list."
        )

    adapted = []
    seen_ids = set()

    for item in items:
        if isinstance(item, ValidatedRequirementInput):
            model = item

        elif isinstance(item, dict):
            requirement_id = item.get("requirement_id")
            requirement_text = (
                item.get("text") or item.get("description")
            )

            if not isinstance(requirement_id, str) or not requirement_id.strip():
                raise ValueError(
                    "Every requirement must provide a valid requirement_id."
                )

            if (
                not isinstance(requirement_text, str)
                or not requirement_text.strip()
            ):
                raise ValueError(
                    f"Requirement {requirement_id!r} has empty text."
                )

            status = str(
                item.get("status", "validated")
            ).strip().lower()

            if status not in APPROVED_STATUSES:
                raise ValueError(
                    f"Requirement {requirement_id!r} has unapproved "
                    f"status: {status!r}."
                )

            metadata = item.get("metadata") or {}

            if not isinstance(metadata, dict):
                raise ValueError(
                    f"Requirement {requirement_id!r} metadata "
                    "must be an object."
                )

            metadata = dict(metadata)

            requirement_json = (
                item.get("requirement_json")
                or metadata.get("requirement_json")
            )

            if requirement_json is None:
                try:
                    parsed_text = json.loads(requirement_text)
                except (json.JSONDecodeError, TypeError):
                    parsed_text = None

                if isinstance(parsed_text, dict):
                    requirement_json = parsed_text

            if requirement_json is not None:
                if not isinstance(requirement_json, dict):
                    raise ValueError(
                        f"Requirement JSON for {requirement_id!r} "
                        "must be an object."
                    )

                metadata["requirement_json"] = requirement_json

            numeric_values = item.get("numeric_values")

            if numeric_values is None:
                numeric_values = extract_numbers_and_units(
                    requirement_text
                )

            source_version_id = (
                item.get("source_version_id")
                or metadata.get("source_requirement_version_id")
            )

            model = ValidatedRequirementInput(
                requirement_id=requirement_id.strip(),
                text=requirement_text.strip(),
                category=item.get("category") or item.get("topic"),
                conditions=item.get("conditions", []),
                numeric_values=numeric_values,
                source_document=item.get("source_document"),
                source_version_id=source_version_id,
                status=status,
                metadata=metadata,
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
            raise ValueError(
                f"Duplicate requirement ID: {normalized_id}"
            )

        seen_ids.add(normalized_id)
        adapted.append(model)

    return adapted


async def load_requirements_from_session(
    session: AsyncSession,
    session_id: str,
) -> tuple[
    list[ValidatedRequirementInput],
    str | None,
    str | None,
]:
    """Load all requirements from the latest confirmed snapshot.

    Returns:
        adapted requirements,
        domain from confirmed requirement JSON,
        purpose from confirmed requirement JSON.

    Neither original_description nor requirements.description is used.
    """
    session_id = session_id.strip() if session_id else ""

    if not session_id:
        raise ValueError("A valid session_id is required.")

    session_result = await session.execute(
        text(
            """
            SELECT session_id, status
            FROM requirement_sessions
            WHERE session_id = :session_id
            """
        ),
        {"session_id": session_id},
    )

    session_row = session_result.mappings().first()

    if session_row is None:
        raise ValueError(
            f"Requirement session {session_id!r} was not found."
        )

    session_status = str(
        session_row["status"] or ""
    ).strip().lower()

    if session_status != "confirmed":
        raise ValueError(
            f"Requirement session {session_id!r} is not confirmed."
        )

    requirements_result = await session.execute(
        text(
            """
            SELECT requirement_id, topic, status
            FROM requirements
            WHERE session_id = :session_id
            ORDER BY created_at ASC
            """
        ),
        {"session_id": session_id},
    )

    requirement_rows = requirements_result.mappings().all()

    if not requirement_rows:
        raise ValueError(
            f"No requirement records were found for session {session_id!r}."
        )

    for row in requirement_rows:
        requirement_id = str(
            row["requirement_id"] or ""
        ).strip()

        status = str(row["status"] or "").strip().lower()

        if not requirement_id:
            raise ValueError(
                f"A requirement in session {session_id!r} "
                "has no requirement_id."
            )

        if status not in APPROVED_STATUSES:
            raise ValueError(
                f"Requirement {requirement_id!r} is not approved. "
                f"Current status: {row['status']!r}."
            )

    source_version_id, snapshot_json = await _load_confirmed_snapshot(
        session=session,
        session_id=session_id,
    )

    snapshot_by_id = _map_snapshot_to_requirement_ids(
        snapshot_json=snapshot_json,
        requirement_rows=requirement_rows,
        session_id=session_id,
    )

    adapted = []
    domains = []
    purposes = []

    for row in requirement_rows:
        requirement_id = str(row["requirement_id"]).strip()
        requirement_json = snapshot_by_id[requirement_id]

        adapted.append(
            _build_requirement_input(
                requirement_id=requirement_id,
                requirement_json=requirement_json,
                topic=row["topic"],
                status=str(row["status"]).strip().lower(),
                session_id=session_id,
                source_version_id=source_version_id,
            )
        )

        domain = _get_domain(requirement_json)
        purpose = _get_purpose(requirement_json)

        if domain:
            domains.append(domain)

        if purpose:
            purposes.append(purpose)

    unique_domains = list(dict.fromkeys(domains))

    if len(unique_domains) > 1:
        raise ValueError(
            "Conflicting domain values found in the confirmed requirements: "
            + ", ".join(unique_domains)
        )

    single_purpose = (
        purposes[0]
        if len(requirement_rows) == 1 and purposes
        else None
    )

    return (
        adapted,
        unique_domains[0] if unique_domains else None,
        single_purpose,
    )


async def load_single_requirement(
    session: AsyncSession,
    requirement_id: str,
    session_id: str,
    source_requirement_version_id: str | None = None,
) -> tuple[
    list[ValidatedRequirementInput],
    str | None,
    str | None,
]:
    """Load one requirement exclusively from its confirmed version snapshot.

    The requirements table verifies identity, session association, topic,
    and approval status.

    The third return value is the purpose from confirmed requirement JSON.
    It is never the session's original_description.
    """
    requirement_id = requirement_id.strip() if requirement_id else ""
    session_id = session_id.strip() if session_id else ""

    if not requirement_id:
        raise ValueError("A valid requirement_id is required.")

    if not session_id:
        raise ValueError("A valid session_id is required.")

    selected_result = await session.execute(
        text(
            """
            SELECT
                r.requirement_id,
                r.session_id,
                r.topic,
                r.status AS requirement_status,
                s.status AS session_status
            FROM requirements AS r
            JOIN requirement_sessions AS s
                ON s.session_id = r.session_id
            WHERE r.requirement_id = :requirement_id
              AND r.session_id = :session_id
            """
        ),
        {
            "requirement_id": requirement_id,
            "session_id": session_id,
        },
    )

    selected_row = selected_result.mappings().first()

    if selected_row is None:
        raise ValueError(
            "The requirement was not found in the specified session."
        )

    session_status = str(
        selected_row["session_status"] or ""
    ).strip().lower()

    if session_status != "confirmed":
        raise ValueError(
            f"Session {session_id!r} is not confirmed. "
            f"Current status: {selected_row['session_status']!r}."
        )

    requirement_status = str(
        selected_row["requirement_status"] or ""
    ).strip().lower()

    if requirement_status not in APPROVED_STATUSES:
        raise ValueError(
            f"Requirement {requirement_id!r} is not approved for generation. "
            f"Current status: {selected_row['requirement_status']!r}."
        )

    # Read all requirement IDs to avoid guessing when a snapshot has no IDs.
    all_rows_result = await session.execute(
        text(
            """
            SELECT requirement_id, topic, status
            FROM requirements
            WHERE session_id = :session_id
            ORDER BY created_at ASC
            """
        ),
        {"session_id": session_id},
    )

    all_requirement_rows = all_rows_result.mappings().all()

    source_version_id, snapshot_json = await _load_confirmed_snapshot(
        session=session,
        session_id=session_id,
        source_requirement_version_id=source_requirement_version_id,
    )

    snapshot_by_id = _map_snapshot_to_requirement_ids(
        snapshot_json=snapshot_json,
        requirement_rows=all_requirement_rows,
        session_id=session_id,
    )

    requirement_json = snapshot_by_id.get(requirement_id)

    if requirement_json is None:
        raise ValueError(
            f"Requirement {requirement_id!r} was not found in the "
            f"confirmed snapshot for session {session_id!r}."
        )

    requirement = _build_requirement_input(
        requirement_id=requirement_id,
        requirement_json=requirement_json,
        topic=selected_row["topic"],
        status=requirement_status,
        session_id=session_id,
        source_version_id=source_version_id,
    )

    return (
        [requirement],
        _get_domain(requirement_json),
        _get_purpose(requirement_json),
    )