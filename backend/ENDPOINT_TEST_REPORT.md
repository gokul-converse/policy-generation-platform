# Skill and Policy API Test Report

## Scope

Initial workflow: requirement input -> Skill Generation -> slash-command discovery -> Policy Generation -> policy modification -> version history -> approval -> policy text retrieval.

## Changes made in this working copy

- Added explicit accepted-status checks (`validated`, `confirmed`, `valid`, `approved`) to the requirement adapter, including Pydantic request objects. Pending, extracted, clarification-required, incomplete, invalid, and rejected requirements are not accepted for generation.
- Added source-version, conditions, source-document, and metadata fields to the normalized requirement model so the adapter can preserve supported provenance/context.
- Requirement session loading now prefers the newest explicitly validated `requirement_versions` snapshot and preserves its actual `requirement_version_id`. It falls back to live requirement rows only when each row is in an accepted status. The teammate-owned tables and module are not modified.
- Policy modification requests can include approved requirements or a requirement `session_id`; AI-assisted modifications without source requirements are rejected instead of silently claiming validated output.
- Policy validation now returns `NEEDS_CLARIFICATION` with zero coverage when no source requirements are supplied.
- Policy text retrieval uses per-policy versioned archives and never returns the shared `data/policy.txt` for an unrelated policy ID.
- Unknown policy version-history requests return HTTP 404.
- Generic policy API errors no longer expose raw exception text to callers.
- Skill instruction loading selects the numerically latest skill version rather than relying on relationship ordering.
- Added regression assertions for slash-command discovery, health, invalid IDs/versions, policy text isolation, and missing source requirements.
- Converted `requirements.txt` from UTF-16 to UTF-8 so package installers can parse it normally.
- Added `.gitignore` and replaced `.env.example` values with safe placeholders. The real `.env` is excluded from the deliverable.

## Executed checks

| Check | Result | Notes |
|---|---|---|
| Python compileall | PASS | All Python files in the working copy compiled successfully. |
| Requirement adapter, policy validation, skill schema, and model tests | PASS | 21 passed. |
| Skill API integration tests | BLOCKED | Test collection cannot import `aiosqlite` in this analysis environment. |
| Policy API integration tests | BLOCKED | Test collection cannot import `agent_framework` in this analysis environment. |
| Live LLM generation | NOT RUN | Requires the configured Foundry/Ollama runtime and credentials. |
| Live Swagger execution | NOT RUN | No application server could be started in this environment because required dependencies are missing. |

A failed test collection is not a functional endpoint failure. API integration results must be confirmed in the project's configured virtual environment.

## API endpoint coverage added/retained in tests

- `GET /health`
- `GET /skills/slash-commands`
- `POST /skills/generate`
- `GET /skills`
- `GET /skills/{skill_id}`
- `GET /skills/{skill_id}/versions`
- `GET /skills/{skill_id}/versions/{version}`
- `POST /policies/generate`
- `GET /policies`
- `GET /policies/{policy_id}` (latest and explicit version)
- `POST /policies/{policy_id}/modify`
- `GET /policies/{policy_id}/versions`
- `GET /policies/{policy_id}/versions/{version}`
- `POST /policies/{policy_id}/versions/{version}/approve`
- `GET /policies/{policy_id}/text`

## How to run the API tests locally

From the backend folder in the project's activated virtual environment:

```powershell
python -m pip install -r requirements.txt
python -m pytest app/test/test_skill_api.py app/test/test_policy_api.py -v
```

The test suite uses mocked generation-agent responses for deterministic API tests and a temporary SQLite database. Do not apply migrations to the shared production or teammate database to run these tests.

## Remaining limitations

- Requirement-change event handling and automatic policy regeneration are not implemented by this initial test-focused change. The current change makes modification source-aware; automatic synchronization should be added after the teammate's requirement branch contract is integrated.
- API integration tests and live model calls remain unverified until run in the configured environment.
