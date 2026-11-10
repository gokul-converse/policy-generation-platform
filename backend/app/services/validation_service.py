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


def _normalize_requirement(
    req: Any,
) -> tuple[str, str, list[str]]:
    """
    Normalize one authoritative requirement.

    Returns:
        requirement_id, source_text, numeric_values

    Raises:
        ValueError: If the requirement is malformed.
    """

    if isinstance(req, ValidatedRequirementInput):
        req_id = str(req.requirement_id or "").strip()
        source_text = str(req.text or "").strip()
        numerics = list(req.numeric_values or [])

    elif isinstance(req, dict):
        req_id = str(req.get("requirement_id") or "").strip()

        source_text = str(
            req.get("text")
            or req.get("requirement_text")
            or req.get("description")
            or ""
        ).strip()

        numerics = list(req.get("numeric_values") or [])

    else:
        raise ValueError(
            f"Unsupported requirement input type: {type(req).__name__}"
        )

    if not req_id:
        raise ValueError(
            "Every authoritative requirement must have a requirement_id."
        )

    if not source_text:
        raise ValueError(
            f"Requirement {req_id!r} has empty source text."
        )

    if not numerics:
        numerics = extract_numbers_and_units(source_text)

    normalized_numerics = [
        str(value).strip()
        for value in numerics
        if str(value).strip()
    ]

    return req_id, source_text, normalized_numerics


