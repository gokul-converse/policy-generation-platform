# Policy Generation Backend

This directory contains the FastAPI backend for generating and managing
enterprise policies and reusable policy skills. It also provides requirement
gathering over WebSockets and an endpoint for generating schema-validated UI
definitions from policy text.

## Backend components

- **FastAPI** serves the REST API, WebSocket workflow, health check, and
  interactive OpenAPI documentation.
- **Azure AI Foundry** is the model provider used by the active requirement,
  policy, skill, UI-generation, and UI-repair workflows. Configure the Foundry
  project and Azure service-principal credentials to run them.
- An Ollama client and settings exist, but the current workflow agents do not
  call that client. Ollama is therefore not a runtime requirement for the
  backend as currently wired.
- **SQLite** stores policies, versions, skills, requirements, and document
  chunks in `data/enterprise_policy.db`. Full-text search uses SQLite FTS5.
- **Alembic** applies database schema migrations from `alembic/versions`.

## Main backend workflows

### 1. Requirement gathering

A client connects to `/ws/requirements` and sends `start`, `answer`, `confirm`,
or `cancel` events. The Requirement Gathering Agent collects the initial
requirement details from the client's description and retrieves relevant
supporting evidence from available documents and stored knowledge. It
organizes the gathered information and passes it to the Requirement
Validation Agent for completeness and validation checks.

### 2. Requirement validation

The Requirement Validation Agent evaluates the gathered requirements against
the available evidence and identifies missing, incomplete, or ambiguous
information. It generates clarification questions when additional details are
required and processes the client's answers to update the requirements. Once
the requirements are complete and valid, they can be presented for
confirmation.

Evidence retrieval searches existing document chunks in the backend's SQLite
database using FTS5 and filters results by the extracted domain. It searches
documents available in the database, not arbitrary files or external
knowledge sources. Requirement sessions are persisted; confirmation saves a
versioned requirement snapshot, while cancellation ends the session.

### 3. Skill generation

`POST /skills/generate` accepts a `session_id`, `requirement_id`, and optional
`source_requirement_version_id`. The backend verifies that the session is
confirmed, loads the requirement from the confirmed snapshot, and passes its
validated requirements to `generate_and_save_skills`. That service calls
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
generated skill. The backend resolves that skill and its exact saved version.
The skill's Source Requirements provide the policy-generation requirements
and metadata (title, domain, and purpose); callers do not submit a separate
requirement or session ID for this endpoint. Policy generation currently
supports one generated skill per policy.

`generate_and_save_policy` resolves the selected skill, extracts its
requirements with `load_requirements_from_selected_skills`, and calls
`generate_policy_from_skill`. The Foundry-backed policy agent generates a
structured policy with numbered sections and requirement-ID mappings. It
receives the exact selected skill version and a coverage checklist built from
its Source Requirements. The skill provides drafting guidance, while its
Source Requirements are the source text the policy must cover. Missing
information or conflicts can be recorded in `unresolved_items`.

Before creating a policy, the backend rejects missing or placeholder content,
then runs deterministic and semantic validation:

- `validate_policy_draft` performs deterministic checks for section content
  and IDs, handbook numbering, requirement-ID mappings and coverage,
  numeric/unit preservation, and configured placeholders.
- `validate_policy_semantics` compares actual policy meaning with the Source
  Requirements and selected skill. A citation alone does not prove that a
  requirement is implemented.
- `merge_policy_validation_reports` combines both sets of findings.

The combined validation report is stored with the policy version. A `FAIL`
blocks initial policy creation and returns HTTP 409 with the validation
comparison. `NEEDS_CLARIFICATION` does not block creation: the draft is saved
with that validation status and its clarification items for review. Each
policy version records the exact skill version used and the original source
requirement lineage.

`POST /policies/{policy_id}/modify` accepts overall policy feedback, not a
section ID. The backend loads the latest policy and its exact skill version,
then `modify_policy` calls `analyze_policy_feedback` to decide whether skill
instructions, Source Requirements, or both need changes. If needed,
`modify_skill_content` prepares the revision and
`validate_skill_modification_output` checks its scope before a new skill
version is created; the original skill version remains unchanged. Feedback
may change the Source Requirements used for the regenerated policy. Those
feedback-derived changes are stored in the new skill version; the original
confirmed requirement snapshot is not updated, and the changed requirements
are not independently confirmed by this workflow.

The backend then regenerates the **complete policy** from the selected skill
version, validates it, and saves a new policy version unless validation
returns `FAIL`. `NEEDS_CLARIFICATION` versions can be saved with their report.
The policy version records the exact skill version used and retains the
original source requirement-version lineage. Because a revised skill version
is committed before policy regeneration, it can remain in the database even
if later policy generation or validation fails.

Policy versions can be listed, retrieved, approved, or returned as formatted
text. Approval activates the policy version and the exact skill versions
referenced by it; inspect the saved validation report before approval.

### 5. UI definition generation

`POST /api/ui/generate` sends policy text to the Foundry-backed agent, parses
the response as JSON, and validates it against
`ui_contracts/policy-ui-contract.schema.json`. If parsing or validation fails,
the backend makes up to two repair attempts before returning an error.

## Requirements

- Python with support for the pinned dependencies in `requirements.txt`
- An Azure AI Foundry project, model deployment, and service principal
  credentials for the active AI workflows

## Local setup (Windows PowerShell)

Run these commands from the `backend` directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set the model/provider values required by the workflows you
intend to use (see [Configuration](#configuration)).

### Prepare the database

With the virtual environment active and the current directory set to `backend`:

```powershell
alembic upgrade head
```

The application uses `data/enterprise_policy.db` by default. Alembic applies
the schema migrations; the application initializes and synchronizes its FTS5
index when it starts.

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
| `FOUNDRY_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint | Not set |
| `FOUNDRY_MODEL` | Azure AI Foundry model deployment name | `gpt-5-nano` |
| `AZURE_TENANT_ID` | Azure service principal tenant ID | Not set |
| `AZURE_CLIENT_ID` | Azure service principal client ID | Not set |
| `AZURE_CLIENT_SECRET` | Azure service principal secret | Not set |
| `GENERATED_SKILLS_DIR` | Directory used to store generated skills | `app/generated_skills` |

Set `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`, and all three Azure
credentials. Although the application has `OLLAMA_BASE_URL` and `OLLAMA_MODEL`
settings and an Ollama client module, the active agents currently use Foundry.
`DATABASE_URL` is not currently used by the application database engine; the
SQLite database location is fixed at `data/enterprise_policy.db`.

## API overview

The API schema and request/response models are available at `/docs`.

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
|   |-- db/           # Async SQLite engine and FTS5 initialization
|   |-- models/       # Database and API models
|   |-- repositories/ # Database access
|   |-- services/     # Policy, skill, requirement, and UI workflows
|   `-- schemas/      # Request validation schemas
|-- alembic/          # Database migration environment and revisions
|-- data/             # Local database and policy data
|-- scripts/          # Backend data and validation utilities
|-- skills/           # Built-in skill definitions
|-- generated_skills/ # Generated skill files (configurable)
|-- .env.example      # Environment variable template
`-- requirements.txt  # Pinned Python dependencies
```

## Development notes

- The backend allows cross-origin requests from `http://localhost:3000`.
- Apply new schema migrations with Alembic before starting against an updated
  schema.
- Use the API docs at `/docs` to inspect request and response schemas and
  manually exercise endpoints.
