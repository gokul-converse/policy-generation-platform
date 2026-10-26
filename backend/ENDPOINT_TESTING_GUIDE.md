# Testing the skill → policy generation flow, endpoint by endpoint

## 0. Prerequisites

```bash
# From backend/, with your venv active
pip install -r requirements.txt --break-system-packages   # if not already installed

# Create tables + seed sample data (idempotent — safe to rerun)
python -m scripts.seed_sample_requirements

# Start the server
uvicorn app.main:app --reload --port 8000
```

**Real LLM calls need real services.** `generate_skills` calls Ollama
(`http://localhost:11434`, model `llama3.2:3b` per `settings.py`), and
policy generation calls Azure AI Foundry (`foundry_project_endpoint` in
`.env`). If neither is reachable, every `/skills/generate` or
`/policies/generate` call below will fail with a connection error — that's
expected, not a bug. If you just want to confirm the *routing/DB/validation*
logic without Ollama/Foundry running, use Swagger (`/docs`) to poke the
read-only `GET` endpoints, or patch `skill_service.generate_skills` /
`policy_service.generate_policy_from_requirements` the way the test suite
does (see `app/test/test_skill_api.py` for the pattern).

**Easiest path**: open **http://localhost:8000/docs** — Swagger UI lets you
fill in and fire every endpoint below interactively, with schemas, without
writing curl. Use the curl commands here when you want scripted repeatable
checks or need to pass the output of one call into the next.

Seeded data available after step 0:
- Session `SES-DEMO-001` (domain `hr`, status `confirmed`)
- `REQ-DEMO-001`: "Employees receive 20 days of annual leave per year."
- `REQ-DEMO-002`: "Leave requests must be submitted at least 5 days before the leave starts."

---

## 1. Health check

```bash
curl http://localhost:8000/health
```
Expect: `{"status":"healthy"}`. If this fails, nothing else will work — check the server actually started.

---

## 2. Skills

### 2.1 `GET /skills/slash-commands`
Lists built-in + generated skills for the `/` autocomplete menu.
```bash
curl http://localhost:8000/skills/slash-commands
```

### 2.2 `POST /skills/generate`
Three valid shapes — pick exactly one of `requirement_id` / `session_id` / `requirements`.

```bash
# (a) single requirement
curl -X POST http://localhost:8000/skills/generate \
  -H "Content-Type: application/json" \
  -d '{"requirement_id": "REQ-DEMO-001"}'

# (b) whole session (loads REQ-DEMO-001 + REQ-DEMO-002 together)
curl -X POST http://localhost:8000/skills/generate \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SES-DEMO-001"}'
```
Expect `201` with a `skills` array. Save a `skill_id` from the response for the next calls.

```bash
# error cases to also check:
curl -X POST http://localhost:8000/skills/generate -d '{}' -H "Content-Type: application/json"               # 422 — neither provided
curl -X POST http://localhost:8000/skills/generate -d '{"requirement_id":"REQ-DEMO-001","session_id":"SES-DEMO-001"}' -H "Content-Type: application/json"  # 422 — both provided
curl -X POST http://localhost:8000/skills/generate -d '{"requirement_id":"REQ-DOES-NOT-EXIST"}' -H "Content-Type: application/json"  # 422 — not found
```

### 2.3 `GET /skills`
Supports pagination (newest first).
```bash
curl http://localhost:8000/skills                                  # default: limit=50, offset=0
curl "http://localhost:8000/skills?limit=10"
curl "http://localhost:8000/skills?limit=10&offset=10"              # next page
curl "http://localhost:8000/skills?limit=500"                       # expect 422 — limit caps at 200
curl "http://localhost:8000/skills?offset=-1"                       # expect 422
```

### 2.4 `GET /skills/{skill_id}`
```bash
curl http://localhost:8000/skills/<skill_id-from-2.2>
curl http://localhost:8000/skills/00000000-0000-0000-0000-000000000000   # expect 404
```