def _normalize_requirements(
    requirements: list[
        ValidatedRequirementInput | dict[str, Any]
    ],
) -> dict[str, dict[str, Any]]:
    """
    Normalize all authoritative requirements.

    Requirement IDs must be present and unique.
    Invalid requirements are rejected instead of silently skipped.
    """

    if not requirements:
        raise ValueError(
            "At least one authoritative validated requirement is required."
        )

    req_map: dict[str, dict[str, Any]] = {}

    for index, raw_requirement in enumerate(requirements, start=1):
        try:
            normalized = _normalize_requirement(raw_requirement)

        except ValueError as exc:
            raise ValueError(
                f"Invalid requirement at position {index}: {exc}"
            ) from exc

        req_id, source_text, numerics = normalized

        if req_id in req_map:
            raise ValueError(
                f"Duplicate authoritative requirement ID: {req_id}"
            )

        req_map[req_id] = {
            "text": source_text,
            "numeric_values": numerics,
        }

    return req_map


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
    requirements: list[
        ValidatedRequirementInput | dict[str, Any]
    ],
    unresolved_items: list[str] | None = None,
) -> PolicyValidationReport:
    """
    Validate policy structure, requirement traceability, coverage,
    numeric preservation, and placeholder usage.

    This function performs deterministic checks only.
    Semantic compliance is handled by the semantic validation agent.
    """

    findings: list[ValidationFinding] = []
    unresolved = list(unresolved_items or [])

    # --------------------------------------------------
    # 1. Normalize authoritative requirements
    # --------------------------------------------------

    req_map = _normalize_requirements(requirements)
    known_req_ids = set(req_map)

    # --------------------------------------------------
    # 2. Section completeness
    # --------------------------------------------------

    if not sections:
        findings.append(
            ValidationFinding(
                rule_name="section_completeness",
                status="FAIL",
                message="Policy contains no sections.",
                details=[
                    "At least one policy section is required."
                ],
            )
        )

    else:
        empty_sections = [
            str(getattr(section, "section_id", None) or "<empty ID>")
            for section in sections
            if not str(getattr(section, "title", None) or "").strip()
            or not str(getattr(section, "content", None) or "").strip()
        ]

        findings.append(
            ValidationFinding(
                rule_name="section_completeness",
                status="FAIL" if empty_sections else "PASS",
                message=(
                    "One or more policy sections are empty."
                    if empty_sections
                    else "All policy sections have titles and content."
                ),
                details=[
                    f"Empty section: {section_id}"
                    for section_id in empty_sections
                ],
            )
        )

    # --------------------------------------------------
    # 3. Section ID validity
    # --------------------------------------------------

    section_ids = [
        str(getattr(section, "section_id", None) or "").strip()
        for section in sections
    ]

    id_issues: list[str] = []

    if any(not section_id for section_id in section_ids):
        id_issues.append(
            "One or more sections have an empty section_id."
        )

    seen_section_ids: set[str] = set()
    duplicate_section_ids: set[str] = set()

    for section_id in section_ids:
        if not section_id:
            continue

        if section_id in seen_section_ids:
            duplicate_section_ids.add(section_id)

        seen_section_ids.add(section_id)

    id_issues.extend(
        f"Duplicate section ID: {section_id}"
        for section_id in sorted(duplicate_section_ids)
    )

    findings.append(
        ValidationFinding(
            rule_name="section_id_validity",
            status="FAIL" if id_issues else "PASS",
            message=(
                "Section IDs must be present and unique."
                if id_issues
                else "All section IDs are present and unique."
            ),
            details=id_issues,
        )
    )

    # --------------------------------------------------
    # 4. Requirement mapping integrity
    # --------------------------------------------------

    cited_ids: set[str] = set()
    mapping_issues: list[str] = []

    for section in sections:
        section_id = str(
            getattr(section, "section_id", None) or "<empty ID>"
        )

        requirement_ids = getattr(
            section,
            "requirement_ids",
            None,
        ) or []

        if not isinstance(requirement_ids, list):
            mapping_issues.append(
                f"Section {section_id} has invalid requirement_ids."
            )
            continue

        section_requirement_ids: list[str] = []

        for requirement_id in requirement_ids:
            if not isinstance(requirement_id, str):
                mapping_issues.append(
                    f"Section {section_id} contains a non-string "
                    "requirement ID."
                )
                continue

            normalized_id = requirement_id.strip()

            if not normalized_id:
                mapping_issues.append(
                    f"Section {section_id} contains an empty requirement ID."
                )
                continue

            section_requirement_ids.append(normalized_id)
            cited_ids.add(normalized_id)

        if len(section_requirement_ids) != len(
            set(section_requirement_ids)
        ):
            mapping_issues.append(
                f"Section {section_id} contains duplicate requirement IDs."
            )

    unauthorized_ids = cited_ids - known_req_ids

    mapping_issues.extend(
        f"Unknown requirement ID cited: {requirement_id}"
        for requirement_id in sorted(unauthorized_ids)
    )

    findings.append(
        ValidationFinding(
            rule_name="source_id_validity",
            status="FAIL" if mapping_issues else "PASS",
            message=(
                "One or more policy requirement mappings are invalid."
                if mapping_issues
                else "All cited requirement IDs are valid and unique."
            ),
            details=mapping_issues,
        )
    )

    # --------------------------------------------------
    # 5. Requirement coverage
    # --------------------------------------------------

    missing_ids = sorted(known_req_ids - cited_ids)

    coverage = round(
        (len(known_req_ids) - len(missing_ids))
        / len(known_req_ids),
        4,
    )

    findings.append(
        ValidationFinding(
            rule_name="requirement_coverage",
            status="FAIL" if missing_ids else "PASS",
            message=(
                f"Requirement coverage is {coverage:.0%}; "
                f"{len(missing_ids)} requirements are not mapped."
                if missing_ids
                else "100% of validated requirement IDs are cited "
                     "in policy sections."
            ),
            details=[
                f"Unaddressed requirement: {requirement_id}"
                for requirement_id in missing_ids
            ],
        )
    )

    # --------------------------------------------------
    # 6. Numeric and unit preservation
    # --------------------------------------------------

    numeric_failures: list[str] = []

    for req_id, req_data in req_map.items():

        mapped_content = "\n".join(
            str(section.content or "")
            for section in sections
            if req_id in (
                getattr(section, "requirement_ids", None) or []
            )
        )

        for numeric_value in req_data["numeric_values"]:

            if numeric_value.casefold() not in mapped_content.casefold():
                numeric_failures.append(
                    f"Requirement {req_id}: source numeric/unit value "
                    f"'{numeric_value}' was not found in mapped policy content."
                )

    findings.append(
        ValidationFinding(
            rule_name="numeric_preservation",
            status="FAIL" if numeric_failures else "PASS",
            message=(
                "One or more source numeric/unit values are missing "
                "from their mapped policy sections."
                if numeric_failures
                else "All extracted source numeric/unit values are present "
                     "in their mapped policy sections."
            ),
            details=numeric_failures,
        )
    )

    # --------------------------------------------------
    # 7. Placeholder detection
    # --------------------------------------------------

    full_text = "\n\n".join(
        f"{section.title}\n{section.content}"
        for section in sections
    )

    placeholders = [
        match.group(0)
        for pattern in PLACEHOLDER_PATTERNS
        for match in pattern.finditer(full_text)
    ]

    findings.append(
        ValidationFinding(
            rule_name="placeholder_detection",
            status="FAIL" if placeholders else "PASS",
            message=(
                "Policy draft contains incomplete placeholder tokens."
                if placeholders
                else "No configured placeholder tokens were found."
            ),
            details=[
                f"Found placeholder: {value}"
                for value in placeholders
            ],
        )
    )

    # --------------------------------------------------
    # 8. Build validation report
    # --------------------------------------------------

    return _build_report(
        findings=findings,
        missing_ids=missing_ids,
        unresolved_items=unresolved,
        coverage_score=coverage,
    )



