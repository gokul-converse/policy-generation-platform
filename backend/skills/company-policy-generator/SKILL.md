---
name: company-policy-generator
description: Generate, review, and update professional company policies of any kind - HR (leave, code of conduct, remote work, anti-harassment/POSH, recruitment, performance), IT and information security (acceptable use, data protection, BYOD, access control, incident response, backup, AI use), finance (expenses, procurement, travel, anti-bribery), legal/compliance (whistleblower, conflict of interest, privacy), and operations/health and safety. Make sure to use this skill whenever the user mentions a policy, SOP, handbook, code of conduct, employee guidelines, compliance document, or asks to "draft", "write", "create", "update", or "review" any internal company rule or document, even if they do not use the word "policy".
---

# Company Policy Generator

Produce policies that are ready to adopt: consistent structure, plain language, enforceable wording, and aligned with the laws that apply to the company. Policies fail in practice when they are vague, copied from another jurisdiction, or impossible to enforce, so every step below aims at clarity, applicability, and enforceability.

## Workflow

1. **Identify the policy type(s).** Match the request to `references/policy-catalog.md`, which lists the standard contents for each policy. If the user asks for a full set ("all HR policies", "policies for a new company"), propose the list from the catalog and confirm before drafting.
2. **Gather company context.** Needed: company name, industry, size, locations/jurisdiction, work model (office/hybrid/remote), and any existing policies or template. If the user has not given these, ask once, in a single short message, and offer to proceed with placeholders. Do not interrogate; ask only for facts that change the content.
3. **Pick the legal frame.** Read `references/legal-frameworks.md` and cite only the laws that apply to the stated jurisdiction and industry. Default to India if no jurisdiction is given and say so. If a law's requirement is uncertain or may have changed, flag it for legal verification instead of asserting it, because a wrongly cited statute undermines the whole policy.
4. **Draft** using the standard structure below.
5. **Quality check** against the checklist below before delivering.
6. **Deliver** in the requested format (see Output formats).

## Standard structure

Use this order unless the user supplies a house template, in which case follow their template.

1. Document control block (policy title, ID, version, effective date, owner, approver, next review date)
2. Purpose
3. Scope (who and what it covers, including contractors/interns where relevant)
4. Definitions (only terms actually used)
5. Policy statements (the rules, numbered 1.1, 1.2 for easy reference)
6. Roles and responsibilities (employee, manager, HR/IT/Finance, leadership)
7. Procedures (step-by-step for requests, approvals, reporting, with timelines)
8. Exceptions and approval process
9. Violations and disciplinary action
10. Related policies and legal references
11. Review cycle and revision history
12. Acknowledgement/sign-off (where employees must confirm)

## Drafting rules

- **Use "must", "may", "must not"** with consistent meaning. "Should" creates ambiguity about whether a rule is mandatory.
- **Make every rule actionable and verifiable**: who does what, by when, and how it is checked.
- **Placeholders for company-specific values**: write `[X days]`, `[Amount in INR]`, `[Designation]` in bold brackets and list all of them in a short table at the end ("Items to customise") so nothing is missed. Offer sensible suggested defaults in that table.
- **Plain language**. Short sentences, no unnecessary legalese. Policies are read by employees, not only lawyers.
- **No invented facts**. Do not fabricate statutes, section numbers, penalties, or company details. When unsure, say "verify with legal counsel".
- **Proportionate to company size**. A 20-person startup needs a 2-page policy, not 15 pages. Match depth to size and risk.
- **Consistency across a set**. When generating several policies, reuse the same terminology, roles, escalation path, and disciplinary wording.
- **Inclusive and non-discriminatory** language throughout.

## IT and security policies

These need extra care because they are technical and audit-facing.
- Name the framework the user wants alignment with (ISO 27001, SOC 2, NIST CSF, DPDP Act, GDPR) and map clauses to its controls when asked.
- Specify concrete controls (password length, MFA, patch timelines, log retention, backup frequency) as placeholders with recommended defaults, not vague statements like "strong passwords".
- Include incident reporting timelines, because regulators and frameworks set them.
- For AI use policies, cover approved tools, prohibited data inputs, human review of outputs, and IP/confidentiality.

## Reviewing or updating an existing policy

When the user supplies a policy: read it fully, list gaps against the standard structure and applicable law, then provide a revised version with changes summarised at the top. Preserve their intent and house style; change only what is needed.

## Quality checklist

- Every section in the structure is present or deliberately omitted
- No contradictions between sections or with related policies
- Applicable laws cited correctly and only where relevant
- All placeholders listed in the "Items to customise" table
- Responsibilities have named roles, not "someone"
- Violations section proportionate and consistent with disciplinary process
- Legal disclaimer included

## Output formats

- Default to a shareable document the user can edit. If the user asks for a Word or PDF file, use the docx or pdf skill respectively.
- For a policy set, produce one document per policy plus a short index listing each policy, owner, and review date.
- Keep the chat reply short: state what was produced, list the key placeholders to customise, and offer one next step.

## Mandatory disclaimer

End every policy with: "This policy is a template generated for internal use and does not constitute legal advice. Have it reviewed by qualified legal counsel before adoption."
