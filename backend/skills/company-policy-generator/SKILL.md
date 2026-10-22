---
name: company-policy-generator
description: Generate complete, company-specific internal policy documents of any kind - HR (leave, attendance, WFH/remote, code of conduct, anti-harassment/POSH, performance, travel and expense, recruitment, exit), IT and information security (acceptable use, BYOD, access control, password, incident response), data privacy, finance (procurement, delegation of authority), health and safety, and similar. Use this skill whenever the user asks to create, draft, write, update, standardise, or review a policy, SOP-style guideline, employee handbook section, or "rules for X" for a company, startup, or team, even if they just say "we need a policy for..." or "make a policy document".
---

# Company Policy Generator

Produce a policy a company can adopt with light editing. A good policy is
(1) compliant with the law where the company operates, (2) specific enough that
a reader can answer "what am I allowed to do, and what do I do next?" without
asking the policy owner, and (3) internally consistent: numbers, roles, and
timelines never contradict each other.

## Step 1: Gather inputs

Ask only for what is missing. If the user described their company, extract
answers from that first. Where an answer is not given, use the default and
record it in the Assumptions section instead of stalling. Ask in one short
batch, never one question at a time.

| Input | Why it matters | Default |
|---|---|---|
| Policy type(s) wanted | Selects the template in `references/policy-types.md` | Required |
| Company name, industry | Industry decides which regulations apply | Generic services firm |
| Country and state/region | Law differs; wrong jurisdiction is the most common compliance error | Ask; never guess |
| Headcount, locations, remote share | Many legal duties trigger at headcount thresholds | 10-50 employees |
| Who is covered | Employees, contractors, interns, vendors, visitors | Employees + contractors |
| Existing policies or practices | New policy must not silently reduce current benefits or contradict other policies | None |
| Tone and culture | Formal vs plain-language | Plain, professional |
| Special asks | Anything specific the user wants included | None |

Country and region are the one input worth asking for if absent.

## Step 2: Verify current law

Statutory numbers recalled from memory go stale. For any policy touching
regulated ground (employment, privacy, safety, finance, harassment), use web
search to confirm the current rule for the user's jurisdiction and company size
before stating a statutory minimum. Read `references/policy-types.md` for the
"legal hooks" to check for each policy type. If something cannot be confirmed,
write it as `[verify: ...]` in the text and list it in the compliance notes. A
flagged gap is better than a confident wrong number.

For purely internal-governance policies with no legal hook (for example an
expense policy), skip research and say so in the assumptions.

## Step 3: Draft the policy

Use this skeleton for every policy type, adding the type-specific sections from
`references/policy-types.md`:

1. **Title block**: policy name, version, effective date, owner, approver, next review date.
2. **Purpose**: one short paragraph on why the policy exists.
3. **Scope**: who and what is covered, and explicit exclusions.
4. **Definitions**: only terms the reader could misread; define each once.
5. **Policy statements**: the rules, grouped by theme, each numbered so it can be cited.
6. **Roles and responsibilities**: who owns, approves, administers, and must comply.
7. **Procedures**: how to request, report, approve, or escalate, with timelines.
8. **Exceptions**: who can approve a deviation, how it is recorded.
9. **Violations and consequences**: proportionate and process-based (notice, explanation, then action).
10. **Records and confidentiality**: what is kept, where, for how long, who sees it.
11. **Related documents**: other policies, forms, or laws referenced.
12. **Governance**: review cycle, amendment procedure, grievance route.
13. **Assumptions and compliance notes** (last page): inputs assumed, `[verify]` items, and a line stating this is a drafting aid that counsel should review before adoption.

### Drafting principles

- **Never go below statutory minimums**, and say so when the company grants more. Better-than-law is fine; silently worse is a liability.
- **Be concrete.** "Report incidents within 24 hours to the IT Security Lead" beats "report promptly to the relevant person".
- **Check consistency.** Roles, deadlines, and thresholds must match everywhere they appear. Cross-check against the user's other policies.
- **Make it enforceable and realistic.** A rule the company will not enforce weakens every other rule. Prefer fewer, clearer rules.
- **Protect sensitive information.** Medical, complaint, and personal data handling must be minimal-disclosure, and policies must not permit retaliation for good-faith use of a protected right.
- **Plain language.** Short sentences, active voice, one defined term per concept. Employees are the main audience, not lawyers.
- Use "[Company Name]" only if the name was not provided.

## Step 4: Produce the output

Default deliverable is a `.docx`: read the `docx` skill's SKILL.md and follow it. Use numbered headings, a real table wherever data is tabular (entitlements, approval limits, severity levels), the title block first, and the Assumptions page last. If the user asks for PDF, Markdown, or a Docs artifact, produce that instead. For several policies, produce one file per policy unless asked for a combined handbook.

When delivering, reply in a few sentences: what the policy covers, the key numbers or rules chosen (so they can sanity-check), and the `[verify]` items needing confirmation. Do not paste the policy into chat.

## Updating or reviewing an existing policy

Work from the supplied document: keep its structure and wording where it is compliant, change only what is non-compliant or requested, and give a short change summary (clause, old, new, reason). Flag any clause that falls below statutory minimums or conflicts with another policy the user has shared.
