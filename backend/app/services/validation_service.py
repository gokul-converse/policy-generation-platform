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
    """Validate a proposed policy modification before creating a version."""

    findings: list[ValidationFinding] = []

    instruction = (instructions or "").strip()
    original_content = str(original_section.content or "")
    revised_content = str(revised_section.content or "")

    def normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", value.casefold()).strip()

    def add_finding(
        rule_name: str,
        passed: bool,
        success_message: str,
        failure_message: str,
        details: list[str] | None = None,
    ) -> None:
        findings.append(
            ValidationFinding(
                rule_name=rule_name,
                status="PASS" if passed else "FAIL",
                message=success_message if passed else failure_message,
                details=details or [],
            )
        )

    # --------------------------------------------------
    # 1. Section identity and content
    # --------------------------------------------------
    identity_issues: list[str] = []

    if revised_section.section_id != original_section.section_id:
        identity_issues.append("The section_id was changed.")

    if not str(revised_section.title or "").strip():
        identity_issues.append("The revised section has no title.")

    if not revised_content.strip():
        identity_issues.append("The revised section has no content.")

    add_finding(
        rule_name="modification_section_identity",
        passed=not identity_issues,
        success_message="The revised section retains a valid identity and content.",
        failure_message="The revised section identity or content is invalid.",
        details=identity_issues,
    )

    # --------------------------------------------------
    # 2. Detect whether content changed
    # --------------------------------------------------
    content_changed = (
        normalize_text(original_content)
        != normalize_text(revised_content)
    )

    add_finding(
        rule_name="modification_content_changed",
        passed=content_changed,
        success_message="The policy section content was modified.",
        failure_message="The policy content was not modified.",
        details=(
            []
            if content_changed
            else [
                "The revision agent returned unchanged policy content. "
                "The requested modification was not applied."
            ]
        ),
    )

    # --------------------------------------------------
    # 3. Normalize authoritative requirements
    # --------------------------------------------------
    normalized_requirements = []

    for raw_requirement in requirements:
        normalized = _normalize_requirement(raw_requirement)

        if normalized is None:
            continue

        req_id, source_text, numeric_values = normalized

        if req_id and source_text:
            normalized_requirements.append(
                {
                    "requirement_id": req_id,
                    "text": source_text,
                    "numeric_values": numeric_values,
                }
            )

    # --------------------------------------------------
    # 4. Detect explicit numeric replacement requests
    # --------------------------------------------------
    number_words = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "eleven": "11",
        "twelve": "12",
        "thirteen": "13",
        "fourteen": "14",
        "fifteen": "15",
        "sixteen": "16",
        "seventeen": "17",
        "eighteen": "18",
        "nineteen": "19",
        "twenty": "20",
    }

    number_pattern = (
        r"(?:\d+(?:\.\d+)?|"
        + "|".join(number_words.keys())
        + r")"
    )

    unit_pattern = (
        r"days?|weeks?|months?|years?|hours?|minutes?|"
        r"business\s+days?|%"
    )

    replacement_patterns = [
        re.compile(
            rf"\bfrom\s+(?P<old>{number_pattern})\s+"
            rf"(?P<old_unit>{unit_pattern})\s+"
            rf"to\s+(?P<new>{number_pattern})\s+"
            rf"(?P<new_unit>{unit_pattern})\b",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\b(?:change|set|update)\b.{{0,100}}?"
            rf"(?P<old>{number_pattern})\s+"
            rf"(?P<old_unit>{unit_pattern})\s+"
            rf"(?:to|into)\s+"
            rf"(?P<new>{number_pattern})\s+"
            rf"(?P<new_unit>{unit_pattern})\b",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\breplace\s+(?P<old>{number_pattern})\s+"
            rf"(?P<old_unit>{unit_pattern})\s+with\s+"
            rf"(?P<new>{number_pattern})\s+"
            rf"(?P<new_unit>{unit_pattern})\b",
            re.IGNORECASE,
        ),
    ]

    def normalize_number(value: str) -> str:
        value = value.casefold().strip()
        return number_words.get(value, value)

    def normalize_unit(value: str) -> str:
        value = re.sub(r"\s+", " ", value.casefold().strip())

        aliases = {
            "day": "days",
            "business day": "business days",
            "week": "weeks",
            "month": "months",
            "year": "years",
            "hour": "hours",
            "minute": "minutes",
        }

        return aliases.get(value, value)

    replacement = None

    for pattern in replacement_patterns:
        replacement = pattern.search(instruction)
        if replacement:
            break

    instruction_issues: list[str] = []
    source_conflicts: list[str] = []

    if replacement:
        old_value = normalize_number(replacement.group("old"))
        new_value = normalize_number(replacement.group("new"))

        old_unit = normalize_unit(replacement.group("old_unit"))
        new_unit = normalize_unit(replacement.group("new_unit"))

        if old_unit != new_unit:
            instruction_issues.append(
                "The requested numeric replacement uses different units. "
                "The requested change requires clarification."
            )

        def contains_value(
            text: str,
            value: str,
            unit: str,
        ) -> bool:
            pattern = re.compile(
                rf"(?<!\d){re.escape(value)}(?!\d)"
                rf"\s+{re.escape(unit)}\b",
                re.IGNORECASE,
            )
            return bool(pattern.search(text))

        # Check authoritative source requirements.
        for requirement in normalized_requirements:
            source_text = normalize_text(requirement["text"])
            req_id = requirement["requirement_id"]

            old_exists = contains_value(
                source_text,
                old_value,
                old_unit,
            )

            new_exists = contains_value(
                source_text,
                new_value,
                new_unit,
            )

            if old_exists and not new_exists:
                source_conflicts.append(
                    f"Requirement {req_id} specifies "
                    f"'{old_value} {old_unit}', not "
                    f"'{new_value} {new_unit}'. "
                    "Update and validate the authoritative "
                    "requirement before applying this change."
                )

        # The requested value must appear in the revised section.
        requested_value_present = contains_value(
            normalize_text(revised_content),
            new_value,
            new_unit,
        )

        if not requested_value_present and not source_conflicts:
            instruction_issues.append(
                f"The requested replacement value "
                f"'{new_value} {new_unit}' is absent from "
                "the revised section."
            )

    # --------------------------------------------------
    # 5. Instruction compliance and source compliance
    # --------------------------------------------------
    instruction_issues.extend(source_conflicts)

    add_finding(
        rule_name="modification_instruction_compliance",
        passed=not instruction_issues,
        success_message="The requested modification passed deterministic checks.",
        failure_message="The requested modification was not applied or conflicts with its source.",
        details=instruction_issues,
    )

    add_finding(
        rule_name="modification_requirement_compliance",
        passed=not source_conflicts,
        success_message="The requested change is consistent with authoritative requirements.",
        failure_message="The requested change conflicts with authoritative requirements.",
        details=source_conflicts,
    )

    # --------------------------------------------------
    # 6. Preserve requirement mappings
    # --------------------------------------------------
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
    added_ids = revised_ids - original_ids

    if removed_ids:
        mapping_issues.append(
            "Existing requirement mappings were removed: "
            + ", ".join(sorted(removed_ids))
        )

    if added_ids:
        mapping_issues.append(
            "Unsupported requirement mappings were added: "
            + ", ".join(sorted(added_ids))
        )

    add_finding(
        rule_name="modification_traceability",
        passed=not mapping_issues,
        success_message="Existing requirement mappings were preserved.",
        failure_message="Requirement mappings were changed.",
        details=mapping_issues,
    )

    # --------------------------------------------------
    # 7. Build final report
    # --------------------------------------------------
    return _build_report(findings)




