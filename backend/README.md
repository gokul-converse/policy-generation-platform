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

### 3. Policy generation and review

`POST /policies/generate` requires the confirmed `session_id` and
`requirement_id`. The service loads requirements only from a confirmed
session, adapts them into a common input format, and resolves policy title,
domain, description, source-version metadata, and the requested skill command
(default `/policy`). The policy-generation agent uses Azure AI Foundry and the
resolved skill guidance to return a structured policy with sections and
requirement-ID mappings.

Before persistence, the backend rejects missing or placeholder policy
content, then validates the draft for:

- Non-empty sections and unique, non-empty section IDs.
- Requirement IDs that exist in the source requirements.
- Requirement-ID coverage across policy sections.
- Preservation of numeric values and units in mapped policy content.
- Configured placeholder tokens and unresolved clarification items.

The validation report is stored with the policy and its initial version. The
backend also writes a formatted text document to `data/policy.txt` and a
versioned copy under `data/policies/`. Requirement-ID coverage is based on
section citations; it is not a semantic proof that every requirement has
actually been satisfied.

Policy review is section-based. `POST /policies/{policy_id}/modify` accepts a
`section_id` and revision instructions; the backend reloads authoritative
requirements and previously applied skills, revises only the requested
section, checks its mappings and requested changes, and validates the whole
policy before creating a new version. A `FAIL` result blocks version
creation. A `NEEDS_CLARIFICATION` draft may still be saved. The approval
endpoint changes a version's status to `approved` without performing
validation checks, so clients should inspect the stored validation report
before approving. Policy versions can be listed, retrieved, approved, or
returned as formatted text.

### 4. Skill generation

`POST /skills/generate` requires a confirmed `session_id` and
`requirement_id`. The backend loads the requirement from that session and
passes it to the Azure AI Foundry skill-generation agent. The agent is
instructed to create the minimum useful set of reusable skills, group related
requirements where appropriate, avoid inventing rules, and cover every input
requirement.

Each generated skill must have a unique lowercase kebab-case name, a
description, instructions, and one or more source requirement IDs. The
backend validates the structured output, checks required Markdown headings
and requirement coverage, and reconstructs the Source Requirements section
from the authoritative requirement text so the IDs and source wording remain
traceable. Validation failures are sent back for repair for up to three
generation attempts. Successfully generated skills are stored as files and
as initial `draft` database versions; duplicate names are rejected. The skill
endpoints list skills and expose their details and version history.

### 5. UI definition generation

`POST /api/ui/generate` sends policy text to the Foundry-backed agent, parses
the response as JSON, and validates it against
`schemas/policy-ui-contract.schema.json`. If parsing or validation fails, the
backend makes up to two repair attempts before returning an error.

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
| `POST` | `/policies/generate` | Generate a policy from a confirmed requirement |
| `GET` | `/policies` | List policies, with optional filters and pagination |
| `GET` | `/policies/{policy_id}` | Retrieve a policy, optionally by version |
| `POST` | `/policies/{policy_id}/modify` | Revise a policy and validate the changes |
| `GET` | `/policies/{policy_id}/versions` | List policy version history |
| `GET` | `/policies/{policy_id}/versions/{version}` | Retrieve a specific policy version |
| `POST` | `/policies/{policy_id}/versions/{version}/approve` | Approve a policy version |
| `GET` | `/policies/{policy_id}/text` | Retrieve formatted policy text |
| `GET` | `/skills/slash-commands` | List skills for slash-command autocomplete |
| `POST` | `/skills/generate` | Generate skills from a confirmed requirement |
| `GET` | `/skills` | List generated skills |
| `GET` | `/skills/{skill_id}` | Retrieve skill details |
| `GET` | `/skills/{skill_id}/versions` | List versions of a skill |
| `GET` | `/skills/{skill_id}/versions/{version}` | Retrieve a specific skill version |
| `POST` | `/api/ui/generate` | Generate a validated UI definition from policy text |
| `WebSocket` | `/ws/requirements` | Gather and process requirements interactively |

The policy and skill generation endpoints expect requirement/session data
already available to the backend; see the request schemas in `/docs` for the
required payloads.

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