def validate_policy_modification(
    original_section: PolicySectionModel,
    revised_section: PolicySectionModel,
    instructions: str,
    requirements: list[ValidatedRequirementInput] | list[dict[str, Any]],
) -> PolicyValidationReport:
    """
    Perform deterministic structural and traceability checks for a
    proposed policy modification.

    Semantic compliance, numeric changes, business-rule conflicts,
    and instruction correctness must be checked by the semantic
    policy validation agent.
    """
    findings: list[ValidationFinding] = []

    original_content = str(original_section.content or "").strip()
    revised_content = str(revised_section.content or "").strip()

    # 1. Validate section identity and content.
    identity_issues: list[str] = []

    if original_section.section_id != revised_section.section_id:
        identity_issues.append(
            "The revised section changed the original section_id."
        )

    if not str(revised_section.title or "").strip():
        identity_issues.append(
            "The revised section has no title."
        )

    if not revised_content:
        identity_issues.append(
            "The revised section has no content."
        )

    findings.append(
        ValidationFinding(
            rule_name="modification_section_identity",
            status="FAIL" if identity_issues else "PASS",
            message=(
                "The revised section identity or content is invalid."
                if identity_issues
                else "The revised section retains its original identity and valid content."
            ),
            details=identity_issues,
        )
    )

    # 2. Validate modification instruction input.
    instruction_issues: list[str] = []

    if not str(instructions or "").strip():
        instruction_issues.append(
            "Modification instructions cannot be empty."
        )

    if not original_content:
        instruction_issues.append(
            "The original section content is empty."
        )

    if (
        original_content
        and revised_content
        and original_content == revised_content
    ):
        instruction_issues.append(
            "The revised section has not changed from the original section."
        )

    findings.append(
        ValidationFinding(
            rule_name="modification_input_validity",
            status="FAIL" if instruction_issues else "PASS",
            message=(
                "The modification input is invalid."
                if instruction_issues
                else "The modification input is structurally valid."
            ),
            details=instruction_issues,
        )
    )

    # 3. Validate authoritative requirement mappings.
    requirement_issues: list[str] = []

    known_requirement_ids: set[str] = set()

    for raw_requirement in requirements:
        normalized = _normalize_requirement(raw_requirement)

        if normalized is None:
            requirement_issues.append(
                "An unsupported requirement input was provided."
            )
            continue

        requirement_id, source_text, _ = normalized

        if not requirement_id:
            requirement_issues.append(
                "An authoritative requirement has an empty requirement_id."
            )
            continue

        if not source_text:
            requirement_issues.append(
                f"Requirement {requirement_id} has empty source text."
            )
            continue

        if requirement_id in known_requirement_ids:
            requirement_issues.append(
                f"Duplicate authoritative requirement ID: {requirement_id}."
            )
            continue

        known_requirement_ids.add(requirement_id)

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

    # Existing mappings must not be silently removed.
    removed_ids = original_ids - revised_ids

    if removed_ids:
        requirement_issues.append(
            "The revision removed existing requirement mappings: "
            + ", ".join(sorted(removed_ids))
        )

    # All mappings must reference known authoritative requirements.
    unknown_ids = revised_ids - known_requirement_ids

    if unknown_ids:
        requirement_issues.append(
            "The revision references unknown requirement IDs: "
            + ", ".join(sorted(unknown_ids))
        )

    findings.append(
        ValidationFinding(
            rule_name="modification_traceability",
            status="FAIL" if requirement_issues else "PASS",
            message=(
                "Requirement mapping validation failed."
                if requirement_issues
                else "Authoritative requirement mappings are valid and preserved."
            ),
            details=requirement_issues,
        )
    )

    return _build_report(findings)