def merge_policy_validation_reports(
    deterministic_report: PolicyValidationReport,
    semantic_report: Any,
    total_requirements: int | None = None,
) -> PolicyValidationReport:
    """
    Merge deterministic and semantic validation reports.

    Deterministic validation checks structure, IDs, coverage,
    numeric preservation, and placeholders.

    Semantic validation checks actual meaning, compliance,
    unsupported additions, and contradictions.
    """

    # --------------------------------------------------
    # 1. Merge findings
    # --------------------------------------------------

    combined_findings = [
        *deterministic_report.findings,
        *semantic_report.findings,
    ]

    # --------------------------------------------------
    # 2. Merge missing requirement IDs
    # --------------------------------------------------

    missing_requirements = list(
        dict.fromkeys(
            [
                *deterministic_report.missing_requirements,
                *semantic_report.missing_requirements,
            ]
        )
    )

    # --------------------------------------------------
    # 3. Merge clarification items
    # --------------------------------------------------

    clarification_items = list(
        dict.fromkeys(
            [
                *deterministic_report.clarification_items,
                *semantic_report.clarification_items,
            ]
        )
    )

    # --------------------------------------------------
    # 4. Calculate combined coverage
    # --------------------------------------------------

    if total_requirements is not None and total_requirements > 0:
        missing_count = min(
            len(missing_requirements),
            total_requirements,
        )

        coverage_score = round(
            (total_requirements - missing_count)
            / total_requirements,
            4,
        )
    else:
        coverage_score = deterministic_report.coverage_score

    # --------------------------------------------------
    # 5. Determine final validation status
    # --------------------------------------------------

    all_statuses = [
        deterministic_report.overall_status,
        semantic_report.overall_status,
    ]

    if "FAIL" in all_statuses:
        overall_status = "FAIL"

    elif (
        "NEEDS_CLARIFICATION" in all_statuses
        or clarification_items
    ):
        overall_status = "NEEDS_CLARIFICATION"

    else:
        overall_status = "PASS"

    # --------------------------------------------------
    # 6. Return the unified report
    # --------------------------------------------------

    return PolicyValidationReport(
        overall_status=overall_status,
        coverage_score=coverage_score,
        missing_requirements=missing_requirements,
        findings=combined_findings,
        clarification_items=clarification_items,
    )
