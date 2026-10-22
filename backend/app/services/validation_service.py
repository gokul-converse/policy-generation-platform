"""Deterministic policy validation layer.

Validates policy draft structure, requirement coverage, source ID authenticity,
numeric and unit preservation, placeholder absence, and unresolved clarification items.
"""

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
    re.compile(r"\[TODO[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[TBD[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[INSERT[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[PLACEHOLDER[^\]]*\]", re.IGNORECASE),
]


def validate_policy_draft(
    sections: list[PolicySectionModel],
    requirements: list[ValidatedRequirementInput] | list[dict[str, Any]],
    unresolved_items: list[str] | None = None,
) -> PolicyValidationReport:
    """Perform deterministic validation on a generated or edited policy draft."""

    findings: list[ValidationFinding] = []
    unresolved = list(unresolved_items or [])

    # 1. Normalize requirements map
    req_map: dict[str, dict[str, Any]] = {}
    for req in requirements:
        if isinstance(req, ValidatedRequirementInput):
            req_id = req.requirement_id
            text = req.text
            numerics = list(req.numeric_values)
            if not numerics:
                numerics = extract_numbers_and_units(text)
        elif isinstance(req, dict):
            req_id = str(req.get("requirement_id", "")).strip()
            text = str(req.get("text", "")).strip()
            numerics = list(req.get("numeric_values") or [])
            if not numerics:
                numerics = extract_numbers_and_units(text)
        else:
            continue

        if req_id:
            req_map[req_id] = {
                "text": text,
                "numeric_values": numerics,
            }

    known_req_ids = set(req_map.keys())

    # 2. Section Completeness Check
    if not sections:
        findings.append(
            ValidationFinding(
                rule_name="section_completeness",
                status="FAIL",
                message="Policy contains no sections.",
                details=["At least one policy section is required."],
            )
        )
    else:
        empty_sections = [
            s.section_id for s in sections if not s.content.strip() or not s.title.strip()
        ]
        if empty_sections:
            findings.append(
                ValidationFinding(
                    rule_name="section_completeness",
                    status="FAIL",
                    message="One or more policy sections are empty.",
                    details=[f"Empty section ID: {sid}" for sid in empty_sections],
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    rule_name="section_completeness",
                    status="PASS",
                    message="All policy sections have titles and content.",
                    details=[],
                )
            )

    # 3. Source ID Validity Check
    cited_ids: set[str] = set()
    for s in sections:
        for rid in s.requirement_ids:
            cited_ids.add(rid)

    unauthorized_ids = cited_ids - known_req_ids
    if unauthorized_ids:
        findings.append(
            ValidationFinding(
                rule_name="source_id_validity",
                status="FAIL",
                message="Policy references unauthorized or unknown requirement IDs.",
                details=[f"Unauthorized ID cited: {uid}" for uid in sorted(unauthorized_ids)],
            )
        )
    else:
        findings.append(
            ValidationFinding(
                rule_name="source_id_validity",
                status="PASS",
                message="All cited requirement IDs are valid and present in input.",
                details=[],
            )
        )

    # 4. Coverage Score Check
    if known_req_ids:
        covered_ids = known_req_ids & cited_ids
        missing_ids = sorted(known_req_ids - covered_ids)
        coverage_score = round(len(covered_ids) / len(known_req_ids), 4)
    else:
        missing_ids = []
        coverage_score = 1.0

    if missing_ids:
        findings.append(
            ValidationFinding(
                rule_name="requirement_coverage",
                status="FAIL",
                message=f"Requirement coverage is {coverage_score:.0%}. {len(missing_ids)} requirements unaddressed.",
                details=[f"Unaddressed requirement: {mid}" for mid in missing_ids],
            )
        )
    else:
        findings.append(
            ValidationFinding(
                rule_name="requirement_coverage",
                status="PASS",
                message="100% of validated requirements are addressed in policy sections.",
                details=[],
            )
        )

    # Combine full policy text for numeric and placeholder checks
    full_text = "\n\n".join(f"{s.title}\n{s.content}" for s in sections)

    # 5. Numeric and Unit Preservation Check
    numeric_failures: list[str] = []
    for req_id, req_data in req_map.items():
        # Get content from sections claiming this requirement, or fall back to full policy text
        mapped_content = "\n".join(
            s.content for s in sections if req_id in s.requirement_ids
        )
        content_to_check = mapped_content if mapped_content.strip() else full_text

        for num_val in req_data["numeric_values"]:
            # Clean and check if number/unit is preserved
            cleaned_num = num_val.strip()
            if cleaned_num and cleaned_num.lower() not in content_to_check.lower():
                numeric_failures.append(
                    f"Requirement {req_id} numeric value '{cleaned_num}' missing from policy text."
                )

    if numeric_failures:
        findings.append(
            ValidationFinding(
                rule_name="numeric_preservation",
                status="FAIL",
                message="Numeric values or units from requirements were altered or omitted.",
                details=numeric_failures,
            )
        )
    else:
        findings.append(
            ValidationFinding(
                rule_name="numeric_preservation",
                status="PASS",
                message="All numeric values and units from source requirements are preserved.",
                details=[],
            )
        )

    # 6. Placeholder Detection Check
    detected_placeholders: list[str] = []
    for pattern in PLACEHOLDER_PATTERNS:
        matches = pattern.findall(full_text)
        if matches:
            detected_placeholders.extend(matches)

    if detected_placeholders:
        findings.append(
            ValidationFinding(
                rule_name="placeholder_detection",
                status="FAIL",
                message="Policy draft contains incomplete placeholder tokens.",
                details=[f"Found placeholder: {ph}" for ph in detected_placeholders],
            )
        )
    else:
        findings.append(
            ValidationFinding(
                rule_name="placeholder_detection",
                status="PASS",
                message="No incomplete placeholder tokens found.",
                details=[],
            )
        )

    # 7. Unresolved Items Check
    if unresolved:
        findings.append(
            ValidationFinding(
                rule_name="unresolved_clarifications",
                status="NEEDS_CLARIFICATION",
                message="Policy contains unresolved questions or decision gaps requiring user clarification.",
                details=unresolved,
            )
        )

    # 8. Compute Overall Status
    has_failures = any(f.status == "FAIL" for f in findings)
    if has_failures:
        overall_status = "FAIL"
    elif unresolved:
        overall_status = "NEEDS_CLARIFICATION"
    else:
        overall_status = "PASS"

    return PolicyValidationReport(
        overall_status=overall_status,
        coverage_score=coverage_score,
        missing_requirements=missing_ids,
        findings=findings,
        clarification_items=unresolved,
    )
