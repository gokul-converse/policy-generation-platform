---
name: company-policy-generator
description: Generate, review, and update professional company policies of any kind - HR (leave, code of conduct, remote work, anti-harassment/POSH, recruitment, performance), IT and information security (acceptable use, data protection, BYOD, access control, incident response, backup, AI use), finance (expenses, procurement, travel, anti-bribery), legal/compliance (whistleblower, conflict of interest, privacy), and operations/health and safety. Make sure to use this skill whenever the user mentions a policy, SOP, handbook, code of conduct, employee guidelines, compliance document, or asks to "draft", "write", "create", "update", or "review" any internal company rule or document, even if they do not use the word "policy".
---

# Company Policy Generator

Produce policies that are ready for review and adoption: consistent structure, plain language, enforceable wording, and alignment with the laws that apply to the company. Policies fail in practice when they are vague, copied from another jurisdiction, padded with empty sections, or impossible to enforce, so every step below aims at clarity, applicability, enforceability, and honesty about what is not yet decided.

## Source of truth (read first)

There are two modes. Identify which one applies before drafting.

**Mode A - Requirement-driven.** The input includes validated source requirements (with requirement IDs, rules, numbers, conditions, unresolved details). In this mode:
- The requirements are the only source of business rules. This skill guides structure, wording and quality only.
- If this skill conflicts with a requirement, the requirement wins.
- Never add rules, numbers, deadlines, penalties, approvers, review schedules or legal obligations that the requirements do not state.
- Preserve every number, unit, threshold, deadline, condition, exception, eligibility rule and negation exactly. Do not round, weaken, strengthen or merge rules in a way that changes meaning.
- Use only requirement IDs that were supplied. Never invent one.
- Do not use literal placeholders such as `[TODO]`, `[TBD]`, `[X days]` or `[INSERT]` as policy content. Report missing information as an unresolved item instead (see Handling gaps).

**Mode B - Free-form drafting.** The user asks for a policy with no source requirements (for example, "write a leave policy for my 50-person company"). In this mode:
- Use the catalog and legal frame to draft a complete policy.
- Company-specific values may be written as bold placeholders such as **[X days]** with a suggested default, and every placeholder must be listed in an "Items to customise" table at the end.

## Workflow

1. **Identify the mode and the policy type(s).** Match the request to `references/policy-catalog.md`. If the user asks for a full set ("all HR policies", "policies for a new company"), propose the list from the catalog and confirm before drafting.
2. **Gather company context.** Needed: company name, industry, size, locations/jurisdiction, work model, and any existing policies or template. If missing, ask once, in a single short message, and offer to proceed. In Mode A, do not ask for anything the requirements already answer.
3. **Pick the legal frame.** Read `references/legal-frameworks.md` and cite only the laws that apply to the stated jurisdiction and industry. Default to India if no jurisdiction is given and say so. If a law's requirement is uncertain or may have changed, flag it for legal verification instead of asserting it, because a wrongly cited statute undermines the whole policy.
4. **Map requirements (Mode A).** List every requirement ID and decide which section will carry it. Every requirement must land in at least one section or be reported as unresolved.
5. **Draft** using the standard structure below.
6. **Quality check** against the checklist below before delivering.
7. **Deliver** in the requested format (see Output formats).

## Standard structure

Use this order unless the user supplies a house template, in which case follow their template.

1. Document control block (policy title, policy ID, version, status, effective date, owner, approver, next review date, source requirement IDs)
2. Purpose
3. Scope (who and what it covers, including contractors/interns where relevant; what is out of scope)
4. Definitions (only terms actually used)
5. Policy statements (the rules, numbered 1.1, 1.2 for easy reference)
6. Roles and responsibilities (employee, manager, HR/IT/Finance, leadership)
7. Procedures (step-by-step for requests, approvals, reporting, with timelines)
8. Exceptions and approval process
9. Violations and disciplinary action
10. Related policies and legal references
11. Review cycle and revision history
12. Acknowledgement/sign-off (where employees must confirm)
13. Unresolved items (Mode A: pending decisions; required whenever any exist)
14. Requirement coverage checklist (Mode A: required)

### Section rules for every standard section

For each of the standard sections, take exactly one of these paths:

- **Supported:** the requirements (Mode A) or the catalog and context (Mode B) give real content. Draft it fully.
- **Not supported (Mode A):** the requirements say nothing. Do not invent content and do not write a stub. Record the gap in Unresolved items as a question the policy owner can answer (for example, "What notification window applies to unplanned absence?").
- **Deliberately omitted:** the section does not fit the policy or company size. Say so in one line.

Never write a section whose only content is that something "is defined", "is specified in policy", or "will be determined". An empty promise is worse than an honest gap.

## Handling gaps

- Each unresolved item is a short, actionable question or decision request a policy owner can answer.
- Carry over every unresolved detail from the source requirements. Never drop one silently.
- Add gaps found when comparing the draft to the catalog (for example, BYOD is named in the purpose but no rule covers it), labelled as "not covered by source requirements".
- Do not resolve a gap by guessing. Do not present a suggested default as an approved rule.
- Exclude generic disclaimers and technical implementation questions (APIs, databases, integrations) unless they are in scope.
- Keep source-stated rules visibly separate from unresolved decisions.

