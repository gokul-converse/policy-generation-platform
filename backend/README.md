# Policy Generation Platform - Backend

The backend provides APIs for gathering and validating requirements,
generating reusable policy skills and enterprise policies, and managing
versioned policy content. It also exposes a WebSocket-based requirement
workflow and an endpoint for generating schema-validated UI definitions from
policy text.

## Contents

- [Architecture](#architecture)
- [Workflows](#workflows)
  - [Requirement gathering](#1-requirement-gathering)
  - [Requirement validation](#2-requirement-validation)
  - [Skill generation](#3-skill-generation)
  - [Policy generation and review](#4-policy-generation-and-review)
  - [UI definition generation](#5-ui-definition-generation)
- [Workflow logging](#workflow-logging)
- [Requirements](#requirements)
- [Local setup](#local-setup-windows-powershell)
- [Configuration](#configuration)
- [API overview](#api-overview)
- [Backend layout](#backend-layout)
- [Development notes](#development-notes)

## Architecture

- **FastAPI** serves the REST API, WebSocket workflow, health check, and
  interactive OpenAPI documentation.
- **Azure AI Foundry** is the model provider used by the active requirement,
  policy, skill, UI-generation, and UI-repair workflows. Configure the Foundry
  project and Azure service-principal credentials to run them.
- An Ollama client and settings exist, but the current workflow agents do not
  call that client. Ollama is therefore not a runtime requirement for the
  backend as currently wired.
- **SQLAlchemy** stores policies, versions, skills, requirements, and document
  chunks in the database configured by `DATABASE_URL`. PostgreSQL is required
  for the document full-text search index; when SQLite is used, that index is
  skipped.
- **Alembic** applies database schema migrations from `alembic/versions`.

## Workflows

### 1. Requirement gathering

A client connects to `/ws/requirements` and sends `start`, `answer`, `confirm`,
or `cancel` events. The Requirement Gathering Agent collects details from the
user-provided description and retrieves relevant evidence from documents and
stored knowledge. It organizes the results and passes them to the Requirement
Validation Agent for completeness and validation checks.

### 2. Requirement validation

The Requirement Validation Agent evaluates the gathered requirements against
the available evidence and identifies missing, incomplete, or ambiguous
information. It generates clarification questions when additional details are
required and processes the client's answers to update the requirements. Once
the requirements are complete and valid, they can be presented for
confirmation.

Evidence retrieval searches indexed document chunks in the configured
database and filters results by the extracted domain. The PostgreSQL
full-text search index is initialized at startup; SQLite startup skips this
index. Retrieval searches documents available in the database, not arbitrary
files or external knowledge sources. Requirement sessions are persisted;
confirmation saves a versioned requirement snapshot, while cancellation ends
the session.

### 3. Skill generation

`POST /skills/generate` accepts a `session_id`, `requirement_id`, and optional
`source_requirement_version_id`. The service verifies that the session is
confirmed, loads the requirement from the confirmed snapshot, and passes the
validated requirements to `generate_and_save_skills`. That service uses
`load_single_requirement` to load the confirmed source version and
`generate_skills` to run the Foundry-backed generator.

The generator returns structured skills and validates them in two stages:

1. **Deterministic checks** enforce one skill per requirement ID, unique
   lowercase kebab-case names, non-empty descriptions and instructions,
   required Markdown headings, and valid requirement mappings.
   `canonicalize_source_requirements` rebuilds each skill's Source
   Requirements section from authoritative text, rather than trusting
   model-generated copies; `validate_generated_skill_set` checks the result.
2. **Semantic checks** use a separate validation agent to look for changed or
   missing meaning, unsupported rules, conflicts, and other mismatches with
   the source requirements. This check is performed by
   `validate_generated_skills`.

Structural failures and semantic `FAIL` results are returned to the
generator for repair, for up to three attempts by default. A semantic
`NEEDS_CLARIFICATION` result stops generation; skills are not saved unless
validation passes. Each successful skill is stored in the database as
Markdown content in an initial `draft` version by `save_skill_set`, with its
source requirement version recorded. Duplicate skill names already in the
database are rejected.

### 4. Policy generation and review

`POST /policies/generate` accepts a `skill_command` identifying one existing
generated skill. The service resolves the skill and its exact saved version.
The skill's Source Requirements provide the policy requirements and metadata
(title, domain, and purpose); callers do not submit a separate requirement or
session ID. Each policy is generated from one skill.

`generate_and_save_policy` resolves the selected skill, extracts its
requirements with `load_requirements_from_selected_skills`, and calls
`generate_policy_from_skill`. The Foundry-backed policy agent generates a
structured policy with numbered sections and requirement-ID mappings. It
receives the exact selected skill version and a coverage checklist built from
its Source Requirements. The skill provides drafting guidance, while its
Source Requirements are the source text the policy must cover. Missing
information or conflicts can be recorded in `unresolved_items`.

Before creating a policy, the backend validates the structured output and
section numbering, and rejects missing or placeholder content. Then
`validate_policy_semantics` checks the complete policy against the Source
Requirements and selected skill. It reviews actual meaning, requirement
traceability, coverage, numeric values and units, unsupported additions, and
conflicts. Requirement-ID citations alone do not prove that a rule is
implemented. This is a semantic check, not an exact numeric-token comparison.

The validation report is stored with the policy version. A `FAIL` blocks
initial policy creation and returns HTTP 409 with the validation comparison.
`NEEDS_CLARIFICATION` does not block creation: the draft is saved with that
validation status and its clarification items for review. Each policy version
records the exact skill version used and the original source requirement
lineage.

`POST /policies/{policy_id}/modify` accepts overall policy feedback, not a
section ID. The backend loads the latest policy and its exact skill version,
then `modify_policy` calls `resolve_modification_skill_baseline` to select the
skill version linked to the current policy (or reuse a newer draft skill
version left by an earlier interrupted attempt). It calls
`analyze_policy_feedback` to decide whether skill instructions, Source
Requirements, or both need changes. If needed, `modify_skill_content`
prepares the revision and `validate_skill_modification_output` checks its
scope before a new skill version is created; the earlier skill version
remains unchanged. Feedback may change the Source Requirements used for the
regenerated policy. Those feedback-derived changes are stored in the new
skill version; the original confirmed requirement snapshot is not updated,
and the changed requirements are not independently confirmed by this
workflow.

The service then regenerates the **complete policy** from the selected skill
version, validates it, and saves a new policy version unless validation
returns `FAIL`. `NEEDS_CLARIFICATION` versions can be saved with their report.
The policy version records the exact skill version used and retains the
original source requirement-version lineage. Because a revised skill version
is committed before policy regeneration, it can remain in the database even
if later policy generation or validation fails.

Policy versions can be listed, retrieved, approved, or returned as formatted
text. Approval activates the policy version and the exact skill versions
referenced by it; inspect the saved validation report before approval.

### Workflow logging

Skill generation, initial policy generation, and feedback-driven policy
modification emit stage-based application logs. Each workflow receives a
short workflow ID, shown in square brackets in its log messages, so its
requirement loading, generation, validation, and persistence events can be
followed together.

Logs include relevant record/version IDs, stage outcomes, item counts,
validation status and finding counts, and elapsed time. Failures are logged
with exception details and then propagated to the API. Service-level workflow
logs avoid writing full generated skill instructions, policy text, or Source
Requirements. A `NEEDS_CLARIFICATION` policy saved successfully is logged as
a warning with its clarification count.

The application writes logs to both the console and timestamped files under
`backend/logs/`, using the format:

```text
timestamp | level | logger | source-file:line | message
```

File logging rotates at 5 MB and retains up to three backup files per log.
To investigate a workflow, find its workflow ID in `backend/logs/`, then
compare entries by stage and elapsed time. A validation rejection will report
the failed rule names; a clarification outcome will report the validation
status and count without dumping the policy contents.

### 5. UI definition generation

`POST /api/ui/generate` sends policy text to the Foundry-backed agent, parses
the response as JSON, and validates it against
`ui_contracts/policy-ui-contract.schema.json`. If parsing or validation fails,
the backend makes up to two repair attempts before returning an error.

## Requirements

- Python and pip, with dependencies listed in `requirements.txt`
- An Azure AI Foundry project, model deployment, and service principal
  credentials for the active AI workflows

## Local setup (Windows PowerShell)

Run the following commands from the `backend` directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and configure `DATABASE_URL` and the model/provider settings
required by the workflows you intend to run. See
[Configuration](#configuration) for details.

### Prepare the database

With the virtual environment active and the current directory set to `backend`:

```powershell
alembic upgrade head
```

The application requires a SQLAlchemy asynchronous connection URL in
`DATABASE_URL`. Alembic applies schema migrations; at startup, the application
initializes the document search index when connected to PostgreSQL.

### Start the backend

With the virtual environment active and the required Azure AI Foundry settings
configured, run from `backend`:

```powershell
uvicorn app.main:app --reload
```

The API listens at `http://127.0.0.1:8000` by default.

- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

The health check reports that the application process is running; it does not
verify connections to Azure AI Foundry.

## Configuration

The application reads settings from `backend/.env` and environment variables.
Do not commit `.env` or put credentials in source control.

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy asynchronous database connection URL | Required by the database engine |
| `FOUNDRY_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint | Not set |
| `FOUNDRY_MODEL` | Azure AI Foundry model deployment name | `gpt-5-nano` |
| `AZURE_TENANT_ID` | Azure service principal tenant ID | Not set |
| `AZURE_CLIENT_ID` | Azure service principal client ID | Not set |
| `AZURE_CLIENT_SECRET` | Azure service principal secret | Not set |

Set `DATABASE_URL`, `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`, and the Azure
credentials required by the configured Foundry identity. The active agents
currently use Foundry; Ollama settings and a client module exist but are not
used by these workflows. Generated skills are stored in the database; the
legacy `GENERATED_SKILLS_DIR` setting is not the active generated-skill
storage mechanism.

## API overview

The interactive API schema and request/response models are available at
`/docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check application process health |
| `POST` | `/policies/generate` | Generate a policy from one saved skill |
| `GET` | `/policies` | List policies, with optional filters and pagination |
| `GET` | `/policies/{policy_id}` | Retrieve a policy, optionally by version |
| `POST` | `/policies/{policy_id}/modify` | Apply overall feedback and regenerate a policy |
| `GET` | `/policies/{policy_id}/versions` | List policy version history |
| `GET` | `/policies/{policy_id}/versions/{version}` | Retrieve a specific policy version |
| `POST` | `/policies/{policy_id}/versions/{version}/approve` | Approve a policy version |
| `GET` | `/policies/{policy_id}/text` | Retrieve formatted policy text |
| `GET` | `/skills/slash-commands` | List skills for slash-command autocomplete |
| `POST` | `/skills/generate` | Generate and validate skills from a confirmed requirement |
| `GET` | `/skills` | List generated skills |
| `GET` | `/skills/{skill_id}` | Retrieve skill details |
| `GET` | `/skills/{skill_id}/versions` | List versions of a skill |
| `GET` | `/skills/{skill_id}/versions/{version}` | Retrieve a specific skill version |
| `POST` | `/api/ui/generate` | Generate a validated UI definition from policy text |
| `WebSocket` | `/ws/requirements` | Gather and process requirements interactively |

The skill-generation endpoint expects a confirmed requirement/session already
available to the backend. Policy generation instead expects the slash-command
of an existing generated skill. See the request schemas in `/docs` for exact
payloads and fields.

## Backend layout

```text
backend/
|-- app/
|   |-- agents/       # Requirement, policy, skill, repair, and Foundry agents
|   |-- api/          # FastAPI REST and WebSocket routes
|   |-- clients/      # Ollama and Azure AI Foundry clients
|   |-- config/       # Environment-backed settings
|   |-- db/           # Async database engine and search-index initialization
|   |-- models/       # Database and API models
|   |-- repositories/ # Database access
|   |-- services/     # Policy, skill, requirement, and UI workflows
|   `-- schemas/      # Request validation schemas
|-- alembic/          # Database migration environment and revisions
|-- data/             # Local backend data and assets
|-- scripts/          # Backend data and validation utilities
|-- skills/           # Built-in skill definitions
|-- generated_skills/ # Legacy directory; active generated skills are database-backed
|-- .env.example      # Environment variable template
`-- requirements.txt  # Pinned Python dependencies
```

## Development notes

- Cross-origin requests are enabled for `http://localhost:3000` for local
  development.
- Apply new schema migrations with Alembic before starting against an updated
  schema.
- Use the API docs at `/docs` to inspect request and response schemas and
  manually exercise endpoints.