def merge_policy_validation_reports(
    deterministic_report: PolicyValidationReport,
    semantic_report: Any,
    total_requirements: int | None = None,
) -> PolicyValidationReport:
    """
    Merge deterministic and semantic policy validation reports.

    Status priority:
        FAIL > NEEDS_CLARIFICATION > PASS

    Deterministic validation provides structural and traceability checks.
    Semantic validation provides meaning, compliance, and business-rule checks.
    """

    if deterministic_report is None:
        raise ValueError(
            "Deterministic policy validation report is required."
        )

    if semantic_report is None:
        raise ValueError(
            "Semantic policy validation report is required."
        )

    # Start with deterministic validation findings.
    merged_findings: list[ValidationFinding] = list(
        deterministic_report.findings or []
    )

    # Add semantic validation findings.
    semantic_findings = getattr(
        semantic_report,
        "findings",
        [],
    ) or []

    for finding in semantic_findings:
        if isinstance(finding, ValidationFinding):
            merged_findings.append(finding)

        elif isinstance(finding, dict):
            merged_findings.append(
                ValidationFinding.model_validate(finding)
            )

        else:
            raise ValueError(
                "Semantic validation returned an unsupported finding type: "
                f"{type(finding).__name__}"
            )

    # Merge missing requirement IDs without duplicates.
    missing_requirements: list[str] = []
    seen_missing: set[str] = set()

    all_missing = [
        *(deterministic_report.missing_requirements or []),
        *(
            getattr(semantic_report, "missing_requirements", [])
            or []
        ),
    ]

    for requirement_id in all_missing:
        if not isinstance(requirement_id, str):
            continue

        normalized_id = requirement_id.strip()

        if normalized_id and normalized_id not in seen_missing:
            missing_requirements.append(normalized_id)
            seen_missing.add(normalized_id)

    # Merge clarification items without duplicates.
    clarification_items: list[str] = []
    seen_clarifications: set[str] = set()

    all_clarifications = [
        *(deterministic_report.clarification_items or []),
        *(
            getattr(semantic_report, "clarification_items", [])
            or []
        ),
    ]

    for item in all_clarifications:
        if not isinstance(item, str):
            continue

        normalized_item = item.strip()
        comparison_key = normalized_item.casefold()

        if normalized_item and comparison_key not in seen_clarifications:
            clarification_items.append(normalized_item)
            seen_clarifications.add(comparison_key)

    # Preserve the semantic agent's overall status.
    semantic_status = getattr(
        semantic_report,
        "overall_status",
        None,
    )

    if semantic_status not in {
        "PASS",
        "FAIL",
        "NEEDS_CLARIFICATION",
    }:
        raise ValueError(
            f"Invalid semantic validation status: {semantic_status!r}"
        )

    # A semantic FAIL must never be silently converted into PASS.
    has_failure = (
        deterministic_report.overall_status == "FAIL"
        or semantic_status == "FAIL"
        or any(finding.status == "FAIL" for finding in merged_findings)
    )

    has_clarification = (
        deterministic_report.overall_status == "NEEDS_CLARIFICATION"
        or semantic_status == "NEEDS_CLARIFICATION"
        or bool(clarification_items)
        or any(
            finding.status == "NEEDS_CLARIFICATION"
            for finding in merged_findings
        )
    )

    if has_failure:
        overall_status = "FAIL"

    elif has_clarification:
        overall_status = "NEEDS_CLARIFICATION"

    else:
        overall_status = "PASS"

    # If the semantic agent reports a non-PASS status without findings,
    # preserve that status in the merged report.
    if semantic_status == "FAIL" and not any(
        finding.status == "FAIL"
        for finding in semantic_findings
    ):
        merged_findings.append(
            ValidationFinding(
                rule_name="semantic_validation",
                status="FAIL",
                message=(
                    "Semantic validation reported FAIL. "
                    "Review the semantic validation result."
                ),
                details=[],
            )
        )

    elif semantic_status == "NEEDS_CLARIFICATION" and not any(
        finding.status == "NEEDS_CLARIFICATION"
        for finding in semantic_findings
    ) and not clarification_items:
        merged_findings.append(
            ValidationFinding(
                rule_name="semantic_validation",
                status="NEEDS_CLARIFICATION",
                message=(
                    "Semantic validation requires clarification."
                ),
                details=[],
            )
        )

    return PolicyValidationReport(
        overall_status=overall_status,
        coverage_score=deterministic_report.coverage_score,
        missing_requirements=missing_requirements,
        findings=merged_findings,
        clarification_items=clarification_items,
    )

