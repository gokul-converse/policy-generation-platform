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
    requirement: Any,
) -> tuple[str, str, list[str]]:
    """
    Normalize one Source Requirement.

    Returns:
        requirement_id, source_text, numeric_values
    """

    if isinstance(requirement, ValidatedRequirementInput):
        requirement_id = str(
            requirement.requirement_id or ""
        ).strip()

        source_text = str(requirement.text or "").strip()
        numeric_values = list(requirement.numeric_values or [])

    elif isinstance(requirement, dict):
        requirement_id = str(
            requirement.get("requirement_id") or ""
        ).strip()

        source_text = str(
            requirement.get("text")
            or requirement.get("requirement_text")
            or requirement.get("description")
            or ""
        ).strip()

        numeric_values = list(
            requirement.get("numeric_values") or []
        )

    else:
        raise ValueError(
            f"Unsupported Source Requirement type: "
            f"{type(requirement).__name__}"
        )

    if not requirement_id:
        raise ValueError(
            "Every Source Requirement must have a requirement_id."
        )

    if not source_text:
        raise ValueError(
            f"Source Requirement '{requirement_id}' has empty text."
        )

    if not numeric_values:
        numeric_values = extract_numbers_and_units(source_text)

    normalized_values = [
        str(value).strip()
        for value in numeric_values
        if str(value).strip()
    ]

    return requirement_id, source_text, normalized_values


def _normalize_requirements(
    requirements: list[
        ValidatedRequirementInput | dict[str, Any]
    ],
) -> dict[str, dict[str, Any]]:
    """Normalize and validate all skill Source Requirements."""

    if not requirements:
        raise ValueError(
            "At least one skill Source Requirement is required."
        )

    requirement_map: dict[str, dict[str, Any]] = {}

    for index, requirement in enumerate(requirements, start=1):
        try:
            requirement_id, source_text, numeric_values = (
                _normalize_requirement(requirement)
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid Source Requirement at position {index}: {exc}"
            ) from exc

        if requirement_id in requirement_map:
            raise ValueError(
                f"Duplicate Source Requirement ID: {requirement_id}"
            )

        requirement_map[requirement_id] = {
            "text": source_text,
            "numeric_values": numeric_values,
        }

    return requirement_map



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


def _validate_section_numbering(
    sections: list[PolicySectionModel],
) -> list[str]:
    """
    Validate hierarchical handbook numbering.

    Valid:
        1
        1.1
        1.2
        2
        2.1

    Invalid:
        SEC-001
        1.3 before 1.2
        2.1 before section 2
        1, 3 (missing section 2)
    """

    issues: list[str] = []

    main_sections: list[int] = []
    subsection_counts: dict[int, int] = {}

    for section in sections:
        section_id = str(
            getattr(section, "section_id", "") or ""
        ).strip()

        if not re.fullmatch(r"[1-9]\d*(?:\.[1-9]\d*)?", section_id):
            issues.append(
                f"Invalid handbook section ID '{section_id}'. "
                "Expected numbering such as 1, 1.1 or 1.2."
            )
            continue

        if "." not in section_id:
            main_number = int(section_id)
            expected_main = len(main_sections) + 1

            if main_number != expected_main:
                issues.append(
                    f"Expected main section {expected_main}, "
                    f"but received {section_id}."
                )
                continue

            main_sections.append(main_number)
            subsection_counts[main_number] = 0

        else:
            main_part, subsection_part = section_id.split(".")

            main_number = int(main_part)
            subsection_number = int(subsection_part)

            if main_number not in main_sections:
                issues.append(
                    f"Subsection {section_id} has no preceding "
                    f"main section {main_number}."
                )
                continue

            expected_subsection = (
                subsection_counts[main_number] + 1
            )

            if subsection_number != expected_subsection:
                issues.append(
                    f"Expected subsection "
                    f"{main_number}.{expected_subsection}, "
                    f"but received {section_id}."
                )
                continue

            subsection_counts[main_number] = subsection_number

    return issues


