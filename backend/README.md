# Backend

The backend is an asynchronous FastAPI application that generates and manages
policy skills and enterprise policies. It uses SQLAlchemy with SQLite for
persistence, Ollama for skill generation, and Azure AI Foundry for policy
generation.

## Requirements

- Python version compatible with the pinned dependencies in `requirements.txt`
- Ollama and the configured model for skill-generation requests
- Azure AI Foundry project access and credentials for policy-generation requests

The health endpoint and read-only API calls can be used without making model
requests.

## Local setup

Run these commands from the repository root in PowerShell:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` with the settings required for the model providers. Do not
commit `.env` or credentials. Environment variable names are case-insensitive;
the supported settings and defaults are defined in
[`app/config/settings.py`](app/config/settings.py):

| Setting | Purpose | Default |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | Ollama server address | `http://localhost:11434` |
| `OLLAMA_MODEL` | Model used for skill generation | `llama3.2:3b` |
| `AZURE_TENANT_ID` | Azure tenant used for Foundry authentication | Empty |
| `AZURE_CLIENT_ID` | Azure client used for Foundry authentication | Empty |
| `AZURE_CLIENT_SECRET` | Azure client secret | Empty |
| `FOUNDRY_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint | Empty |
| `FOUNDRY_MODEL` | Azure AI Foundry model name | `gpt-5-nano` |

Apply database migrations before starting the API. From `backend/`:

```powershell
uvicorn app.main:app --reload --port 8000
```

The seed step is optional and creates sample requirements for local endpoint
testing. The application database is `backend/data/enterprise_policy.db`.
Interactive API documentation is available at <http://localhost:8000/docs>
after the server starts.

## Architecture

```text
app/
  api/                 FastAPI routes and HTTP error mapping
  agents/              LLM instructions and skill/policy generation
  clients/             Ollama and Azure AI Foundry clients
  config/              Environment-backed application settings
  db/                  Async SQLAlchemy engine, sessions, and FTS setup
  models/               Request/response schemas and database models
  repositories/         Database persistence and retrieval
  services/             Generation orchestration and business rules
  observability/        Logging, metrics, and tracing
  test/                 Automated tests and local test utilities
alembic/                Database migrations
scripts/                Local data/bootstrap scripts
skills/                 Built-in skill definitions
```

Routes should remain focused on HTTP concerns. Put workflow and validation
behavior in services, persistence in repositories, and API/database schemas
in their respective model modules.

### Runtime model instructions

The system instructions passed to the generation agents are currently defined
as constants in `app/agents/policy_generation/policy_generator.py` and
`app/agents/policy_generation/skill_generation.py`. They are runtime model
inputs and are separate from the repository's Copilot instructions in
`.github/copilot-instructions.md`.

## API overview

The API is mounted from `app/main.py`. FastAPI serves the complete OpenAPI
schema and request/response models at `/docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Basic health check |
| `GET` | `/skills/slash-commands` | List built-in and generated skills |
| `POST` | `/skills/generate` | Generate and persist skills |
| `GET` | `/skills` | List generated skills |
| `GET` | `/skills/{skill_id}` | Get skill details |
| `GET` | `/skills/{skill_id}/versions` | List skill versions |
| `GET` | `/skills/{skill_id}/versions/{version}` | Get a skill version and content |
| `POST` | `/policies/generate` | Generate and persist a policy |
| `GET` | `/policies` | List policies with filters and pagination |
| `GET` | `/policies/{policy_id}` | Get the latest or a requested policy version |
| `POST` | `/policies/{policy_id}/modify` | Revise policy content and create a version |
| `GET` | `/policies/{policy_id}/versions` | List policy versions |
| `GET` | `/policies/{policy_id}/versions/{version}` | Get a policy version |
| `POST` | `/policies/{policy_id}/versions/{version}/approve` | Approve a policy version |
| `GET` | `/policies/{policy_id}/text` | Retrieve policy text |

See [ENDPOINT_TESTING_GUIDE.md](ENDPOINT_TESTING_GUIDE.md) for example requests,
expected responses, and endpoint-level testing steps.

## Tests

Run the offline test suite from `backend/`:

```powershell
python -m pytest app/test -k "not live"
```

The live skill-generation test requires its configured model service and is
excluded by the command above. Test modules use mocks for generation where
possible; use the endpoint testing guide when validating configured external
services.

## Database changes

Create a new Alembic revision for schema changes and apply it with
`alembic upgrade head`. Do not rely on `create_db_tables()` as a production
migration mechanism; it is a development bootstrap helper.
