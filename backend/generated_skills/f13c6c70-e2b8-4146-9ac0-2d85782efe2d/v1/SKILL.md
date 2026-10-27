---
name: sample-leave-policy-draft
description: Draft, review, and maintain a reusable Sample Leave Policy draft based
  on the validated requirement. Ensures source requirements text is preserved, and
  the policy draft is structured for adoption.
metadata:
  requirement_ids:
  - d4ad4bc2-91b9-4289-9edb-a8fad9e5fdec
---

# Sample Leave Policy Draft

## Purpose

Provide a reusable draft of the Sample Leave Policy based on the validated requirement. This skill outputs a policy draft suitable for review, while preserving the original requirement text in the Source Requirements section.

## Instructions

1. Load the validated requirement text for the policy with ID d4ad4bc2-91b9-4289-9edb-a8fad9e5fdec from the input.
2. Create a policy draft titled using the policy_name field from the requirement (Sample Leave Policy).
3. Structure the draft with sections such as Purpose, Scope, Entitlements, Leave Request Process, Carry-forward and Encashment rules, Emergency/unplanned absences, Documentation requirements, and Responsibilities.
4. In the Source Requirements section, reference the original requirement text exactly as captured in the input.
5. In the Source Requirements, include one bullet per requirement in the input, formatted as:
- REQUIREMENT_ID: ORIGINAL_REQUIREMENT_TEXT
6. Place the Source Requirements section after its heading and ensure the overall instruction block maintains the order: Purpose, Instructions, Source Requirements.
7. Do not include commentary outside this structured draft.

## Source Requirements

- d4ad4bc2-91b9-4289-9edb-a8fad9e5fdec: {"policy_name": "Sample Leave Policy", "domain": "hr", "purpose": "Define annual, sick, and casual leave entitlements; observe public holidays; establish eligibility by employment type and tenure; set the process for submitting leave requests and manager approvals; outline carry-forward and encashment rules; define procedures for emergency/unplanned absences; specify documentation requirements for extended sick leave; and delineate responsibilities of employees, managers, and HR.", "scope": "All employees (full-time, probationary, temporary/contract, part-time) across jurisdictions where local labor laws apply; applies to annual, sick, casual leaves, and public holidays; excludes unpaid leaves beyond policy and any exemptions defined by law.", "stakeholders": ["Employees", "Line Managers", "HR", "HR Portal IT/System Administrators", "Finance"], "rules": ["Leave entitlements by employment type: Permanent and probationary employees receive 15 annual leave days, 12 sick leave days, and 12 casual leave days per year.", "Leave entitlements for Temporary, Contract, and Part-time employees are pro-rated based on actual hours worked relative to full-time hours, with minimum entitlements governed by applicable jurisdiction.", "Pro-rata calculation method: based on actual hours worked relative to full-time hours.", "Carry-forward: unused annual leave may be carried forward up to 30 days.", "Carry-forward expiry: carried-forward leave expires after 12 months.", "Encashment/forfeiture: the decision to encash or forfeit unused leave depends on leave type, company policy, and applicable labor laws.", "Leave request submission: requests must be submitted via the HR portal, specifying dates and leave type.", "Approval timeline: managers must review and approve or reject requests within 2 business days.", "Escalation: unresolved requests should be escalated to HR.", "Emergency/unplanned absences: procedures to handle such absences are defined in policy.", "Documentation: documentation requirements for extended sick leave are specified in policy.", "Responsibilities: clearly define responsibilities of employees, managers, and HR regarding leave administration.", "Compliance: leave rules must comply with local laws and jurisdiction-specific requirements (to be confirmed with HR)."], "unresolved_details": ["Jurisdiction-specific minimum annual entitlements for non-full-time staff; confirm with HR.", "Tax treatment and implications of encashment of unused leave; confirm with HR based on employee jurisdiction.", "Public holidays entitlements and treatment (paid status, eligibility, and observance) across jurisdictions.", "Final, system-level details for the leave management workflow beyond 'HR portal' (system name, URLs, access roles, and integration specifics).", "Any additional SLA or escalation pathways beyond the 2-business-day approval window that may be required by policy.", "Public holidays policy across jurisdictions: number of public holidays per year, paid status, eligibility, and interaction with leave balances (e.g., if a holiday occurs during annual/sick/casual leave).", "The clarification limit was reached; remaining details are listed for review."]}
