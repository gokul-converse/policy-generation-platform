# Policy Generation Platform

This repository contains the policy-generation backend and its product workflow
notes. The backend provides a FastAPI service for generating skills and
enterprise policies, reviewing policy versions, and approving them.

## Documentation

- [Backend setup, architecture, configuration, and API overview](backend/README.md)
- [Endpoint-by-endpoint testing guide](backend/ENDPOINT_TESTING_GUIDE.md)
- [Workspace coding-agent instructions](.github/copilot-instructions.md)

## Product workflow

The intended user flow is:

1. Submit policy requirements.
2. Select predefined skills or provide custom skill instructions.
3. Generate a policy using the selected skills.
4. Review and revise policy sections while retaining version history.
5. Approve the desired policy version.

The backend API and its current capabilities are documented in
[backend/README.md](backend/README.md). This workflow describes the product
experience; it does not imply that this repository contains a web frontend.
