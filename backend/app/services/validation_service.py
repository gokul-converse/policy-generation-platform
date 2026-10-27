from __future__ import annotations

import re
from typing import Any

from app.models.policy_api import (
    PolicySectionModel,
    PolicyValidationReport,
    ValidationFinding,
)
from app.models.skill_api import ValidatedRequirementInput
from app.services.requirement_adapter import extract_numbers_and_units

PLACEHOLDER_PATTERNS = [
    re.compile(r"\[\s*TODO\s*\]", re.IGNORECASE),
    re.compile(r"\[\s*TBD\s*\]", re.IGNORECASE),
    re.compile(r"\[\s*INSERT\b[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[\s*PLACEHOLDER\s*\]", re.IGNORECASE),
]

# Recognizes common explicit numeric replacements, for example:
# "change from 20 days to 25 days", "replace 20 days with 25 days".
_NUMERIC_REPLACEMENT_PATTERNS = [
    re.compile(
        r"\bfrom\s+(?P<old>\d+(?:\.\d+)?)\s*"
        r"(?P<old_unit>days?|weeks?|months?|years?|hours?|minutes?|%|percent)?"
        r"\s+to\s+(?P<new>\d+(?:\.\d+)?)\s*"
        r"(?P<new_unit>days?|weeks?|months?|years?|hours?|minutes?|%|percent)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:change|set|update)\b.{0,50}?"
        r"(?P<old>\d+(?:\.\d+)?)\s*"
        r"(?P<old_unit>days?|weeks?|months?|years?|hours?|minutes?|%|percent)?"
        r"\s+(?:to|into)\s+(?P<new>\d+(?:\.\d+)?)\s*"
        r"(?P<new_unit>days?|weeks?|months?|years?|hours?|minutes?|%|percent)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\breplace\s+(?P<old>\d+(?:\.\d+)?)\s*"
        r"(?P<old_unit>days?|weeks?|months?|years?|hours?|minutes?|%|percent)?"
        r"\s+with\s+(?P<new>\d+(?:\.\d+)?)\s*"
        r"(?P<new_unit>days?|weeks?|months?|years?|hours?|minutes?|%|percent)?\b",
        re.IGNORECASE,
    ),
]


def _normalize_requirement(req: Any) -> tuple[str, str, list[str]] | None:
    """Return requirement ID, source text, and numeric/unit values."""
    if isinstance(req, ValidatedRequirementInput):
        req_id = str(req.requirement_id or "").strip()
        source_text = str(req.text or "").strip()
        numerics = list(req.numeric_values or [])
    elif isinstance(req, dict):
        req_id = str(req.get("requirement_id", "")).strip()
        source_text = str(
            req.get("text") or req.get("requirement_text") or req.get("description") or ""
        ).strip()
        numerics = list(req.get("numeric_values") or [])
    else:
        return None

    if not numerics and source_text:
        numerics = extract_numbers_and_units(source_text)

    return req_id, source_text, [str(value).strip() for value in numerics if str(value).strip()]


def _build_report(
    findings: list[ValidationFinding],
    missing_ids: list[str] | None = None,
    unresolved_items: list[str] | None = None,
    coverage_score: float = 1.0,
) -> PolicyValidationReport:
    """Build the common validation report and calculate overall status."""
    unresolved = list(unresolved_items or [])
    if unresolved and not any(f.rule_name == "unresolved_clarifications" for f in findings):
        findings.append(
            ValidationFinding(
                rule_name="unresolved_clarifications",
                status="NEEDS_CLARIFICATION",
                message="Policy contains unresolved questions or decision gaps.",
                details=unresolved,
            )
        )

    if any(f.status == "FAIL" for f in findings):
        overall_status = "FAIL"
    elif unresolved or any(f.status == "NEEDS_CLARIFICATION" for f in findings):
        overall_status = "NEEDS_CLARIFICATION"
    else:
        overall_status = "PASS"

    return PolicyValidationReport(
        overall_status=overall_status,
        coverage_score=coverage_score,
        missing_requirements=list(missing_ids or []),
        findings=findings,
        clarification_items=unresolved,
    )