### 2.5 `GET /skills/{skill_id}/versions`
```bash
curl http://localhost:8000/skills/<skill_id>/versions
```

### 2.6 `GET /skills/{skill_id}/versions/{version}`
```bash
curl http://localhost:8000/skills/<skill_id>/versions/1
curl http://localhost:8000/skills/<skill_id>/versions/99   # expect 404
```

---

## 3. Policies

### 3.1 `POST /policies/generate`
Four valid shapes: `requirement_id`, `session_id`, `requirements`, or `requirements_description`.

```bash
# session-based, using the skill you just generated
curl -X POST http://localhost:8000/policies/generate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SES-DEMO-001",
    "skill_command": "/annual-leave-entitlement"
  }'
```
Expect `201` with a `PolicyResponse` — note the `id` (policy_id) and `version`.

```bash
# requirement_id-based, no skill selected
curl -X POST http://localhost:8000/policies/generate \
  -H "Content-Type: application/json" \
  -d '{"requirement_id": "REQ-DEMO-001"}'

# bad session -> 400
curl -X POST http://localhost:8000/policies/generate \
  -H "Content-Type: application/json" \
  -d '{"session_id": "NON-EXISTENT-SESSION"}'
```

### 3.2 `GET /policies`
Supports filtering (`domain`, `status`) and pagination, in any combination.
```bash
curl http://localhost:8000/policies                                       # default: limit=50, offset=0
curl "http://localhost:8000/policies?domain=hr"
curl "http://localhost:8000/policies?status=draft"                        # or status=approved
curl "http://localhost:8000/policies?domain=hr&status=draft"
curl "http://localhost:8000/policies?limit=5&offset=5"
curl "http://localhost:8000/policies?status=not-a-real-status"            # expect 422
```
Note: `status` filters by each policy's *latest* version, applied after
pagination — if you combine `status` with `limit`, a page can return fewer
than `limit` rows even if more policies exist further on. Filter by `domain`
and `limit` together if you need an exact page size.

### 3.3 `GET /policies/{policy_id}`
```bash
curl http://localhost:8000/policies/<policy_id-from-3.1>
curl "http://localhost:8000/policies/<policy_id>?version=1"
```

### 3.4 `POST /policies/{policy_id}/modify`
```bash
curl -X POST http://localhost:8000/policies/<policy_id>/modify \
  -H "Content-Type: application/json" \
  -d '{
    "section_id": "entitlement",
    "instructions": "Clarify that the 20 days exclude public holidays."
  }'
```
Creates a new version — check the response `version` incremented.

### 3.5 `GET /policies/{policy_id}/versions`
```bash
curl http://localhost:8000/policies/<policy_id>/versions
```

### 3.6 `GET /policies/{policy_id}/versions/{version}`
```bash
curl http://localhost:8000/policies/<policy_id>/versions/1
```

### 3.7 `POST /policies/{policy_id}/versions/{version}/approve`
```bash
curl -X POST http://localhost:8000/policies/<policy_id>/versions/1/approve
```

### 3.8 `GET /policies/{policy_id}/text`
```bash
curl http://localhost:8000/policies/<policy_id>/text
curl "http://localhost:8000/policies/<policy_id>/text?version=1"
```
Returns plain text, not JSON.

---

## Suggested run order for a full manual pass

1. `/health`
2. `/skills/generate` with `session_id` → grab `skill_id`
3. `/skills` → `/skills/{id}` → `/skills/{id}/versions` → `/skills/{id}/versions/1`
4. `/policies/generate` with `session_id` + `skill_command` from step 2 → grab `policy_id`
5. `/policies` → `/policies/{id}` → `/policies/{id}/text`
6. `/policies/{id}/modify` → confirm `version` is now 2
7. `/policies/{id}/versions/2/approve`
8. Re-run `pytest app/test/ -q` to confirm nothing regressed

## If you'd rather not depend on Ollama/Foundry being up

Run the automated suite instead — it mocks the LLM calls and covers every
endpoint's logic without needing live services:
```bash
pytest app/test/ -q
```