def validate_policy_draft(
    sections: list[PolicySectionModel],
    requirements: list[
        ValidatedRequirementInput | dict[str, Any]
    ],
    unresolved_items: list[str] | None = None,
) -> PolicyValidationReport:
    """
    Perform deterministic validation of a generated policy.

    Validates:
    1. Section completeness.
    2. Section ID validity.
    3. Source Requirement mapping integrity.
    4. Source Requirement coverage.
    5. Numeric and unit preservation.
    6. Placeholder detection.

    Semantic compliance is handled separately by the
    Policy Validation Agent.

    Requirements are taken from the selected SkillVersion.
    """

    findings: list[ValidationFinding] = []
    unresolved = list(unresolved_items or [])

    # --------------------------------------------------
    # 1. Normalize skill Source Requirements
    # --------------------------------------------------

    requirement_map = _normalize_requirements(requirements)
    known_requirement_ids = set(requirement_map)

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
            str(
                getattr(section, "section_id", None)
                or "<empty ID>"
            )
            for section in sections
            if not str(
                getattr(section, "title", None) or ""
            ).strip()
            or not str(
                getattr(section, "content", None) or ""
            ).strip()
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
        str(
            getattr(section, "section_id", None) or ""
        ).strip()
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
    # 3A. Handbook section numbering
    # --------------------------------------------------

    numbering_issues = _validate_section_numbering(
        sections
    )

    findings.append(
        ValidationFinding(
            rule_name="handbook_section_numbering",
            status=(
                "FAIL"
                if numbering_issues
                else "PASS"
            ),
            message=(
                "Policy section numbering does not follow "
                "the required handbook hierarchy."
                if numbering_issues
                else "Policy section numbering follows "
                "the required handbook hierarchy."
            ),
            details=numbering_issues,
        )
    )


    # --------------------------------------------------
    # 4. Source Requirement mapping integrity
    # --------------------------------------------------

    cited_requirement_ids: set[str] = set()
    mapping_issues: list[str] = []

    for section in sections:
        section_id = str(
            getattr(section, "section_id", None)
            or "<empty ID>"
        )

        requirement_ids = (
            getattr(section, "requirement_ids", None) or []
        )

        if not isinstance(requirement_ids, list):
            mapping_issues.append(
                f"Section {section_id} has invalid requirement_ids."
            )
            continue

        section_requirement_ids: list[str] = []

        for requirement_id in requirement_ids:
            if not isinstance(requirement_id, str):
                mapping_issues.append(
                    f"Section {section_id} contains a "
                    "non-string Source Requirement ID."
                )
                continue

            normalized_id = requirement_id.strip()

            if not normalized_id:
                mapping_issues.append(
                    f"Section {section_id} contains an empty "
                    "Source Requirement ID."
                )
                continue

            section_requirement_ids.append(normalized_id)
            cited_requirement_ids.add(normalized_id)

        if len(section_requirement_ids) != len(
            set(section_requirement_ids)
        ):
            mapping_issues.append(
                f"Section {section_id} contains duplicate "
                "Source Requirement IDs."
            )

    unknown_requirement_ids = (
        cited_requirement_ids - known_requirement_ids
    )

    mapping_issues.extend(
        f"Unknown Source Requirement ID cited: {requirement_id}"
        for requirement_id in sorted(unknown_requirement_ids)
    )

    findings.append(
        ValidationFinding(
            rule_name="source_requirement_mapping",
            status="FAIL" if mapping_issues else "PASS",
            message=(
                "One or more Source Requirement mappings are invalid."
                if mapping_issues
                else "All cited Source Requirement IDs are valid."
            ),
            details=mapping_issues,
        )
    )

    # --------------------------------------------------
    # 5. Source Requirement coverage
    # --------------------------------------------------

    missing_requirement_ids = sorted(
        known_requirement_ids - cited_requirement_ids
    )

    total_requirements = len(known_requirement_ids)

    coverage_score = round(
        (
            total_requirements
            - len(missing_requirement_ids)
        ) / total_requirements,
        4,
    )

    findings.append(
        ValidationFinding(
            rule_name="source_requirement_coverage",
            status=(
                "FAIL"
                if missing_requirement_ids
                else "PASS"
            ),
            message=(
                f"Source Requirement coverage is "
                f"{coverage_score:.0%}; "
                f"{len(missing_requirement_ids)} "
                "requirements are not mapped."
                if missing_requirement_ids
                else "100% of skill Source Requirements "
                "are mapped to policy sections."
            ),
            details=[
                f"Unaddressed Source Requirement: {requirement_id}"
                for requirement_id in missing_requirement_ids
            ],
        )
    )

    # --------------------------------------------------
    # 6. Numeric and unit preservation
    # --------------------------------------------------

    numeric_failures: list[str] = []

    for requirement_id, requirement_data in requirement_map.items():

        mapped_content = "\n".join(
            str(section.content or "")
            for section in sections
            if requirement_id in (
                getattr(section, "requirement_ids", None) or []
            )
        )

        for numeric_value in requirement_data["numeric_values"]:
            if numeric_value.casefold() not in mapped_content.casefold():
                numeric_failures.append(
                    f"Source Requirement {requirement_id}: "
                    f"numeric/unit value '{numeric_value}' "
                    "is missing from its mapped policy content."
                )

    findings.append(
        ValidationFinding(
            rule_name="numeric_preservation",
            status="FAIL" if numeric_failures else "PASS",
            message=(
                "One or more source numeric/unit values "
                "are missing from mapped policy sections."
                if numeric_failures
                else "All extracted source numeric/unit values "
                "are preserved in mapped policy sections."
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
        missing_ids=missing_requirement_ids,
        unresolved_items=unresolved,
        coverage_score=coverage_score,
    )



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