def validate_policy_draft(
    sections: list[PolicySectionModel],
    requirements: list[ValidatedRequirementInput] | list[dict[str, Any]],
    unresolved_items: list[str] | None = None,
) -> PolicyValidationReport:
    """Validate structure, traceability, coverage, numeric fidelity and placeholders."""
    findings: list[ValidationFinding] = []
    unresolved = list(unresolved_items or [])

    req_map: dict[str, dict[str, Any]] = {}
    for raw_req in requirements:
        normalized = _normalize_requirement(raw_req)
        if normalized is None:
            continue
        req_id, source_text, numerics = normalized
        if req_id:
            req_map[req_id] = {"text": source_text, "numeric_values": numerics}

    known_req_ids = set(req_map)

    # 1. Section completeness.
    if not sections:
        findings.append(ValidationFinding(
            rule_name="section_completeness", status="FAIL",
            message="Policy contains no sections.",
            details=["At least one policy section is required."],
        ))
    else:
        empty_sections = [
            section.section_id or "<empty ID>"
            for section in sections
            if not str(section.title or "").strip()
            or not str(section.content or "").strip()
        ]
        findings.append(ValidationFinding(
            rule_name="section_completeness",
            status="FAIL" if empty_sections else "PASS",
            message=("One or more policy sections are empty." if empty_sections
                     else "All policy sections have titles and content."),
            details=[f"Empty section: {section_id}" for section_id in empty_sections],
        ))

    # 2. Section IDs must be non-empty and unique.
    ids = [str(section.section_id or "").strip() for section in sections]
    id_issues: list[str] = []
    if any(not section_id for section_id in ids):
        id_issues.append("One or more sections have an empty section_id.")
    seen: set[str] = set()
    duplicates: set[str] = set()
    for section_id in ids:
        if section_id and section_id in seen:
            duplicates.add(section_id)
        seen.add(section_id)
    id_issues.extend(f"Duplicate section ID: {item}" for item in sorted(duplicates))
    findings.append(ValidationFinding(
        rule_name="section_id_validity",
        status="FAIL" if id_issues else "PASS",
        message=("Section IDs must be present and unique." if id_issues
                 else "All section IDs are present and unique."),
        details=id_issues,
    ))

    # 3. Requirement source-ID validity.
    cited_ids = {
        str(requirement_id).strip()
        for section in sections
        for requirement_id in (section.requirement_ids or [])
        if str(requirement_id).strip()
    }
    unauthorized_ids = cited_ids - known_req_ids
    findings.append(ValidationFinding(
        rule_name="source_id_validity",
        status="FAIL" if unauthorized_ids else "PASS",
        message=("Policy references unauthorized or unknown requirement IDs."
                 if unauthorized_ids
                 else "All cited requirement IDs are valid and present in input."),
        details=[f"Unauthorized ID cited: {item}" for item in sorted(unauthorized_ids)],
    ))

    # 4. Coverage means IDs are cited, not that semantic compliance is proven.
    if known_req_ids:
        missing_ids = sorted(known_req_ids - cited_ids)
        coverage = round((len(known_req_ids) - len(missing_ids)) / len(known_req_ids), 4)
    else:
        missing_ids = []
        coverage = 1.0

    findings.append(ValidationFinding(
        rule_name="requirement_coverage",
        status="FAIL" if missing_ids else "PASS",
        message=(f"Requirement coverage is {coverage:.0%}; {len(missing_ids)} requirements are unaddressed."
                 if missing_ids else "100% of validated requirement IDs are cited in policy sections."),
        details=[f"Unaddressed requirement: {item}" for item in missing_ids],
    ))

    full_text = "\n\n".join(f"{section.title}\n{section.content}" for section in sections)

    # 5. Numeric/unit preservation against each requirement's mapped sections.
    numeric_failures: list[str] = []
    for req_id, req_data in req_map.items():
        mapped_content = "\n".join(
            section.content for section in sections if req_id in (section.requirement_ids or [])
        )
        content = mapped_content if mapped_content.strip() else full_text
        for numeric_value in req_data["numeric_values"]:
            if numeric_value.casefold() not in content.casefold():
                numeric_failures.append(
                    f"Requirement {req_id}: source numeric/unit value '{numeric_value}' was not found in mapped policy content."
                )
    findings.append(ValidationFinding(
        rule_name="numeric_preservation",
        status="FAIL" if numeric_failures else "PASS",
        message=("One or more source numeric/unit values are missing."
                 if numeric_failures else "All extracted source numeric/unit values are present in mapped policy content."),
        details=numeric_failures,
    ))

    # 6. Placeholder detection.
    placeholders = [
        match.group(0)
        for pattern in PLACEHOLDER_PATTERNS
        for match in pattern.finditer(full_text)
    ]
    findings.append(ValidationFinding(
        rule_name="placeholder_detection",
        status="FAIL" if placeholders else "PASS",
        message=("Policy draft contains incomplete placeholder tokens."
                 if placeholders else "No configured placeholder tokens were found."),
        details=[f"Found placeholder: {value}" for value in placeholders],
    ))

    return _build_report(findings, missing_ids, unresolved, coverage)



