---
name: it-security-policy-drafting
description: Draft IT security policy content for password management, MFA, access
  provisioning, data handling, device usage, and incident reporting, aligned with
  the provided validated requirement.
metadata:
  requirement_ids:
  - 1a367a18-7008-4c40-9fff-2e1f29b1139f
---

# IT Security Policy: Password Management and Access Controls

## Purpose
Draft IT security policy content for password management, MFA, access provisioning, data handling, device usage, and incident reporting, aligned with the provided validated requirement.

## Instructions
- Follow the validated requirement text to generate a policy skeleton and content sections that address password management, MFA, access provisioning, data classification and handling, incident reporting, and employee responsibilities. Ensure alignment with IT security governance and avoid introducing new business rules beyond the provided requirement.

## Source Requirements
- 1a367a18-7008-4c40-9fff-2e1f29b1139f: {"policy_name": null, "domain": "it_security", "purpose": "Establish and communicate the organization's IT security controls for password management, multi-factor authentication, data access permissions, device usage, incident reporting, and employee responsibilities for protecting confidential information.", "scope": "Policy applies to all corporate systems, confidential and sensitive data, employees, contractors, and guests with access. It covers production, testing, development, legacy systems, and BYOD devices accessing company resources. Personal systems without company access and public data are out of scope unless required by company security standards.", "stakeholders": ["IT Security", "HR", "Managers", "System Owners", "Data Owners", "Employees", "Contractors", "Guests"], "rules": ["Enforce 14-character minimum passwords; block compromised passwords; prevent reuse of the last 10 passwords; lock accounts after 10 failed login attempts; enable MFA; enforce secure resets; rotate passwords when compromised.", "MFA must be used for access to corporate systems using authenticator apps or hardware security keys; SMS is allowed only where approved; exceptions require a documented business justification, manager and IT security approvals, and an expiry date; unresolved requests escalated to the security lead; revoke exceptions when no longer needed.", "Access provisioning follows least-privilege; employees submit access requests; approvals required from the employee's manager and system owner; IT provisions access; HR is notified of terminations or role changes; IT revokes or updates access promptly.", "Data classified as Public, Internal, Confidential, or Restricted; data owners assign classifications; access controls, encryption, and retention appropriate to each level; IT Security reviews and enforces compliance; encryption in transit and at rest as appropriate; retention rules align with classification.", "Incident reporting process established with escalation to IT Security; incidents are logged and managed according to defined processes.", "Employees have responsibilities to protect confidential information; comply with policy; not share credentials; report suspected incidents; complete security training as directed."], "unresolved_details": ["Policy naming conventions and versioning approach", "Enforcement actions, penalties, and performance metrics", "Retention periods for access logs and security event data", "Incident response SLAs and testing frequency", "Security training cadence, content, and tracking metrics", "Integration with existing identity and access management systems", "BYOD policy alignment and device enrollment requirements"]}