## Drafting rules

- **Use MUST, MUST NOT and MAY** with consistent meaning. Avoid "should", which leaves it unclear whether a rule is mandatory.
- **Make every rule actionable and verifiable:** who does what, by when, and how it is checked, using only what the source supports.
- **Plain language.** Short sentences, no unnecessary legalese. Policies are read by employees, not only lawyers.
- **No invented facts.** Do not fabricate statutes, section numbers, penalties, approvers, or company details. When unsure, say "verify with legal counsel".
- **Proportionate to company size.** A 20-person startup needs a 2-page policy, not 15 pages.
- **Consistency across a set.** Reuse the same terminology, roles, escalation path and disciplinary wording.
- **Inclusive and non-discriminatory** language throughout.
- **Meaningful title.** Derive the title from the policy domain if no name is given (for example, "IT Security Policy"). Never use "REQUIREMENT", "Untitled" or another placeholder as a title.
- **Traceability.** Each section that addresses a requirement lists the exact requirement IDs it covers. Do not attach an ID just because a section is on the same topic.
- **Catalog is a checklist, not content.** Use `references/policy-catalog.md` to spot missing coverage. In Mode A, an uncovered catalog item becomes an unresolved item, not new policy text.

## IT and security policies

These need extra care because they are technical and audit-facing.
- Name the framework the user or requirements want alignment with (ISO 27001, SOC 2, NIST CSF, DPDP Act, GDPR) and map clauses to its controls when asked. Do not claim alignment the source does not state.
- Keep concrete controls (password length, MFA, lockout threshold, retention) exactly as the source gives them. Where the source gives none, list the missing control as an unresolved item; in Mode B, offer a recommended default as a placeholder.
- Always address these areas, either from source content or as unresolved items: device usage and BYOD, incident reporting channel and timelines, incident severity and escalation, log retention, access reviews and joiner-mover-leaver, security training cadence and tracking, enforcement and exceptions.
- For AI use policies, cover approved tools, prohibited data inputs, human review of outputs, and IP/confidentiality.

## Work-from-home and leave policies

- Remote work: check coverage of approval authority, core hours/availability, equipment and IT support, data security, home workplace safety, and expense reimbursement. If the source does not cover one, list it as unresolved and note it needs company approval before it becomes a rule.
- Leave: check coverage of unplanned/emergency absence, sick-leave documentation, public holidays, tax/jurisdiction treatment, and specific responsibilities of employee, manager and HR. A responsibilities section must name what each role does, not just state that responsibilities exist.

## Reviewing or updating an existing policy

When the user supplies a policy: read it fully, list gaps against the standard structure, the source requirements (if any) and applicable law, then provide a revised version with changes summarised at the top. Preserve their intent and house style; change only what is needed.

## Quality checklist

Run every item before delivering. Fix failures; do not just report them.

- Every requirement ID is mapped to at least one section, or listed as unresolved (Mode A)
- Every number, unit, threshold, deadline and condition matches the source exactly
- No section is hollow, and none merely says something "is defined" or "specified in policy"
- Every unresolved detail from the source appears in the Unresolved items section
- Gaps against the catalog are listed as unresolved, not silently skipped or invented
- Title is meaningful and not a placeholder
- No `[TODO]`, `[TBD]` or `[X]` placeholders in Mode A output; all placeholders listed in "Items to customise" in Mode B
- No invented rules, penalties, approvers, review schedules or legal claims
- MUST/MUST NOT/MAY used consistently
- No contradictions between sections or with related policies
- Applicable laws cited correctly and only where relevant
- Responsibilities name roles, not "someone"
- Coverage checklist is honest: it never claims full coverage when a requirement is partial, missing or ambiguous
- Legal disclaimer and review note present

## Requirement coverage checklist (Mode A, required)

End every requirement-driven policy with a table:

| Requirement ID | Summary | Section(s) | Status |
|---|---|---|---|
| (exact ID) | (one line) | (section numbers) | Fully covered / Partially covered / Missing / Unresolved |

Status meanings: **Fully covered** means the rule is stated with all its numbers and conditions. **Partially covered** means some detail is absent. **Missing** means no section addresses it. **Unresolved** means the source is ambiguous or conflicting and a decision is pending.

## Output formats

- Default to a shareable document the user can edit. If the user asks for a Word or PDF file, use the docx or pdf skill respectively.
- For a policy set, produce one document per policy plus a short index listing each policy, owner, and review date.
- Keep the chat reply short: state what was produced, summarise the unresolved items and coverage status, and offer one next step.

## Review and disclaimer

Every policy is a draft until reviewed. State in the document control block that status is DRAFT and that approval requires HR/IT (as relevant) and legal review.

End every policy with: "This policy is a template generated for internal use and does not constitute legal advice. Have it reviewed by qualified legal counsel before adoption."