def validate_policy_modification(
    original_section: PolicySectionModel,
    revised_section: PolicySectionModel,
    instructions: str,
    requirements: list[ValidatedRequirementInput] | list[dict[str, Any]],
) -> PolicyValidationReport:
    """Validate a proposed policy modification before version creation."""

    findings: list[ValidationFinding] = []
    instruction = (instructions or "").strip()

    original_content = str(original_section.content or "")
    revised_content = str(revised_section.content or "")

    normalized_revision = re.sub(
        r"\s+", " ", revised_content.casefold()
    )

    # 1. Validate section identity and content.
    identity_issues: list[str] = []

    if revised_section.section_id != original_section.section_id:
        identity_issues.append(
            "The revision changed the section_id."
        )

    if not str(revised_section.title or "").strip():
        identity_issues.append(
            "The revised section has no title."
        )

    if not revised_content.strip():
        identity_issues.append(
            "The revised section has no content."
        )

    findings.append(
        ValidationFinding(
            rule_name="modification_section_identity",
            status="FAIL" if identity_issues else "PASS",
            message=(
                "The revised section identity/content is invalid."
                if identity_issues
                else "The revised section retains a valid identity and content."
            ),
            details=identity_issues,
        )
    )

    # 2. Detect explicit numeric replacement requests.
    replacement = None

    for pattern in _NUMERIC_REPLACEMENT_PATTERNS:
        replacement = pattern.search(instruction)
        if replacement:
            break

    instruction_issues: list[str] = []
    source_conflicts: list[str] = []

    if replacement:
        old_value = replacement.group("old")
        new_value = replacement.group("new")

        old_unit = (
            replacement.groupdict().get("old_unit") or ""
        ).casefold()

        new_unit = (
            replacement.groupdict().get("new_unit") or ""
        ).casefold()

        expected_unit = new_unit or old_unit

        # Build numeric patterns without confusing 25 with 250.
        def value_pattern(value: str, unit: str) -> re.Pattern:
            unit_part = (
                rf"\s+{re.escape(unit)}\b"
                if unit
                else ""
            )
            return re.compile(
                rf"(?<!\d){re.escape(value)}(?![\d.])"
                rf"{unit_part}",
                re.IGNORECASE,
            )

        requested_pattern = value_pattern(
            new_value, expected_unit
        )

        # Check authoritative requirements first.
        for raw_req in requirements:
            normalized = _normalize_requirement(raw_req)

            if normalized is None:
                continue

            req_id, source_text, _ = normalized

            source_text_normalized = re.sub(
                r"\s+", " ", source_text.casefold()
            )

            old_pattern = value_pattern(old_value, old_unit)
            source_new_pattern = value_pattern(
                new_value, expected_unit
            )

            if (
                old_pattern.search(source_text_normalized)
                and not source_new_pattern.search(
                    source_text_normalized
                )
            ):
                old_display = (
                    f"{old_value} {old_unit}".strip()
                )
                new_display = (
                    f"{new_value} {expected_unit}".strip()
                )

                source_conflicts.append(
                    f"Requirement {req_id} specifies "
                    f"'{old_display}', not '{new_display}'. "
                    "Update and validate the authoritative "
                    "requirement before applying this change."
                )

        # Only report the missing replacement when the source
        # requirements do not already explain why it was rejected.
        if (
            not source_conflicts
            and not requested_pattern.search(normalized_revision)
        ):
            requested_display = (
                f"{new_value} {expected_unit}".strip()
            )

            instruction_issues.append(
                f"Requested replacement value '{requested_display}' "
                "is absent from the revised section."
            )

        instruction_issues.extend(source_conflicts)

    findings.append(
        ValidationFinding(
            rule_name="modification_instruction_compliance",
            status="FAIL" if instruction_issues else "PASS",
            message=(
                "The requested modification conflicts with authoritative "
                "requirements or was not applied."
                if instruction_issues
                else "The requested modification passed the deterministic checks."
            ),
            details=instruction_issues,
        )
    )

    # 3. Preserve all existing requirement mappings.
    original_ids = {
        str(item).strip()
        for item in (original_section.requirement_ids or [])
        if str(item).strip()
    }

    revised_ids = {
        str(item).strip()
        for item in (revised_section.requirement_ids or [])
        if str(item).strip()
    }

    mapping_issues: list[str] = []
    removed_ids = original_ids - revised_ids

    if removed_ids:
        mapping_issues.append(
            "The revision removed existing requirement mappings: "
            + ", ".join(sorted(removed_ids))
        )

    findings.append(
        ValidationFinding(
            rule_name="modification_traceability",
            status="FAIL" if mapping_issues else "PASS",
            message=(
                "Requirement mappings were removed."
                if mapping_issues
                else "Existing requirement mappings were preserved."
            ),
            details=mapping_issues,
        )
    )

    return _build_report(findings)
