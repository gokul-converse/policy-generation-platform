---
name: skill-creator
description: Guide the creation, drafting, structuring, and evaluation of new Agent Skills following Anthropic standards. Use this skill whenever creating or refining a reusable SKILL.md file with YAML frontmatter, actionable guidance, and progressive disclosure references.
---

# Skill Creator

Guide the creation of reusable Agent Skills. A skill is a directory containing `SKILL.md` with YAML frontmatter and Markdown body.

## 1. Skill Metadata & Frontmatter
Every `SKILL.md` starts with valid YAML frontmatter:
```yaml
---
name: <lowercase-kebab-case-name>
description: <concise 3rd person description of purpose and triggers>
---
```

## 2. Anatomical Structure
1. **Frontmatter**: Concise metadata (`name`, `description`).
2. **Title & Purpose**: One clear statement of what the skill does.
3. **Step-by-Step Workflow**: Actionable instructions written directly to the agent.
4. **Concrete Constraints**: Specific boundaries, required structures, and forbidden actions.
5. **Progressive Disclosure**: Detailed domain tables, schemas, or legal hooks stored in `references/` files rather than bloating the main `SKILL.md`.

## 3. Grounding & Fidelity
- Do not hallucinate company-specific facts, thresholds, or legal minimums.
- Preserve source requirement IDs, numbers, currencies, and deadlines.
- Flag missing decisions or ambiguities rather than inventing answers.
